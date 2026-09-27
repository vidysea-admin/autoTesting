"""AT-577 cycle 2 (checker verdict 9b0ccb8, cycle 1 FAIL): the entry case's
dedicated session and the serial route's shared session write into the SAME
`run_dir`, both numbering screenshots from 01 -- unprefixed, the shared
session's first write silently overwrote the entry case's file on disk.
Drives the real `stages.execute.run_case` (not faked) against a fake PAGE
whose `screenshot()` writes real, distinguishable bytes, so a collision is
provably data loss on disk, not just two same-shaped Evidence records.
Contract: qa/contracts/execute.md E4, qa/contracts/ui-run.md RU1-RU4.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_ui_runs_parallel_trace import client, scratch_root

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Result
from autotester.schema.flowspec import Step
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore

__all__ = ["client", "scratch_root"]

BASE_URL = "https://demo.test/"
OTHER_URL = "https://demo.test/other"


class _RecordingPage:
    """Just enough of a Playwright page for a NAVIGATE step + screenshot.
    Bytes written are derived from the CURRENT url, so two screenshots at
    different urls are provably different files on disk -- a path collision
    (same file, last writer wins) reads back as ONE content, not two."""

    def __init__(self, url: str) -> None:
        self.url = url

    def add_style_tag(self, content: str) -> None:
        pass

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        pass

    def wait_for_timeout(self, timeout_ms: int) -> None:
        pass

    def screenshot(self, path: str, full_page: bool = False) -> None:
        Path(path).write_bytes(self.url.encode())


def _entry_case() -> Case:
    return Case(
        project="demo", flow_id="flow-entry", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="entry", steps=[Step(order=1, action=Action.NAVIGATE, target=BASE_URL)],
    )


def _ordinary_case() -> Case:
    return Case(
        project="demo", flow_id="flow-ordinary", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="ordinary", steps=[Step(order=1, action=Action.NAVIGATE, target=OTHER_URL)],
    )


def test_entry_and_ordinary_case_screenshots_never_collide_on_disk(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": BASE_URL, "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    entry_case = store.add_case(_entry_case())
    ordinary_case = store.add_case(_ordinary_case())

    def fake_start(self):
        self._page = _RecordingPage(BASE_URL)
        self.state.run_dir.mkdir(parents=True, exist_ok=True)
        return self

    import autotester.stages.run_case_pipeline as pipeline_module
    import autotester.ui.routes_runs as routes_runs_module
    from autotester.browser.session import BrowserSession

    monkeypatch.setattr(BrowserSession, "start", fake_start)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)

    def fake_grade(rubric, result, run_id, judge, run_dir=None, secrets=None):
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")

    # run_case itself is NOT faked -- the real execute.py::run_case runs
    # against the fake page, so the real BrowserSession.screenshot() call
    # (evidence_prefix and all) is what this test exercises.
    monkeypatch.setattr(pipeline_module, "grade", fake_grade)

    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303, response.text

    run_ids = sorted(p.name for p in store.paths.runs_dir.iterdir() if p.is_dir())
    assert len(run_ids) == 1
    run_id = run_ids[0]
    results = {r.case_id: r for r in store.load_results(run_id)}
    assert set(results) == {entry_case.id, ordinary_case.id}

    entry_shots = [e for e in results[entry_case.id].evidence if e.path.endswith(".png")]
    ordinary_shots = [e for e in results[ordinary_case.id].evidence if e.path.endswith(".png")]
    assert len(entry_shots) == 1
    assert len(ordinary_shots) == 1
    entry_path, ordinary_path = entry_shots[0].path, ordinary_shots[0].path
    assert entry_path != ordinary_path, (
        f"entry and ordinary case screenshots must never share a path: {entry_path!r}"
    )

    run_dir = store.paths.run_dir(run_id)
    entry_file = run_dir / entry_path
    ordinary_file = run_dir / ordinary_path
    assert entry_file.exists(), f"{entry_file} must exist -- not silently overwritten"
    assert ordinary_file.exists(), f"{ordinary_file} must exist"
    assert entry_file.read_bytes() == BASE_URL.encode(), (
        "the entry case's own screenshot must hold the entry page's bytes, "
        "not whatever the shared session wrote last"
    )
    assert ordinary_file.read_bytes() == OTHER_URL.encode()
