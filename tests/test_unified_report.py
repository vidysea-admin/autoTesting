"""T-168 damage-control report (`qa/contracts/damage-control-report.md` DC1-DC4). Offline,
fixture-only: stored release records, verdicts, crawls and persona revisions are READ; no model,
browser or network is involved. Also covers the `release-report` CLI and the project's UI route.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from autotester.cli import app as cli_app
from autotester.schema.case import Case
from autotester.schema.crawl import CoverageHole, Crawl, CrawlCoverage
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    CrawlStatus,
    EvidenceKind,
    Outcome,
    Result,
)
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.schema.portal_persona import PersonaRevision, PortalPersona
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.unified_report import ApiFailure, ApiSection, HistorySection
from autotester.schema.verdict import Failure, Verdict
from autotester.stages import release, release_compare, unified_report
from autotester.stages.crawl_report import coverage_figure, crawl_summary
from autotester.stages.unified_report import build_report, export_unified_html
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app as ui_app

PW = "hunter2-unit-test-secret"
runner = CliRunner()
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(f"DEMO_PASSWORD={PW}\n", encoding="utf-8")
    return tmp_path


def _flows(store: ProjectStore, *ids: str) -> None:
    store.save_flowspec(FlowSpec(project="demo", flows=[
        Flow(id=f, name=f, entry_screen="home") for f in ids]))


def _store(root: Path) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])]))
    return store


def _case(store: ProjectStore, case_id: str, flow: str) -> None:
    steps = [Step(order=1, action=Action.FILL, target="password", value=PW),  # a leaked value
             Step(order=2, action=Action.CLICK, target="Save")]
    store.add_case(Case(id=case_id, project="demo", flow_id=flow, kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title=f"Case {case_id}", steps=steps))


def _release(store: ProjectStore, run_id: str, day: int, results: dict[str, Result],
             failure: bool = False) -> None:
    """Persist verdicts then the release record the way T-167's COMPARE stage does."""
    for case_id, result in results.items():
        fails = [Failure(criterion_id="c1", reason="Save did nothing", fix_hint="wire Save")]
        store.save_verdict(run_id, Verdict(run_id=run_id, case_id=case_id, result=result,
                                           failures=fails if result is Result.FAIL else []))
    scope = release.build_scope(
        store.load_project(), store, run_id=run_id, approval_id="ap", max_actions=9,
        created_at=datetime(2026, 10, day, tzinfo=UTC))
    store.save_release_scope(scope)
    store.save_release_record(release_compare.build_record(store, scope, finished=True))


def _seed(root: Path) -> ProjectStore:
    """rel0: trusted baseline (all PASS). rel1: c2 regressed, flow f3 has no plan (not run)."""
    store = _store(root)
    _flows(store, "f1", "f2")
    for case_id, flow in (("c1", "f1"), ("c2", "f2")):
        _case(store, case_id, flow)
    from autotester.schema.release import FlowPlan
    store.save_flow_plan(FlowPlan(project="demo", flow_id="f1", case_ids=["c1"]))
    store.save_flow_plan(FlowPlan(project="demo", flow_id="f2", case_ids=["c2"]))
    _release(store, "rel0", 1, {"c1": Result.PASS, "c2": Result.PASS})
    _flows(store, "f1", "f2", "f3")
    _release(store, "rel1", 2, {"c1": Result.PASS, "c2": Result.FAIL})
    store.save_result("rel1", RawResult(case_id="c2", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.NETWORK, path="POST https://demo.test/api/save -> 500"),
        Evidence(kind=EvidenceKind.NETWORK, path="GET https://demo.test/api/ok -> 200")]))
    return store


