"""AT-576, live: the real defect a faked `BrowserSession.start` cannot see.

`test_ui_runs_serial_entry_order.py` proves the ORDERING decision with a fake
session (cheap, always runs). This file proves the ordering actually FIXES
the live bug: with a real `BrowserSession`, starting one sync Playwright
driver while another is already live on the same thread raises "It looks
like you are using Playwright Sync API inside the asyncio loop" -- a fake
`.start()`/`.close()` is a no-op, so no unit test using one could ever have
caught AT-576 (it shipped for three weeks, 939af44 to this fix, entirely
behind that blind spot).

Only the AI provider is faked (`LangChainFallbackProvider` -> `MockProvider`,
same seam `test_ui_runs_parallel_trace.py::test_a_real_run_writes_a_trace_
with_at_least_one_span` already uses) -- `BrowserSession` itself is real,
driven against a local fixture site (`tests/fixtures/regression_site`) on an
isolated `AUTOTESTER_ROOT`. Skipped when Chromium is unavailable, same as
every other `_live.py` file in this suite.

RAM-gated by project convention (qa/contracts/core-invariants.md, `/maker`
dispatch prompt): a real Chromium launch is only attempted when free RAM is
comfortably above the floor a shared host needs kept back for everything
else. Below that floor the test SKIPS with the measurement instead of
launching a browser under memory pressure.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

RAM_FLOOR_MB = 3584.0  # 3.5 GB, this project's own convention (parallel_run.py's _RAM_FLOOR_MB)


def _free_ram_mb() -> float:
    from autotester.stages.parallel_run import _free_ram_mb
    return _free_ram_mb()


@pytest.fixture(scope="module")
def _regression_site(tmp_path_factory: pytest.TempPathFactory,
                     serve_dir: Callable[[Path], str]) -> str:
    pytest.importorskip("playwright")
    site_dir = Path(__file__).resolve().parent / "fixtures" / "regression_site"
    return serve_dir(site_dir)


def test_a_serial_run_mixing_an_entry_case_with_ordinary_cases_does_not_500(
    _regression_site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1 entry case (navigates to base_url) + 2 ordinary cases, driven
    through the real `/projects/<slug>/run` route against a real, isolated
    `BrowserSession` for each. Before AT-576's fix: 500 (nested sync
    Playwright). After: 303, and all 3 results + the Run are saved."""
    free_mb = _free_ram_mb()
    if free_mb < RAM_FLOOR_MB:
        pytest.skip(
            f"RAM gate: {free_mb:.0f} MB free < {RAM_FLOOR_MB:.0f} MB floor -- "
            "not launching a real Chromium under memory pressure (AT-576 live check)"
        )

    from fastapi.testclient import TestClient

    from autotester.providers.mock import MockProvider
    from autotester.schema.case import Case
    from autotester.schema.enums import Action, CaseClass, CaseKind
    from autotester.schema.flowspec import Step
    from autotester.schema.verdict import Judgment
    from autotester.store.project_store import ProjectStore
    from autotester.ui.app import app

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    base = _regression_site + "/"
    client = TestClient(app)

    client.post("/onboard", data={
        "slug": "rd", "name": "Regression Demo", "base_url": base,
        "allowed_domains": "127.0.0.1",
    })
    store = ProjectStore("rd", tmp_path)
    project = store.load_project()
    assert project is not None
    store.save_project(project.model_copy(update={"headed": False}))

    entry_case = store.add_case(Case(
        project="rd", flow_id="flow-home", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Homepage loads", steps=[Step(order=1, action=Action.NAVIGATE, target=base)],
    ))
    login_case = store.add_case(Case(
        project="rd", flow_id="flow-login", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Login page loads",
        steps=[Step(order=1, action=Action.NAVIGATE, target=base + "login.html")],
    ))
    home_again_case = store.add_case(Case(
        project="rd", flow_id="flow-home2", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Sign-in link is clickable", steps=[
            Step(order=1, action=Action.NAVIGATE, target=base + "index.html"),
            Step(order=2, action=Action.CLICK, target="a"),
        ],
    ))

    judgment = Judgment(result="PASS", criteria_met=1, criteria_total=1)
    judge = MockProvider(model="mock", responses={"judge": [judgment] * 10})

    import autotester.ui.routes_runs as routes_runs_module
    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", lambda: judge)

    response = client.post("/projects/rd/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    run_ids = sorted(p.name for p in store.paths.runs_dir.iterdir() if p.is_dir())
    assert len(run_ids) == 1, "the Run must be saved even with an entry case in the mix"
    run_id = run_ids[0]
    run = store.load_run(run_id)
    assert run is not None

    results = {r.case_id: r for r in store.load_results(run_id)}
    assert set(results) == {entry_case.id, login_case.id, home_again_case.id}
    assert len(results) == 3

    # AT-577 cycle 2 (checker verdict 9b0ccb8): the entry case's dedicated
    # session and the shared session used to write screenshots into the SAME
    # run_dir, both numbering from 01 -- the shared session's first write
    # silently overwrote the entry case's. With evidence_prefix set on the
    # entry session, every case's screenshots live under their own path, so
    # no two cases ever collide and none is silently lost.
    total_steps = len(entry_case.steps) + len(login_case.steps) + len(home_again_case.steps)
    png_paths = [e.path for r in results.values() for e in r.evidence if e.path.endswith(".png")]
    assert len(png_paths) == total_steps, (
        f"one screenshot per step, none overwritten: {len(png_paths)} PNGs for "
        f"{total_steps} steps -- {png_paths}"
    )
    assert len(set(png_paths)) == len(png_paths), (
        f"no screenshot path may be shared across cases: {png_paths}"
    )
    run_dir = store.paths.run_dir(run_id)
    for path in png_paths:
        assert (run_dir / path).exists(), f"{run_dir / path} must exist on disk"
