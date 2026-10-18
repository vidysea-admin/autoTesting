"""T-210 / MP11: one isolated browser context per role account.

Fake-session tests pin the structure (one session, one profile dir, one owning thread per
account, parallel start and parallel jobs, secrets typed as placeholders only). The live test
drives a real Chromium against the local two-account fixture app (tests/multi_role_app.py) and
checks the behaviour MP11 names: no shared cookies, storage or profile directory, and a sign-out
in one context leaves the other signed in.
"""

from __future__ import annotations

import faulthandler
import functools
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from multi_role_app import PARENT_HOST, build_project, start_app

from autotester.browser.secrets import SecretStore
from autotester.stages.multi_role_session import PlatformScopeError, RoleSessions


class _FakeSession:
    """Stands in for BrowserSession: records the thread it lives on and what was typed."""

    def __init__(self, project, secrets, run_dir, paths=None, **_kw) -> None:
        self.paths, self.project = paths, project
        self.state = SimpleNamespace(evidence_prefix="")
        self.threads: dict[str, int] = {}
        self.typed: list[tuple[str, str | None]] = []
        self.visited: list[str] = []
        self.closed, self.fail_suffix = False, None

    def start(self) -> _FakeSession:
        self.threads["start"] = threading.get_ident()
        if self.fail_suffix and self.paths.slug.endswith(self.fail_suffix):
            raise RuntimeError("browser would not start")
        return self

    def close(self) -> None:
        self.threads["close"] = threading.get_ident()
        self.closed = True

    def goto(self, url: str) -> None:
        self.visited.append(url)

    def fill(self, locator: str, value: str | None, **_kw: object) -> None:
        self.typed.append((locator, value))

    def click(self, locator: str, **_kw: object) -> None:
        self.visited.append(f"click {locator}")

    def settle(self, *_a: object, **_kw: object) -> None:
        return None


@pytest.fixture
def app():
    handle = start_app()
    yield handle
    handle.stop()


def _sessions(app, tmp_path: Path, made: list | None = None, *, fail_suffix: str | None = None,
              **kw) -> RoleSessions:
    project = build_project(app, tmp_path)
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)

    def build(*args, **kwargs):
        session = _FakeSession(*args, **kwargs)
        session.fail_suffix = fail_suffix
        if made is not None:
            made.append(session)
        return session

    return RoleSessions(project, secrets, tmp_path / "runs", paths_root=tmp_path,
                        session_cls=build, **kw)


def test_one_session_and_one_distinct_profile_dir_per_account(app, tmp_path):
    made: list[_FakeSession] = []
    with _sessions(app, tmp_path, made) as roles:
        dirs = [roles.profile_dir(a) for a in ("alice-parent", "bob-parent", "carol-school")]
        assert len(made) == 3 and len(set(dirs)) == 3
        assert {s.paths.profile_dir for s in made} == set(dirs)
        assert all(d.parent == tmp_path / "profiles" for d in dirs)
        assert {s.state.evidence_prefix for s in made} == {
            "alice-parent", "bob-parent", "carol-school"}


def test_each_session_lives_on_its_own_thread_for_start_use_and_close(app, tmp_path):
    made: list[_FakeSession] = []
    accounts = ("alice-parent", "bob-parent", "carol-school")
    with _sessions(app, tmp_path, made) as roles:
        used = {a: {roles.run_as(a, lambda s: threading.get_ident()) for _ in range(2)}
                for a in accounts}
        assert all(len(ids) == 1 for ids in used.values())
        assert len({next(iter(ids)) for ids in used.values()}) == 3
        for account in accounts:
            session = next(s for s in made if s.paths.slug.endswith(account))
            assert session.threads["start"] in used[account]
    for session in made:
        assert session.closed and session.threads["close"] == session.threads["start"]


def test_a_failed_start_closes_the_sessions_that_did_start(app, tmp_path):
    made: list[_FakeSession] = []
    roles = _sessions(app, tmp_path, made, fail_suffix="-role-carol-school")
    with pytest.raises(RuntimeError, match="would not start"):
        roles.open()
    assert made and all(s.closed for s in made)


def test_run_parallel_really_overlaps_and_isolates_a_failing_role(app, tmp_path):
    barrier = threading.Barrier(3, timeout=10)  # a serial runner would break it
    with _sessions(app, tmp_path) as roles:
        def job(_s):
            barrier.wait()
            return threading.get_ident()

        def boom(_s):
            barrier.wait()
            raise ValueError("this role crashed")

        results, errors = roles.run_parallel(
            {"alice-parent": job, "bob-parent": job, "carol-school": boom})
    assert set(results) == {"alice-parent", "bob-parent"} and len(set(results.values())) == 2
    assert set(errors) == {"carol-school"} and isinstance(errors["carol-school"], ValueError)