def _crawl(store: ProjectStore) -> Crawl:
    cov = CrawlCoverage(
        controls_discovered=5, controls_exercised=2, screens_reached=2,
        screens_queued_unvisited=1, percent=40, holes=[
            CoverageHole(node_id="n1", url_template="demo.test/a", selector="#x", name="Export",
                         reason="not_visited"),
            CoverageHole(node_id="n1", url_template="demo.test/a", selector="#y", name="Sync",
                         reason="bound:max_actions")])
    crawl = Crawl(project="demo", id="crawl_1", status=CrawlStatus.STOPPED_BOUND,
                  stop_reason="max_actions", screens=2, actions=9, coverage=cov)
    store.save_crawl(crawl)
    store.add_crawl_network("crawl_1", Evidence(
        kind=EvidenceKind.NETWORK, path="GET https://demo.test/api/gone -> 404"))
    return crawl


def _section(html: str, name: str) -> str:
    return re.search(rf'<section id="{name}".*?</section>', html, re.S).group(0)


def test_one_invocation_one_artifact_with_all_four_classes(root: Path) -> None:  # DC3
    _seed(root)
    out = root / "out" / "report.html"
    export_unified_html("demo", None, out, root)
    assert [p.name for p in out.parent.iterdir()] == ["report.html"]
    html = out.read_text(encoding="utf-8")
    for name in ("regression", "api", "workflows", "history", "coverage"):
        assert f'<section id="{name}"' in html
    assert "rel1" in html and "rel0" in html  # the run and its baseline are named


def test_regression_reads_the_diff_and_shows_unplanned_flow_as_not_run(root: Path) -> None:
    _seed(root)
    html = export_unified_html("demo", None, root / "r.html", root).read_text(encoding="utf-8")
    reg = _section(html, "regression")
    assert "c2" in reg and "regressed" in reg.lower()
    row = re.search(r"<tr>(?:(?!</tr>).)*>f3<.*?</tr>", reg, re.S).group(0)
    assert "not run" in row and "passed" not in row  # RR6: never folded into passed


def test_no_baseline_means_no_regression_claim(root: Path) -> None:
    store = _store(root)
    _flows(store, "f1")
    _case(store, "c1", "f1")
    from autotester.schema.release import FlowPlan
    store.save_flow_plan(FlowPlan(project="demo", flow_id="f1", case_ids=["c1"]))
    _release(store, "only", 1, {"c1": Result.PASS})
    rep = build_report(store, None)
    assert rep.regression.diff.baseline_run_id is None
    html = export_unified_html("demo", None, root / "n.html", root).read_text(encoding="utf-8")
    reg = _section(html, "regression")
    assert "no regression claim" in reg.lower() and "Regressed" not in reg


def test_dc1_crawl_coverage_figure_and_reasons_survive_and_unvisited_is_never_passed(
        root: Path) -> None:
    store = _seed(root)
    crawl = _crawl(store)
    rep = build_report(store, None)
    assert rep.coverage.rows == crawl_summary(crawl)  # the crawl page's own rows, same figure
    assert rep.coverage.incomplete is True
    html = export_unified_html("demo", None, root / "c.html", root).read_text(encoding="utf-8")
    cov = _section(html, "coverage")
    assert coverage_figure(crawl) in cov
    assert "not_visited: 1" in cov and "bound:max_actions: 1" in cov
    assert "PASS" not in cov and "passed" not in cov.lower() and "green" not in cov.lower()
    assert ("not_visited", "Export") in [(r, n[:6]) for r, n in rep.coverage.unreached]
    assert "not_visited" not in _section(html, "workflows")  # never a workflow/pass row


