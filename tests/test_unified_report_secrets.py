"""T-168 DC4 repair (cycle 1): a secret with HTML-special characters never reaches the report.

`Redactor.scrub` matches exact bytes, so a secret containing `& < > '` must be removed from the
report OBJECT before the renderer escapes it. The secret is planted in every text field the report
carries; neither its raw nor its HTML-escaped form may appear in the HTML or the CLI output.
"""

from __future__ import annotations

import html as htmllib
import subprocess
import sys
from pathlib import Path

import pytest
from test_unified_report import REPO, _flows, _store
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
from autotester.schema.flowspec import Step
from autotester.schema.portal_persona import PersonaRevision, PortalPersona
from autotester.schema.release import FlowPlan, ReleaseIssue
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Failure, Verdict
from autotester.stages import release, release_compare
from autotester.stages.unified_report import build_report, load_workflows
from autotester.store.project_store import ProjectStore

S = "p&ss<w>o'rdQ9"
runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(f'DEMO_PASSWORD="{S}"\n', encoding="utf-8")
    return tmp_path


def _forms() -> list[str]:
    return [S, htmllib.escape(S), htmllib.escape(S, quote=False)]


def _seed_everywhere(root: Path) -> ProjectStore:
    """Plant S in every text field the report carries (flow, case, verdict, record, API, persona,
    crawl). The record is built the way COMPARE builds it, then given the free-text fields."""
    store = _store(root)
    _flows(store, f"f-{S}")
    store.add_case(Case(
        id="c1", project="demo", flow_id=f"f-{S}", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title=f"Title {S}", steps=[Step(order=1, action=Action.FILL, target=f"pw {S}", value=S)]))
    store.save_flow_plan(FlowPlan(project="demo", flow_id=f"f-{S}", case_ids=["c1"]))
    store.save_verdict("rel1", Verdict(run_id="rel1", case_id="c1", result=Result.FAIL, failures=[
        Failure(criterion_id=f"crit-{S}", reason=f"reason {S}", fix_hint=f"fix {S}")]))
    scope = release.build_scope(store.load_project(), store, run_id="rel1", approval_id="ap",
                                max_actions=9, git_sha=f"sha-{S}")
    store.save_release_scope(scope)
    rec = release_compare.build_record(store, scope, finished=True)
    store.save_release_record(rec.model_copy(update={
        "flagged_bad": True, "flagged_reason": f"flagged {S}",
        "issues": [ReleaseIssue(flow_id=f"f-{S}", case_id="c1", kind="failed", detail=f"d {S}")]}))
    store.save_result("rel1", RawResult(case_id="c1", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.NETWORK, path=f"POST https://demo.test/a?t={S} -> 500")]))
    store.save_portal_persona(PortalPersona(project="demo", history=[PersonaRevision(
        at="2026-10-03T00:00:00Z", summary=f"sum {S}", new_screens=[f"n {S}"],
        changed_screens=[f"c {S}"], missing_screens=[f"m {S}"], broken_screens=[f"b {S}"],
        missing_unjudged=[f"u {S}"])]))
    hole = CoverageHole(node_id="n1", url_template=f"demo.test/a?k={S}", selector="#x",
                        name=f"Export {S}", reason="not_visited")
    store.save_crawl(Crawl(project="demo", id="cr1", status=CrawlStatus.STOPPED_BOUND,
                           stop_reason=f"max {S}", screens=2, actions=9, coverage=CrawlCoverage(
                               controls_discovered=5, controls_exercised=2, screens_reached=2,
                               percent=40, holes=[hole])))
    store.add_crawl_network("cr1", Evidence(
        kind=EvidenceKind.NETWORK, path=f"GET https://demo.test/g?pw={S} -> 404"))
    return store


def test_dc4_special_character_secret_is_absent_raw_and_escaped_in_html_and_cli(
        root: Path) -> None:
    _seed_everywhere(root)
    out = root / "cli.html"
    result = runner.invoke(cli_app, ["release-report", "demo", "--out", str(out)])
    assert result.exit_code == 0, result.output
    page = out.read_text(encoding="utf-8")
    assert "fix " in page and "Export" in page  # the planted fields really rendered
    for form in _forms():
        assert form not in page, form
        assert form not in result.output, form
    env = {"AUTOTESTER_ROOT": str(root), "PATH": __import__("os").environ["PATH"],
           "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
    scan = subprocess.run([sys.executable, str(REPO / "scripts/check_no_secrets.py"), str(out)],
                          env=env, capture_output=True, text=True)
    assert scan.returncode == 0 and "0 leak(s)" in scan.stdout


def test_dc4_report_object_is_clean_before_it_is_rendered(root: Path) -> None:
    store = _seed_everywhere(root)
    dumped = build_report(store, None).model_dump_json()
    for form in _forms():
        assert form not in dumped, form


def test_dc4_workflow_loader_scrubs_repro_steps_on_its_own(root: Path) -> None:
    store = _seed_everywhere(root)
    steps = load_workflows(store, "rel1").cases[0].repro_steps
    assert steps and not any(form in line for line in steps for form in _forms())

