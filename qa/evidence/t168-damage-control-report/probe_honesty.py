import os, re, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from seed import *
from autotester.stages.unified_report import build_report, export_unified_html, unified_html

def fresh():
    d = Path(tempfile.mkdtemp(prefix="p168-")); os.environ["AUTOTESTER_ROOT"] = str(d); return d
def sec(html, n):
    m = re.search(rf'<section id="{n}".*?</section>', html, re.S); return m.group(0) if m else "<<NO SECTION>>"
def txt(h): return re.sub(r"<[^>]+>", " ", h)
res = {}
def check(name, ok, detail=""):
    res[name] = ok; print(("PASS " if ok else "FAIL ") + name, detail)

# H1 no baseline, with a failing case: must not claim regression
d = fresh(); s = mk_project(d); case(s, "c1", "f1"); 
record(s, "only", 1, {"f1": ["c1"]}, {"c1": Result.FAIL})
h = unified_html(s, None); r = sec(h, "regression")
check("H1 no-baseline makes no regression claim", "No trusted baseline" in r and "Regressed" not in r and "Fixed" not in r, "")
check("H1b failing flow shows failed", "failed" in r)

# H2 case not run / no verdict / unfinished release
d = fresh(); s = mk_project(d); case(s, "cA", "f1"); case(s, "cB", "f2"); case(s, "cC", "f3")
s.save_flowspec(FlowSpec(project="demo", flows=[Flow(id=f, name=f, entry_screen="home") for f in ("f1","f2","f3","f4")]))
record(s, "r1", 1, {"f1": ["cA"], "f2": ["cB"], "f3": ["cC"]}, {"cA": Result.PASS}, finished=False, unplanned=("f4",))
s.save_verdict("r1", Verdict(run_id="r1", case_id="cA", result=Result.PASS, failures=[]))
s.save_result("r1", RawResult(case_id="cB", outcome=Outcome.COMPLETED))   # executed, never graded
s.save_result("r1", RawResult(case_id="cC", outcome=Outcome.NOT_RUN, not_run_reason="browser crashed"))
h = unified_html(s, "r1"); w = sec(h, "workflows"); r = sec(h, "regression")
def case_block(w, cid):
    m = re.search(rf"<h3>[^<]*<code>{cid}</code>.*?(?=<h3>|$)", w, re.S); return m.group(0) if m else ""
cb, cc = case_block(w, "cB"), case_block(w, "cC")
check("H2 cB executed-but-ungraded = 'no verdict' not PASS", "no verdict" in cb and "PASS" not in cb, txt(cb)[:120])
check("H2 cC not-run shown with reason", "not run" in cc and "browser crashed" in cc and "PASS" not in cc, txt(cc)[:140])
check("H2 unfinished release warned", "not finished" in r)
f4 = re.search(r"<tr>(?:(?!</tr>).)*>f4<.*?</tr>", r, re.S)
check("H2 planless flow f4 'not run' not passed", bool(f4) and "not run" in f4.group(0) and "passed" not in f4.group(0))
# case in scope with NO result file at all (cB2) -> not run
# H2b: a scoped case with no result and no verdict
d = fresh(); s = mk_project(d); case(s, "cX", "f1"); record(s, "r1", 1, {"f1": ["cX"]}, {})
w = sec(unified_html(s, "r1"), "workflows"); cx = case_block(w, "cX")
check("H2b scoped case with nothing recorded = not run", "not run" in cx and "PASS" not in cx, txt(cx)[:100])

# H3 crawl states
from autotester.schema.crawl import CoverageHole
def crawl_case(status, cov, **kw):
    d = fresh(); s = mk_project(d); case(s, "c1", "f1"); record(s, "r1", 1, {"f1": ["c1"]}, {"c1": Result.PASS})
    s.save_crawl(Crawl(project="demo", id="cr1", status=status, screens=3, actions=5, coverage=cov, **kw))
    return s, unified_html(s, "r1")
