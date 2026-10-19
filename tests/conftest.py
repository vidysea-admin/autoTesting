"""Shared pytest fixtures. First conftest in this repo — added at Track B3,
which needs a real local site to crawl (a fake page cannot exercise
navigation, dialogs, or network failures).

`_NoCacheHandler` is imported from `scripts/regression_proof.py` rather than
redefined, following the import pattern `tests/test_regression_proof.py`
already uses — one no-cache handler in the repo, not two.
"""

from __future__ import annotations

import functools
import http.server
import os
import shutil
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from regression_proof import _NoCacheHandler

_APPROVAL_KEY_ENV = "AUTOTESTER_APPROVAL_KEY"
_TMP_ROOT = Path(__file__).resolve().parents[1] / ".work" / "pytest-tmp"
_TMP_KEEP_SECONDS = 24 * 3600


def pytest_configure(config: pytest.Config) -> None:
    """AT-672: root every `tmp_path` / `tmp_path_factory` dir under `<repo>/.work/pytest-tmp`.

    pytest's default basetemp lives in the OS temp dir, which on Umesh's Windows host is on C:;
    C: fell to 0.34 GB free during full suites and the resulting ENOSPC showed up as false FAILs
    in unrelated tests. The repo's `.work/` (gitignored) is on the repo drive. Chosen over a
    "redirect only when TEMP is on the system drive" test because it is one rule on every OS
    and CI, not a drive-letter heuristic. A caller's explicit `--basetemp` wins; xdist workers
    keep the per-worker dir their controller gave them. Each run gets its own short dir (so
    concurrent runs never delete each other's files) and runs older than a day are pruned."""
    if config.option.basetemp is not None or hasattr(config, "workerinput"):
        return
    _TMP_ROOT.mkdir(parents=True, exist_ok=True)  # pytest mkdirs basetemp without parents
    run_dir = _TMP_ROOT / f"r{os.getpid()}-{int(time.time())}"
    config.option.basetemp = run_dir
    config._at672_redirected = True  # type: ignore[attr-defined]
    if _TMP_ROOT.is_dir():
        cutoff = time.time() - _TMP_KEEP_SECONDS
        for old in _TMP_ROOT.iterdir():
            try:
                if old.is_dir() and old.stat().st_mtime < cutoff:
                    shutil.rmtree(old, ignore_errors=True)
            except OSError:
                pass  # pruning is best-effort; never fail a run over it


@pytest.fixture(scope="session", autouse=True)
def _approval_signing_key() -> Iterator[None]:
    """AT-110: every `RunApproval` is now signed with an HMAC keyed from
    `AUTOTESTER_APPROVAL_KEY`. Setting it here, for every test, means the many
    existing fixtures across the suite that grant a fixture approval
    (`crawl_fake.grant_crawl_approval`, `test_consent.approval()`, ...) need
    only add `.sign()` at the construction site — the key itself is never a
    per-file concern.

    SESSION-scoped and plain `os.environ` rather than the (function-scoped
    only) `monkeypatch` fixture: several fixtures that sign an approval during
    their own setup are themselves `scope="module"` (e.g.
    `test_explore_modal.py::panel_crawl`), and pytest instantiates
    higher-scoped fixtures BEFORE function-scoped ones for the same test — a
    function-scoped autouse fixture had already set the key too late for them
    (measured: `SigningKeyMissing` from inside a module-scoped fixture's own
    `.sign()` call). `setdefault` leaves an already-exported real value alone,
    mirroring `core.env.load_repo_env`'s "existing environment variables win".
    Deliberately NOT the real `.env` (`PYTEST_CURRENT_TEST` already keeps
    `core.env.load_repo_env` from touching it): a test that wants to exercise
    the "no key configured" refusal uses the function-scoped `monkeypatch`
    fixture's `delenv("AUTOTESTER_APPROVAL_KEY")` over this — `monkeypatch`
    restores whatever was there before, session-set or not."""
    had_it = _APPROVAL_KEY_ENV in os.environ
    os.environ.setdefault(_APPROVAL_KEY_ENV, "test-only-signing-key-never-a-real-secret")
    yield
    if not had_it:
        os.environ.pop(_APPROVAL_KEY_ENV, None)


