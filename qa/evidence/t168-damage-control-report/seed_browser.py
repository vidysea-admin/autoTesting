import os, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
root = Path(sys.argv[1]); root.mkdir(parents=True, exist_ok=True); os.environ["AUTOTESTER_ROOT"] = str(root)
from seed import *
s = mk_project(root, "demo")
s.save_flowspec(FlowSpec(project="demo", flows=[Flow(id=f, name=f, entry_screen="home") for f in ("f1","f2","f3")]))
case(s, "c1", "f1", title="Checkout works"); case(s, "c2", "f2", title="Profile saves")
record(s, "rel0", 1, {"f1": ["c1"], "f2": ["c2"]}, {"c1": Result.PASS, "c2": Result.PASS})
record(s, "rel1", 2, {"f1": ["c1"], "f2": ["c2"]}, {"c1": Result.FAIL, "c2": Result.PASS}, baseline="rel0", unplanned=("f3",),
       note="vs rel0", issues=[ReleaseIssue(flow_id="f1", case_id="c1", kind="failed", detail=f"Checkout 500 {XSS} token {PLAIN}"),
                              ReleaseIssue(flow_id="f3", kind="not_run", detail="flow has no plan")])
s.save_verdict("rel1", Verdict(run_id="rel1", case_id="c1", result=Result.FAIL, failures=[Failure(criterion_id="c1-a", reason="Pay button inert", fix_hint="wire Pay")]))
s.save_verdict("rel1", Verdict(run_id="rel1", case_id="c2", result=Result.PASS, failures=[]))
s.save_result("rel1", RawResult(case_id="c1", outcome=Outcome.COMPLETED, evidence=[Evidence(kind=EvidenceKind.NETWORK, path="POST https://demo.test/api/pay -> 500")]))
s.save_portal_persona(PortalPersona(project="demo", history=[PersonaRevision(at="2026-10-03T00:00:00Z", summary="billing page changed", new_screens=["a"], missing_unjudged=["billing"])]))
cov = CrawlCoverage(controls_discovered=5, controls_exercised=2, screens_reached=2, percent=40, holes=[
  CoverageHole(node_id="n1", url_template="demo.test/a", selector="#x", name="Export", reason="not_visited")])
s.save_crawl(Crawl(project="demo", id="cr1", status=CrawlStatus.STOPPED_BOUND, stop_reason="max_actions", screens=2, actions=9, coverage=cov))
# project with NO baseline
s2 = ProjectStore("nobase", root)
s2.save_project(Project(slug="nobase", name="No baseline", base_url="https://demo.test", allowed_domains=["demo.test"], secrets=[]))
s2.save_flowspec(FlowSpec(project="nobase", flows=[Flow(id="f1", name="f1", entry_screen="home")]))
case(s2, "k1", "f1", title="Only case")
record(s2, "only", 3, {"f1": ["k1"]}, {"k1": Result.PASS})
# empty project
s3 = ProjectStore("empty", root)
s3.save_project(Project(slug="empty", name="Empty", base_url="https://demo.test", allowed_domains=["demo.test"], secrets=[]))
print("seeded", root)