def test_dc2_every_section_comes_from_its_loader_and_render_computes_nothing(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed(root)
    monkeypatch.setattr(unified_report, "load_history",
                        lambda s: HistorySection(unavailable="SENTINEL-HISTORY"))
    monkeypatch.setattr(unified_report, "load_api", lambda s, r, c: ApiSection(failures=[
        ApiFailure(source="run:S", method="GET", url="https://SENTINEL-API", status=599,
                   raw="x")]))
    html = export_unified_html("demo", None, root / "d.html", root).read_text(encoding="utf-8")
    assert "SENTINEL-HISTORY" in html and "SENTINEL-API" in html and "599" in html
    assert store  # the sentinels replaced the real loaders' output, nothing else invented it
    src = (REPO / "src/autotester/stages/unified_report_render.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(len|sum|round|max|min|sorted)\(|\.count\(", src), "render computes"


def test_cr5_unjudged_screens_are_an_incomplete_diff_never_missing(root: Path) -> None:
    store = _seed(root)
    rev = PersonaRevision(at="2026-10-03T00:00:00Z", summary="screens 1 not judged",
                          missing_unjudged=["billing"])
    store.save_portal_persona(PortalPersona(project="demo", history=[rev]))
    hist = _section(export_unified_html("demo", None, root / "h.html", root)
                    .read_text(encoding="utf-8"), "history")
    assert "billing" in hist and "incomplete" in hist.lower() and "not judged" in hist.lower()
    assert "missing: 1" not in hist


def test_absence_is_unavailable_with_a_reason_never_zero_or_green(root: Path) -> None:  # C12
    store = _store(root)
    store.save_run(Run(id="run_a", project="demo"))
    rep = build_report(store, None)
    for section in (rep.regression, rep.history, rep.coverage):
        assert section.unavailable
    html = export_unified_html("demo", None, root / "e.html", root).read_text(encoding="utf-8")
    assert html.lower().count("unavailable") >= 3


def test_api_failures_are_non_ok_first_party_rows_from_run_and_crawl(root: Path) -> None:  # NA1
    store = _seed(root)
    _crawl(store)
    failures = build_report(store, None).api.failures
    assert {(f.source, f.method, f.status) for f in failures} == {
        ("run:c2", "POST", 500), ("crawl:crawl_1", "GET", 404)}
    assert all(f.url.startswith("https://demo.test/") for f in failures)


def test_re6_a_failing_case_shows_criterion_reason_fix_hint_and_repro(root: Path) -> None:
    _seed(root)
    html = export_unified_html("demo", None, root / "w.html", root).read_text(encoding="utf-8")
    wf = _section(html, "workflows")
    for needle in ("c1", "Save did nothing", "wire Save", "1. fill password", "2. click Save"):
        assert needle in wf
    assert wf.index("Case c1") < wf.index("Case c2")
    assert wf.count("Save did nothing") == 1  # the PASS case carries no failure detail


def test_dc4_no_secret_reaches_the_artifact_and_the_scanner_says_so(root: Path) -> None:
    _seed(root)
    out = export_unified_html("demo", None, root / "s.html", root)
    assert PW not in out.read_text(encoding="utf-8")
    env = {"AUTOTESTER_ROOT": str(root), "PATH": __import__("os").environ["PATH"],
           "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
    scan = [sys.executable, str(REPO / "scripts/check_no_secrets.py")]
    clean = subprocess.run([*scan, str(out)], env=env, capture_output=True, text=True)
    assert clean.returncode == 0 and "0 leak(s)" in clean.stdout
    leaky = root / "leaky.html"
    leaky.write_text(f"<p>{PW}</p>", encoding="utf-8")
    assert subprocess.run([*scan, str(leaky)], env=env, capture_output=True).returncode == 1


def test_cli_and_ui_with_no_runs_show_an_empty_state_not_a_green_report(root: Path) -> None:
    _store(root)
    result = runner.invoke(cli_app, ["release-report", "demo", "--out", str(root / "x.html")])
    assert result.exit_code == 1 and "no runs" in result.output.lower()
    page = TestClient(ui_app).get("/projects/demo/damage-report")
    assert page.status_code == 200 and "no runs" in page.text.lower() and "PASS" not in page.text


def test_cli_writes_the_report_and_the_ui_route_and_project_page_reach_it(root: Path) -> None:
    _seed(root)
    out = root / "cli.html"
    result = runner.invoke(cli_app, ["release-report", "demo", "--out", str(out)])
    assert result.exit_code == 0 and out.exists()
    client = TestClient(ui_app)
    assert 'id="regression"' in client.get("/projects/demo/damage-report").text
    assert "/projects/demo/damage-report" in client.get("/projects/demo").text
