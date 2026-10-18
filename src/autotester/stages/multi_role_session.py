"""One isolated browser context per role account, each owned by its own thread (MP11).

One job: hold N `BrowserSession`s for N `RoleAccount`s of one project so that no two share a
cookie jar, local storage or profile directory (a persistent profile per account), and let a
caller drive any of them, or all of them at once, without crossing wires. It wraps
`browser/session.py` and edits nothing in it.

Why a thread per account: Playwright's sync API refuses a second driver on the same thread and
a session must be used from the thread that started it, so every account gets a one-thread
executor that starts, uses and closes its session. `run_as` is therefore also a serialiser per
role, and `run_parallel` is real concurrency across roles. Credentials are typed only as
`{{SECRET:KEY}}` placeholders, resolved by `SecretStore` for the page's own host (MPI5), and a
sign-in URL outside the account's platform is refused before anything is typed.
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypeVar

from autotester.browser.secrets import SecretStore, host_of
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.schema.role_account import RoleAccount
from autotester.stages.run_budget import RunBudget

T = TypeVar("T")


class PlatformScopeError(RuntimeError):
    """A URL a role account was asked to use is outside that account's own platform."""


def host_in_platform(platform: Platform, host: str) -> bool:
    """True when `host` is one of the platform's hosts, or a subdomain if it allows them.

    Hosts only, like `Project.allows_domain`; ports are not part of the boundary. The platform's
    `base_url` host always counts, so a platform with no `allowed_domains` still
    admits its own site. A blank host never matches (it would open every gate, AT-001)."""
    candidate = host.strip().lower().rstrip(".")
    if not candidate:
        return False
    domains = {d.rstrip(".") for d in platform.allowed_domains}
    if base := host_of(platform.base_url):
        domains.add(base)
    return any(candidate == d or (platform.include_subdomains and candidate.endswith(f".{d}"))
               for d in domains)


class _Worker:
    """A role's one-thread executor and the session that lives on that thread."""

    def __init__(self, account_id: str) -> None:
        self.ident: int | None = None
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"role-{account_id}",
                                       initializer=self._note_thread)
        self.session: Any = None

    def _note_thread(self) -> None:
        self.ident = threading.get_ident()


class RoleSessions:
    """Open once, drive per role, close once. Use as a context manager."""

    def __init__(self, project: Project, secrets: SecretStore, run_dir: Path, *,
                 paths_root: Path | None = None,
                 session_cls: Callable[..., Any] = BrowserSession,
                 budget: RunBudget | None = None) -> None:
        self.project, self.secrets, self.run_dir = project, secrets, run_dir
        self.session_cls, self.budget = session_cls, budget
        self.accounts: dict[str, RoleAccount] = {a.id: a for a in project.role_accounts or []}
        self._paths = {aid: ProjectPaths(f"{project.slug}-role-{aid}", paths_root)
                       for aid in self.accounts}
        self._workers: dict[str, _Worker] = {}

    # -- lookups ------------------------------------------------------------
    def account(self, account_id: str) -> RoleAccount:
        return self.accounts[account_id]  # KeyError for an unknown id

    def accounts_on(self, platform_id: str) -> list[RoleAccount]:
        return [a for a in self.accounts.values() if a.platform_id == platform_id]

    def platform_of(self, account_id: str) -> Platform:
        wanted = self.account(account_id).platform_id
        return next(p for p in self.project.effective_platforms() if p.id == wanted)

    def profile_dir(self, account_id: str) -> Path:
        return self._paths[account_id].profile_dir

    # -- lifecycle ----------------------------------------------------------
    def open(self) -> RoleSessions:
        """Start every account's session in parallel, each on its own thread."""
        if self._workers:
            return self
        dirs = [self.profile_dir(aid) for aid in self.accounts]
        if len(set(dirs)) != len(dirs):  # MP11: never two roles in one profile
            raise ValueError("two role accounts resolved to the same profile directory")
        self._workers = {aid: _Worker(aid) for aid in self.accounts}
        starts = {aid: w.pool.submit(self._start, self.accounts[aid])
                  for aid, w in self._workers.items()}
        failure: BaseException | None = None
        for aid, future in starts.items():
            try:
                self._workers[aid].session = future.result()
            except BaseException as exc:
                failure = failure or exc
        if failure is not None:
            self.close()
            raise failure
        return self

    def _start(self, account: RoleAccount) -> Any:
        """Runs on the account's own thread: build, brake, tag evidence, start."""
        if self.budget is not None:
            self.budget.check_start()
        session = self.session_cls(self.project, self.secrets, self.run_dir,
                                   self._paths[account.id])
        if self.budget is not None:
            session.budget = self.budget
        if (state := getattr(session, "state", None)) is not None:
            state.evidence_prefix = account.id  # siblings share run_dir; files stay apart (AT-572)
        try:
            session.start()
        except BaseException:
            with contextlib.suppress(Exception):
                session.close()
            raise
        return session

    def close(self) -> None:
        """Close each session on the thread that started it, then stop the threads."""
        workers, self._workers = self._workers, {}
        closing = [w.pool.submit(w.session.close) for w in workers.values()
                   if w.session is not None]
        for future in closing:
            with contextlib.suppress(Exception):
                future.result()
        for worker in workers.values():
            worker.pool.shutdown(wait=True)

    def __enter__(self) -> RoleSessions:
        return self.open()

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- driving ------------------------------------------------------------
    def _worker(self, account_id: str) -> _Worker:
        self.account(account_id)
        if account_id not in self._workers:
            raise RuntimeError("role sessions are not open")
        return self._workers[account_id]

    def run_as(self, account_id: str, fn: Callable[[Any], T]) -> T:
        """Run `fn(session)` on `account_id`'s own thread and return its result (or raise)."""
        worker = self._worker(account_id)
        if worker.ident == threading.get_ident():  # already on this role's thread: no self-wait
            return fn(worker.session)
        return worker.pool.submit(fn, worker.session).result()

    def run_parallel(self, jobs: dict[str, Callable[[Any], Any]]
                     ) -> tuple[dict[str, Any], dict[str, Exception]]:
        """Run one job per account at the same time; one role crashing never aborts the others."""
        workers = {aid: self._worker(aid) for aid in jobs}  # validate every id before any job
        futures = {aid: workers[aid].pool.submit(fn, workers[aid].session)
                   for aid, fn in jobs.items()}
        results: dict[str, Any] = {}
        errors: dict[str, Exception] = {}
        for aid, future in futures.items():
            try:
                results[aid] = future.result()
            except Exception as exc:
                errors[aid] = exc
        return results, errors

    def sign_in(self, account_id: str, login_url: str, *, user_locator: str,
                password_locator: str, submit_locator: str) -> None:
        """Open `login_url`, type the account's two keys as placeholders, press submit.

        The URL's host must belong to the account's own platform, checked before the browser
        moves; the message names the host, never the URL (AT-341)."""
        account, platform = self.account(account_id), self.platform_of(account_id)
        host = host_of(login_url)
        if not host_in_platform(platform, host):
            raise PlatformScopeError(
                f"sign-in host {host!r} is outside platform {platform.id!r} for {account.id!r}")

        def _login(session: Any) -> None:
            session.goto(login_url)
            session.fill(user_locator, f"{{{{SECRET:{account.username_key}}}}}")
            session.fill(password_locator, f"{{{{SECRET:{account.password_key}}}}}")
            session.click(submit_locator)
            session.settle()  # the sign-in navigation finishes before anything else is driven

        self.run_as(account_id, _login)
