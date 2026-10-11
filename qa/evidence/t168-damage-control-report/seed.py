"""Checker-built seed for T-168 probes. Not product code."""
from __future__ import annotations
import sys
from datetime import UTC, datetime
from pathlib import Path
from autotester.schema.case import Case
from autotester.schema.crawl import CoverageHole, Crawl, CrawlCoverage
from autotester.schema.enums import Action, CaseClass, CaseKind, CrawlStatus, EvidenceKind, Outcome, Result
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.schema.portal_persona import PersonaRevision, PortalPersona
from autotester.schema.project import Project, SecretRef
from autotester.schema.release import (FlowOutcome, FlowPlan, RegressionDiff, ReleaseIssue,
                                       ReleaseRecord, ReleaseScope)
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.verdict import Failure, Verdict
from autotester.store.project_store import ProjectStore

PLAIN = "Zq9-plainChecker7"
SPECIAL = "p&ss<w>o'rdQ9"
XSS = "<script>window.__xss=1</script><img src=x onerror=window.__xss=2>"

def mk_project(root: Path, slug="demo", plant=True) -> ProjectStore:
    (root / ".env").write_text(f'DEMO_PLAIN={PLAIN}\nDEMO_SPECIAL="{SPECIAL.replace(chr(34), chr(92)+chr(34))}"\n', encoding="utf-8")
    s = ProjectStore(slug, root)
    s.save_project(Project(slug=slug, name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PLAIN", domains=["demo.test"]), SecretRef(key="DEMO_SPECIAL", domains=["demo.test"])]))
    return s

def record(s, run_id, day, cases_by_flow, results, *, finished=True, flagged=False, reason=None,
           unplanned=(), baseline=None, note="", issues=(), git_sha=None, flow_ids=None):
    plans = [FlowPlan(project=s.paths.slug, flow_id=f, case_ids=c) for f, c in cases_by_flow.items()]
    exp = list(cases_by_flow) + list(unplanned)
    scope = ReleaseScope(run_id=run_id, project=s.paths.slug, approval_id="ap", max_actions=9, wall_clock_s=60,
        expected_flow_ids=exp, plans=plans, unplanned_flow_ids=list(unplanned), git_sha=git_sha,
        created_at=datetime(2026, 10, day, tzinfo=UTC))
    s.save_release_scope(scope)
    flows = [FlowOutcome(flow_id=f, status=("passed" if all(results.get(c) is Result.PASS for c in cs) else "failed"), case_ids=cs)
             for f, cs in cases_by_flow.items()] + [FlowOutcome(flow_id=f, status="not_run") for f in unplanned]
    rec = ReleaseRecord(run_id=run_id, project=s.paths.slug, approval_id="ap", git_sha=git_sha, scope=scope,
        finished=finished, flagged_bad=flagged, flagged_reason=reason, results=results, flows=flows,
        issues=list(issues), diff=RegressionDiff(baseline_run_id=baseline, note=note,
        regressed=[c for c, r in results.items() if baseline and r is not Result.PASS]))
    s.save_release_record(rec)

def case(s, cid, flow, title=None, steps=None):
    steps = steps or [Step(order=1, action=Action.FILL, target="pw", value=PLAIN), Step(order=2, action=Action.CLICK, target="Save")]
    s.add_case(Case(id=cid, project=s.paths.slug, flow_id=flow, kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                    title=title or f"Case {cid}", steps=steps))
