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
import sys
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from regression_proof import _NoCacheHandler

_APPROVAL_KEY_ENV = "AUTOTESTER_APPROVAL_KEY"


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
    try:
        runner = playwright.sync_playwright().start()
        browser = runner.chromium.launch(headless=True)
    except Exception as exc:  # browser binary missing on this machine
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    page = browser.new_page()

    def visit(name: str) -> str:
        page.goto(f"{base}/{name}")
        page.wait_for_load_state("domcontentloaded")
        return name

    yield page, visit
    browser.close()
    runner.stop()


