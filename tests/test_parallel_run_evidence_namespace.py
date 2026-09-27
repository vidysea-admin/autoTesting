"""AT-572 (fix cycle 3): `default_session_factory` must give each parallel
case's session its own evidence namespace under the shared `run_dir`, not
just its own login profile -- otherwise two cases' first screenshot both
land at `01-...png` and the second write clobbers the first (checker's live
Mode D run: two cases both referenced `01-step01-navigate.png`; the run dir
held 4 PNGs for 6 captured steps). Split from `test_parallel_run.py` at the
300-line cap. Contract: qa/contracts/parallel-run.md PR2.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_parallel_run import _case, _project

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.stages.parallel_run import default_session_factory


class _FakePage:
    """Writes distinguishable bytes per instance. A real screenshot's bytes
    differ page to page; this fake makes that observable without a real
    browser (`start()` is monkeypatched out, exactly as `test_ui_runs*.py`
    already does for the non-browser test suite)."""

    def __init__(self, content: bytes) -> None:
        self._content = content
        self.url = "https://p1.test/"

    def add_style_tag(self, content: str) -> None:
        pass

    def screenshot(self, path: str, full_page: bool = False) -> None:
        Path(path).write_bytes(self._content)


def _secrets(tmp_path: Path) -> SecretStore:
    """A real `SecretStore` over an isolated, never-real `.env` (`tmp_path`,
    not the repo root) -- `screenshot()`'s `_record` calls `self.secrets.
    redactor()`, so a bare `None` would crash, but nothing here may read the
    real `.env`."""
    project = _project()
    paths = ProjectPaths(project.slug, tmp_path)
    return SecretStore.load(project, paths.env_file, strict=False)


def test_default_session_factory_gives_each_case_its_own_evidence_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-572/PR2: two cases with different first pages, run one after the
    other through the same factory (mirroring how `run_cases` actually
    drives them), must get distinct screenshot paths holding different
    bytes -- never the same `01-...` filename in the shared `run_dir`."""
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    run_dir = tmp_path / "runs" / "run_1"
    run_dir.mkdir(parents=True)  # start() is mocked out; do what it would have done
    factory = default_session_factory(
        _project(max_parallel=2), secrets=_secrets(tmp_path), run_dir=run_dir,
    )

    home_case, login_case = _case(0), _case(1)

    home_session = factory(home_case)
    home_session._page = _FakePage(b"HOMEPAGE-SCREENSHOT-BYTES")
    home_evidence = home_session.screenshot("step01-navigate")

    login_session = factory(login_case)
    login_session._page = _FakePage(b"LOGIN-PAGE-SCREENSHOT-BYTES")
    login_evidence = login_session.screenshot("step01-navigate")

    assert home_evidence.path != login_evidence.path
    home_bytes = (run_dir / home_evidence.path).read_bytes()
    login_bytes = (run_dir / login_evidence.path).read_bytes()
    assert home_bytes == b"HOMEPAGE-SCREENSHOT-BYTES"
    assert login_bytes == b"LOGIN-PAGE-SCREENSHOT-BYTES"
    assert home_bytes != login_bytes


def test_serial_path_is_unaffected_evidence_path_stays_a_bare_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The serial route never sets `evidence_prefix` (it builds `BrowserSession`
    directly, not through `default_session_factory`) -- confirm a session with
    no prefix still records a bare filename, exactly as every existing reader
    (`grade.py`, `routes_report.py`) already expects."""
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    project = _project()
    paths = ProjectPaths(project.slug, tmp_path)
    run_dir = tmp_path / "run_serial"
    run_dir.mkdir(parents=True)  # start() is mocked out; do what it would have done
    session = BrowserSession(project, _secrets(tmp_path), run_dir, paths)
    session._page = _FakePage(b"SERIAL-BYTES")

    evidence = session.screenshot("step01-navigate")

    assert evidence.path == "01-step01-navigate.png"
    assert "/" not in evidence.path