full = CrawlCoverage(controls_discovered=4, controls_exercised=4, screens_reached=3, percent=100, holes=[])
s, h = crawl_case(CrawlStatus.COMPLETED, full); c = sec(h, "coverage")
print("   complete crawl rows:", re.sub(r"\s+", " ", txt(c))[:300])
check("H3a complete crawl, no gaps => not flagged incomplete", "Incomplete" not in c)
bnd = CrawlCoverage(controls_discovered=10, controls_exercised=10, screens_reached=3, percent=100, holes=[])
s, h = crawl_case(CrawlStatus.STOPPED_BOUND, bnd, stop_reason="max_actions"); c = sec(h, "coverage")
check("H3b bounded crawl with 100% coverage + no holes still incomplete", "Incomplete" in c, txt(c)[:200])
s, h = crawl_case(CrawlStatus.COMPLETED, None); c = sec(h, "coverage")
check("H3c completed crawl with NO coverage record not green", "Incomplete" in c, txt(c)[:200])
for st in [x for x in CrawlStatus if x is not CrawlStatus.COMPLETED]:
    try:
        s, h = crawl_case(st, full); c = sec(h, "coverage")
        check(f"H3d {st.value} crawl incomplete", "Incomplete" in c, "")
    except Exception as e: print("   skip", st, type(e).__name__, str(e)[:80])
# percent<100 w/ holes lists them
part = CrawlCoverage(controls_discovered=5, controls_exercised=2, screens_reached=2, percent=40, holes=[
  CoverageHole(node_id="n1", url_template="demo.test/a", selector="#x", name="Export", reason="not_visited"),
  CoverageHole(node_id="n1", url_template="demo.test/a", selector="#y", name="Sync", reason="bound:max_actions")])
s, h = crawl_case(CrawlStatus.STOPPED_BOUND, part, stop_reason="max_actions"); c = sec(h, "coverage")
check("H3e holes listed, Export+Sync in Not exercised, never 'passed'", "Export" in c and "Sync" in c and "passed" not in c.lower() and "PASS" not in c)
check("H3f 'not_visited' appears nowhere outside coverage", "not_visited" not in sec(h, "workflows") and "not_visited" not in sec(h, "regression") and "not_visited" not in sec(h, "api"))

# H4 missing inputs
d = fresh(); s = mk_project(d); s.save_run(Run(id="run_a", project="demo"))
h = unified_html(s, None)
for n in ("regression", "history", "coverage", "workflows"):
    check(f"H4 {n} Unavailable", "Unavailable:" in sec(h, n), re.sub(r'\s+',' ',txt(sec(h, n)))[:110])
a = sec(h, "api"); print("   api section for run with nothing:", re.sub(r'\s+',' ',txt(a))[:150])
# H4b: results exist but carry NO network evidence at all (capture never ran) -> what does api say?
d = fresh(); s = mk_project(d); case(s, "c1", "f1"); record(s, "r1", 1, {"f1": ["c1"]}, {"c1": Result.PASS})
s.save_result("r1", RawResult(case_id="c1", outcome=Outcome.COMPLETED))
a = sec(unified_html(s, "r1"), "api"); print("   api with results, zero NETWORK evidence:", re.sub(r'\s+',' ',txt(a))[:200])
check("H4b api says unavailable/uncaptured when no network evidence exists at all", "Unavailable" in a or "no network" in a.lower(), "")

# H5 counts == rows (persona)
d = fresh(); s = mk_project(d); case(s, "c1", "f1"); record(s, "r1", 1, {"f1": ["c1"]}, {"c1": Result.PASS})
rev = PersonaRevision(at="2026-10-03T00:00:00Z", summary="s", new_screens=["a","b"], changed_screens=["c"], missing_screens=["d","e","f"], broken_screens=["g"], missing_unjudged=["h","i"])
s.save_portal_persona(PortalPersona(project="demo", history=[rev]))
hs = sec(unified_html(s, "r1"), "history"); print("  ", re.sub(r'\s+',' ',txt(hs)))
nums = dict(re.findall(r"(new|changed|missing unjudged|missing|broken) (\d+)", txt(hs)))
lists = {k: len(re.search(rf"<b>{k}:</b>([^<]*)", hs).group(1).split(",")) if re.search(rf"<b>{k}:</b>", hs) else 0 for k in ("New","Changed","Missing","Broken")}
check("H5 persona counts equal rows shown", nums.get("new")=="2" and lists["New"]==2 and nums.get("missing")=="3" and lists["Missing"]==3 and nums.get("broken")=="1" and lists["Broken"]==1 and nums.get("changed")=="1", f"{nums} {lists}")
# H6 explicit unknown run / route errors
try: unified_html(s, "nope"); check("H6 unknown run id raises", False)
except ValueError as e: check("H6 unknown run id raises ValueError", True, str(e))
print("\nSUMMARY", sum(res.values()), "/", len(res), "FAILED:", [k for k,v in res.items() if not v])