def test_run_as_from_inside_its_own_role_thread_runs_inline_instead_of_deadlocking(app, tmp_path):
    with _sessions(app, tmp_path) as roles:
        got = roles.run_as(
            "alice-parent", lambda s: roles.run_as("alice-parent", lambda s2: s2 is s))
        assert got is True


def test_run_parallel_with_an_unknown_id_submits_nothing(app, tmp_path):
    ran: list[str] = []
    with _sessions(app, tmp_path) as roles, pytest.raises(KeyError):
        roles.run_parallel({"alice-parent": lambda s: ran.append("a"), "nobody": lambda s: None})
    assert ran == []


def test_unknown_account_is_refused(app, tmp_path):
    with _sessions(app, tmp_path) as roles, pytest.raises(KeyError):
        roles.run_as("nobody", lambda s: None)


def test_sign_in_types_placeholders_never_values_and_scopes_the_url(app, tmp_path):
    made: list[_FakeSession] = []
    with _sessions(app, tmp_path, made) as roles:
        url = app.url(PARENT_HOST, "/login")
        roles.sign_in("alice-parent", url, user_locator="#u", password_locator="#p",
                      submit_locator="#go")
        typed = next(s for s in made if s.paths.slug.endswith("alice-parent")).typed
        assert typed == [("#u", "{{SECRET:ALICE_USER}}"), ("#p", "{{SECRET:ALICE_PASS}}")]
        assert not any(t for s in made if not s.paths.slug.endswith("alice-parent")
                       for t in s.typed)
        with pytest.raises(PlatformScopeError):  # carol's platform is the school, not the parent
            roles.sign_in("carol-school", url, user_locator="#u", password_locator="#p",
                          submit_locator="#go")
        assert not next(s for s in made if s.paths.slug.endswith("carol-school")).typed


# -- live: real Chromium, local fixture only --------------------------------------------------
@functools.cache
def _skip_if_no_chromium() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")


@pytest.fixture
def _deadline():
    faulthandler.dump_traceback_later(240, exit=True)
    yield
    faulthandler.cancel_dump_traceback_later()


def _who(roles: RoleSessions, account: str, app) -> str:
    def read(s):
        s.goto(app.url(PARENT_HOST, "/me"))
        return s.page.inner_text("#who")
    return roles.run_as(account, read)


def test_mp11_contexts_share_no_cookies_storage_or_profile_and_signout_is_local(
        app, tmp_path, _deadline):
    _skip_if_no_chromium()
    project = build_project(app, tmp_path)
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    with RoleSessions(project, secrets, tmp_path / "runs", paths_root=tmp_path) as roles:
        login = app.url(PARENT_HOST, "/login")
        for account in ("alice-parent", "bob-parent"):  # same host, same cookie name
            roles.sign_in(account, login, user_locator="#u", password_locator="#p",
                          submit_locator="#go")
        assert _who(roles, "alice-parent", app) == "signed-in-as:alice"
        assert _who(roles, "bob-parent", app) == "signed-in-as:bob"
        cookies = {a: roles.run_as(a, lambda s: s.page.context.cookies())
                   for a in ("alice-parent", "bob-parent")}
        sid = {a: [c["value"] for c in jar if c["name"] == "sid"] for a, jar in cookies.items()}
        assert len(sid["alice-parent"]) == len(sid["bob-parent"]) == 1
        assert sid["alice-parent"] != sid["bob-parent"] and len(app.sessions) == 2
        stored = {a: roles.run_as(a, lambda s: (s.goto(app.url(PARENT_HOST, "/storage")),
                                                s.page.inner_text("#stored"))[1])
                  for a in ("alice-parent", "bob-parent")}
        assert stored == {"alice-parent": "alice", "bob-parent": "bob"}
        profiles = [roles.profile_dir(a) for a in ("alice-parent", "bob-parent")]
        assert profiles[0] != profiles[1] and all(p.is_dir() for p in profiles)

        roles.run_as("alice-parent", lambda s: s.goto(app.url(PARENT_HOST, "/logout")))
        assert _who(roles, "alice-parent", app) == "anonymous"
        assert _who(roles, "bob-parent", app) == "signed-in-as:bob"
        assert list(app.sessions.values()) == ["bob"]