@pytest.fixture(autouse=True)
def _inline_run_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-203: `POST /projects/<slug>/run` now enqueues and returns at once, so a test that asserts
    the finished run would race a background thread. Every test therefore gets a fresh queue
    whose worker runs the job inline, in the request; the queue's own scheduling (limit,
    single-flight, queued state) is tested in `tests/test_run_queue.py` with a manual spawner.

    A runner crash is RE-RAISED out of the request (AT-866): the real queue records it as
    `failed` and carries on, which would let a test stay green over a run that never worked,
    as every inline-run test did before this fixture existed. A gate refusal (`RunRefused`)
    is a normal answer and stays quiet."""
    from autotester.ui import run_queue

    crashes: list[Exception] = []

    def runner(entry: run_queue.QueueEntry) -> None:
        try:
            run_queue._registered_runner(entry)
        except run_queue.RunRefused:
            raise
        except Exception as exc:
            crashes.append(exc)
            raise

    def spawn(job: Callable[[], None]) -> None:
        job()
        if crashes:
            first = crashes[0]
            crashes.clear()
            raise first

    monkeypatch.setattr(run_queue, "_QUEUE", run_queue.RunQueue(spawn=spawn, runner=runner))


@pytest.fixture(scope="session", autouse=True)
def _ui_test_host() -> Iterator[None]:
    """AT-758: the UI refuses any Host outside its allow-list, and `TestClient` names the host
    `testserver`. Listing it for the whole session keeps every UI test as it was; a test of the
    guard itself `monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS")` to see the real default."""
    had_it = "AUTOTESTER_ALLOWED_HOSTS" in os.environ
    os.environ.setdefault("AUTOTESTER_ALLOWED_HOSTS", "testserver")
    yield
    if not had_it:
        os.environ.pop("AUTOTESTER_ALLOWED_HOSTS", None)


@pytest.fixture(scope="session")
def serve_dir() -> Iterator[Callable[[Path], str]]:
    """Serve a directory over HTTP on an ephemeral localhost port.

    Yields a factory: `base_url = serve_dir(some_directory)`. Every server
    started through it is shut down at teardown, so a test never leaks a
    thread or a port.
    """
    servers: list[http.server.ThreadingHTTPServer] = []

    def _serve(directory: Path) -> str:
        handler = functools.partial(_NoCacheHandler, directory=str(directory))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield _serve

    for server in servers:
        server.shutdown()
        server.server_close()

# -- the mutation instrument's synthetic project (C7) ------------------------
#
# Registered here rather than imported: importing a fixture shadows the test's
# own parameter name, which ruff flags as F811 on every use. Named
# `mutation_repo` rather than `repo` because conftest fixtures are visible to
# the whole suite and a bare `repo` is too generic to own globally.

from tests_mutation_fixtures import MODULE, TESTS  # noqa: E402


@pytest.fixture
def mutation_repo(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts" / "mod.py").write_text(MODULE, encoding="utf-8")
    (tmp_path / "tests" / "test_mod.py").write_text(TESTS, encoding="utf-8")
    return tmp_path


def spec(**overrides) -> dict:
    mutation = {
        "name": "threshold broken", "file": "scripts/mod.py",
        "old": 'if value > 10:', "new": 'if value > 0:',
        "kills": ["test_small_values_are_small"],
    }
    mutation.update(overrides.pop("mutation", {}))
    return {"tests": "tests/test_mod.py", "mutations": [mutation], **overrides}


BIDI_SITE = Path(__file__).resolve().parent / "fixtures" / "bidi_site"


@pytest.fixture(scope="module")
def page_factory(serve_dir: Callable[[Path], str]):
    """A real Chromium page over tests/fixtures/bidi_site, per module.

    Lives here rather than in either visual-order test file: both of them need
    it, and a copy in each is the "one concept, two places" the design rules
    call a bug. Module-scoped, so each file gets its own browser.
    """
    playwright = pytest.importorskip("playwright.sync_api")
    base = serve_dir(BIDI_SITE)
    runner = None
    try:
        runner = playwright.sync_playwright().start()
        browser = runner.chromium.launch(headless=True)
    except Exception as exc:  # browser binary missing on this machine
        # stop the driver: a started-but-never-stopped one leaves a running asyncio
        # loop on this thread and breaks every later TestClient/asyncio.run test.
        if runner is not None:
            runner.stop()
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    page = browser.new_page()

    def visit(name: str) -> str:
        page.goto(f"{base}/{name}")
        page.wait_for_load_state("domcontentloaded")
        return name

    yield page, visit
    browser.close()
    runner.stop()




# -- T-204: every TestClient is signed in as the suite admin ----------------------
#
# Adding the login gate (auth.md AU16) makes every route need a session. One
# session-scoped patch signs each TestClient request in as an admin in the test's own
# scratch store (tests/auth_login_fixture.py), so no existing assertion changes.
# The auth tests turn it off with AUTOTESTER_TEST_NO_AUTO_LOGIN=1.


@pytest.fixture(scope="session", autouse=True)
def _signed_in_test_clients(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    import auth_login_fixture
    from starlette.testclient import TestClient

    from autotester.auth import audit
    from autotester.ui.auth_middleware import SESSION_COOKIES

    original = TestClient.request
    suite_auth_dir = str(tmp_path_factory.mktemp("suite-auth"))

    def _request(self, method, url, *args, **kwargs):
        if not auth_login_fixture.enabled():
            return original(self, method, url, *args, **kwargs)
        borrowed = not os.environ.get("AUTOTESTER_ROOT") and "AUTOTESTER_AUTH_DIR" not in os.environ
        real_root = audit.repo_root
        if borrowed:  # never the real repo's .auth/ store, nor its .work/audit.jsonl (P7)
            os.environ["AUTOTESTER_AUTH_DIR"] = suite_auth_dir
            audit.repo_root = lambda: Path(suite_auth_dir)
        try:
            token = auth_login_fixture.ensure_session()
            for name in SESSION_COOKIES:  # the plain and the Secure `__Host-` name (AU3)
                self.cookies.set(name, token)
            return original(self, method, url, *args, **kwargs)
        finally:
            if borrowed:
                os.environ.pop("AUTOTESTER_AUTH_DIR", None)
                audit.repo_root = real_root

    TestClient.request = _request
    yield
    TestClient.request = original


# -- the live-port wiring fixtures (g11-oracle-wiring) -------------------------
# Registered here, not imported into each test module, for the F811 reason above.
from role_port_wired import live_deadline, probed_port, wired_port  # noqa: E402,F401
