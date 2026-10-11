import os, re, sys, tempfile, subprocess, html as H
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from seed import *
from autotester.stages.unified_report import unified_html, export_unified_html
from typer.testing import CliRunner
from autotester.cli import app

def build(secret):
    d = Path(tempfile.mkdtemp(prefix="s168-")); os.environ["AUTOTESTER_ROOT"] = str(d)
    s = mk_project(d)
    S = secret
    s.save_flowspec(FlowSpec(project="demo", flows=[Flow(id="f1", name=f"flow {S}", entry_screen="home"), Flow(id="f2", name="f2", entry_screen="home")]))
    case(s, "c1", "f1", title=f"Title {S} {XSS}", steps=[Step(order=1, action=Action.FILL, target=f"pw {S}", value=S), Step(order=2, action=Action.CLICK, target="Save")])
    case(s, "c2", "f2")
    for (rid, day, res, base) in (("rel0", 1, {"c1": Result.PASS, "c2": Result.PASS}, None), ("rel1", 2, {"c1": Result.FAIL, "c2": Result.PASS}, "rel0")):
        record(s, rid, day, {"f1": ["c1"], "f2": ["c2"]}, res, baseline=base, note=f"note {S} {XSS}",
               reason=f"reason {S}", flagged=(rid == "rel1"), git_sha=f"sha-{S}",
               issues=[ReleaseIssue(flow_id="f1", case_id="c1", kind="failed", detail=f"detail {S} {XSS}")] if rid == "rel1" else [])
        for c, r in res.items():
            s.save_verdict(rid, Verdict(run_id=rid, case_id=c, result=r, failures=[Failure(criterion_id=f"crit {S}", reason=f"reason {S} {XSS}", fix_hint=f"fix {S}")] if r is Result.FAIL else []))
    s.save_result("rel1", RawResult(case_id="c1", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.NETWORK, path=f"POST https://demo.test/api/save?token={S}&x=1 -> 500")]))
    s.save_portal_persona(PortalPersona(project="demo", history=[PersonaRevision(at="2026-10-03T00:00:00Z", summary=f"sum {S}", new_screens=[f"scr {S}"], missing_unjudged=[f"u {S}"])]))
    cov = CrawlCoverage(controls_discovered=5, controls_exercised=2, screens_reached=2, percent=40, holes=[
        CoverageHole(node_id="n1", url_template=f"demo.test/a?k={S}", selector="#x", name=f"Export {S}", reason="not_visited")])
    s.save_crawl(Crawl(project="demo", id="cr1", status=CrawlStatus.STOPPED_BOUND, stop_reason=f"max {S}", screens=2, actions=9, coverage=cov))
    s.add_crawl_network("cr1", Evidence(kind=EvidenceKind.NETWORK, path=f"GET https://demo.test/g?pw={S} -> 404"))
    return d, s

for label, S in (("plain", PLAIN), ("special", SPECIAL)):
    d, s = build(S)
    out = d / "out.html"
    r = CliRunner().invoke(app, ["release-report", "demo", "--out", str(out)])
    htmltxt = out.read_text(encoding="utf-8")
    esc = H.escape(S); esc_q = H.escape(S, quote=False)
    leak_raw = S in htmltxt; leak_esc = (esc in htmltxt) or (esc_q in htmltxt)
    leak_cli = S in r.output
    print(f"[{label}] cli exit={r.exit_code} raw_in_html={leak_raw} escaped_form_in_html={leak_esc} in_cli_output={leak_cli}")
    env = {"AUTOTESTER_ROOT": str(d), "PATH": os.environ["PATH"], "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    sc = subprocess.run([sys.executable, r"D:\autoTesting\.worktrees\t168-damage-control-report\scripts\check_no_secrets.py", str(out)], env=env, capture_output=True, text=True)
    print(f"   scanner exit={sc.returncode}: {sc.stdout.strip()[-160:]}")
    # which fields leak
    if leak_esc:
        for m in re.finditer(re.escape(esc), htmltxt):
            ctx = htmltxt[max(0, m.start()-35):m.start()]
            print("   leak ctx:", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", ctx))[-40:])
    # xss
    print(f"   raw <script in html: {'<script' in htmltxt.lower()}, raw <img: {'<img' in htmltxt.lower()}")
    if label == "plain": keep = out
