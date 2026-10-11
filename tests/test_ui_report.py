"""Run history, inline screenshots, portable downloads. Contract:
qa/contracts/ui-report.md UR1-UR4.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind, EvidenceKind, Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _demo_store(scratch_root: Path) -> ProjectStore:
    store = ProjectStore("demo", scratch_root)
    store.save_project(
        Project(slug="demo", name="Demo", base_url="https://demo.test",
                allowed_domains=["demo.test"])
    )
    return store


def _seed_project_with_two_runs(scratch_root: Path) -> ProjectStore:
    store = _demo_store(scratch_root)
    for case_id, flow_id in (
        ("case_1", "flow_login"), ("case_2", "flow_login"), ("case_3", "flow_profile"),
    ):
        store.add_case(Case(
            id=case_id, project="demo", flow_id=flow_id, kind=CaseKind.BEST,
            case_class=CaseClass.HAPPY, title=f"Check {case_id}",
        ))
    for run_id, result_value in (("run_1", Result.PASS), ("run_2", Result.FAIL)):
        case_ids = ["case_1"] if run_id == "run_1" else ["case_1", "case_2", "case_3"]
        store.save_run(Run(id=run_id, project="demo", case_ids=case_ids))
        store.save_result(run_id, RawResult(case_id="case_1", outcome=Outcome.COMPLETED))
        store.save_verdict(run_id, Verdict(
            run_id=run_id, case_id="case_1", result=result_value,
            grader_provider="mock", rubric_hash="rub_x",
        ))
    return store

def test_report_lists_every_run_newest_first(client: TestClient, scratch_root: Path) -> None:
    store = _seed_project_with_two_runs(scratch_root)
    (store.paths.runs_dir / "zzz-crawl-artifacts").mkdir()

    response = client.get("/projects/demo/report")

    assert response.status_code == 200
    text = response.text
    assert text.index("run_2") < text.index("run_1")  # newest first
    assert "/projects/demo/runs/run_1" in text
    assert "/projects/demo/runs/run_2" in text
    assert "zzz-crawl-artifacts" not in text

def test_run_view_returns_404_for_a_directory_without_a_run(
    client: TestClient, scratch_root: Path
) -> None:
    store = _seed_project_with_two_runs(scratch_root)
    (store.paths.runs_dir / "crawl_latest").mkdir()

    response = client.get("/projects/demo/runs/crawl_latest")

    assert response.status_code == 404
    assert "Run not found" in response.text
    assert "No case results in this run yet" not in response.text

def test_run_view_embeds_a_real_screenshot_inline(client, scratch_root):
    store = _demo_store(scratch_root)
    run_dir = store.paths.run_dir("run_1")
    store.save_run(Run(id="run_1", project="demo", case_ids=["case_1"]))
    (run_dir / "01-shot.png").write_bytes(
        bytes.fromhex("89504e470d0a1a0a0000000d49484452")  # a real (truncated) PNG header
    )
    store.save_result("run_1", RawResult(
        case_id="case_1", outcome=Outcome.COMPLETED,
        evidence=[Evidence(kind=EvidenceKind.SCREENSHOT, path="01-shot.png", label="step 1")],
    ))
    store.save_verdict("run_1", Verdict(
        run_id="run_1", case_id="case_1", result=Result.PASS,
        grader_provider="mock", rubric_hash="rub_x",
    ))

    response = client.get("/projects/demo/runs/run_1")

    assert response.status_code == 200
    assert "data:image/png;base64," in response.text
    assert "step 1" in response.text


def test_run_view_says_so_honestly_when_a_case_has_no_screenshots(
    client: TestClient, scratch_root: Path
) -> None:
    store = _seed_project_with_two_runs(scratch_root)
    del store  # seeded results carry no evidence

    response = client.get("/projects/demo/runs/run_1")

    assert response.status_code == 200
    assert "no screenshots captured" in response.text


def test_report_offers_real_excel_and_html_downloads(client, scratch_root):
    store = _seed_project_with_two_runs(scratch_root)
    (store.paths.runs_dir / "zzz-crawl-artifacts").mkdir()

    excel = client.get("/projects/demo/report.xlsx")
    html = client.get("/projects/demo/report.html")

    assert excel.status_code == 200
    assert excel.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )
    assert len(excel.content) > 0
    assert html.status_code == 200
    assert "text/html" in html.headers["content-type"]
    assert b"Check case_1" in html.content


def test_downloads_404_for_an_unknown_project(client: TestClient, scratch_root: Path) -> None:
    assert client.get("/projects/nope/report.xlsx").status_code == 404
    assert client.get("/projects/nope/report.html").status_code == 404


def test_report_shows_an_overview_summary_not_just_a_bare_history_table(
    client: TestClient, scratch_root: Path
) -> None:
    """Umesh, on a screenshot of this page: 'no summary, no overview'."""
    _seed_project_with_two_runs(scratch_root)

    response = client.get("/projects/demo/report")

    assert response.status_code == 200
    assert "Total runs" in response.text
    assert "Latest-run pass rate" in response.text
    assert "Overall pass rate" not in response.text
    assert "0%" in response.text  # latest run FAIL; lifetime rate would be 50%
    assert "<div class='value'>3</div><div class='label'>cases covering 2 distinct flows" in (
        response.text
    )


def test_run_history_rows_use_compact_badges_not_full_size_stat_tiles(
    client: TestClient, scratch_root: Path
) -> None:
    """The old table rendered a full `.stat` tile (big serif number) per row,
    reading as a wall of oversized, meaningless numbers -- history rows must
    use the compact `.run-results` badge summary instead."""
    _seed_project_with_two_runs(scratch_root)

    response = client.get("/projects/demo/report")

    assert "class='run-results'" in response.text
    history_section = response.text.split("Run history", 1)[1]
    assert "class='stat'>" not in history_section


def test_run_view_shows_scoreboard_and_grader_not_just_a_bare_badge(
    client: TestClient, scratch_root: Path
) -> None:
    """Umesh, on a screenshot of this page: 'non informational too'."""
    store = _demo_store(scratch_root)
    store.save_run(Run(id="run_1", project="demo", case_ids=["case_1"]))
    store.save_result("run_1", RawResult(case_id="case_1", outcome=Outcome.COMPLETED))
    store.save_verdict("run_1", Verdict(
        run_id="run_1", case_id="case_1", result=Result.PASS,
        grader_provider="gemini", rubric_hash="rub_x", scoreboard="Criteria 2/2 met.",
    ))

    response = client.get("/projects/demo/runs/run_1")

    assert response.status_code == 200
    assert "Criteria 2/2 met." in response.text
    assert "judged by gemini" in response.text


def test_run_view_screenshots_link_to_a_matching_lightbox_target(
    client: TestClient, scratch_root: Path
) -> None:
    """Umesh: thumbnails were readable but too small to read detail without
    clicking -- each thumbnail must open a full-size CSS-only lightbox."""
    store = _demo_store(scratch_root)
    run_dir = store.paths.run_dir("run_1")
    store.save_run(Run(id="run_1", project="demo", case_ids=["case_1"]))
    (run_dir / "01-shot.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    store.save_result("run_1", RawResult(
        case_id="case_1", outcome=Outcome.COMPLETED,
        evidence=[Evidence(kind=EvidenceKind.SCREENSHOT, path="01-shot.png",
                            label="step 1", step_order=1)],
    ))
    store.save_verdict("run_1", Verdict(
        run_id="run_1", case_id="case_1", result=Result.PASS,
        grader_provider="mock", rubric_hash="rub_x",
    ))

    response = client.get("/projects/demo/runs/run_1")
    text = response.text

    assert "class='flow-step' href='#lb-0-0'" in text
    assert "id='lb-0-0'" in text
    assert "class='lightbox'" in text


def test_run_view_orders_the_step_flow_by_step_order_not_evidence_order(
    client: TestClient, scratch_root: Path
) -> None:
    """The DFS-style trace must show the literal sequence the case walked --
    if evidence arrives out of order, step_order must still win."""
    store = _demo_store(scratch_root)
    run_dir = store.paths.run_dir("run_1")
    store.save_run(Run(id="run_1", project="demo", case_ids=["case_1"]))
    (run_dir / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (run_dir / "b.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    store.save_result("run_1", RawResult(
        case_id="case_1", outcome=Outcome.COMPLETED,
        evidence=[
            Evidence(kind=EvidenceKind.SCREENSHOT, path="b.png", label="second", step_order=2),
            Evidence(kind=EvidenceKind.SCREENSHOT, path="a.png", label="first", step_order=1),
        ],
    ))
    store.save_verdict("run_1", Verdict(
        run_id="run_1", case_id="case_1", result=Result.PASS,
        grader_provider="mock", rubric_hash="rub_x",
    ))

    response = client.get("/projects/demo/runs/run_1")
    text = response.text

    assert text.index(">first<") < text.index(">second<")


def test_run_view_shows_failure_reasons_for_a_fail(client, scratch_root):
    from autotester.schema.verdict import Failure

    store = _demo_store(scratch_root)
    store.save_run(Run(id="run_1", project="demo", case_ids=["case_1"]))
    store.save_result("run_1", RawResult(case_id="case_1", outcome=Outcome.COMPLETED))
    store.save_verdict("run_1", Verdict(
        run_id="run_1", case_id="case_1", result=Result.FAIL,
        grader_provider="gemini", rubric_hash="rub_x",
        failures=[Failure(criterion_id="c1", reason="login form still visible",
                           fix_hint="check the redirect wait")],
    ))

    response = client.get("/projects/demo/runs/run_1")

    assert "login form still visible" in response.text
    assert "check the redirect wait" in response.text


@pytest.mark.parametrize("counts", [None, {"static": 0, "behavioural": 2, "adversarial": 5}])
def test_run_view_reports_measured_class_counts_or_legacy_absence(client, scratch_root, counts):
    store = _seed_project_with_two_runs(scratch_root)
    run = store.load_run("run_2")
    store.save_run(run.model_copy(update={"catalog_runnable_counts": counts}))
    response = client.get("/projects/demo/runs/run_2")
    assert response.status_code == 200
    assert "Catalog runnable-class counts" in response.text
    if counts is None:
        assert "NOT_RECORDED" in response.text
    else:
        assert all(f"{tier}: {value}" in response.text for tier, value in counts.items())


def test_run_view_lists_cheap_tier_failures_first_ahead_of_passes(client, scratch_root):
    """CT6(4)/D-071: a failed static case precedes a failed adversarial one, in a
    failures section ahead of passes -- not case-id order (b_adv sorts before c_static)."""
    store = _demo_store(scratch_root)
    rows = (("a_pass", CaseClass.HAPPY, Result.PASS),
            ("b_adv", CaseClass.SERVER_ERROR, Result.FAIL),
            ("c_static", CaseClass.INPUT_EMPTY, Result.FAIL))
    store.save_run(Run(id="run_1", project="demo", case_ids=[r[0] for r in rows]))
    for cid, case_class, result in rows:
        store.add_case(Case(id=cid, project="demo", flow_id="f", kind=CaseKind.BEST,
                            case_class=case_class, title=f"T {cid}"))
        store.save_result("run_1", RawResult(case_id=cid, outcome=Outcome.COMPLETED))
        store.save_verdict("run_1", Verdict(run_id="run_1", case_id=cid, result=result,
                                            grader_provider="mock", rubric_hash="rub_x"))
    text = client.get("/projects/demo/runs/run_1").text
    assert text.index("<h2>Failures</h2>") < text.index("T c_static") < text.index("T b_adv")
    assert text.index("T b_adv") < text.index("T a_pass")
