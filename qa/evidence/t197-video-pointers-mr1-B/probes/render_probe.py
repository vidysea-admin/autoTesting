import hashlib, json, sys
from pathlib import Path
import autotester
print("AT_FILE", autotester.__file__)
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
res = {}
def put(name, text):
    (out / name).write_text(text, encoding="utf-8", newline="")
    res[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
try:
    from autotester.schema.video_review import VideoReview
    from autotester.stages import video_review_render as vr
    html = getattr(vr, "render_review_html", None) or getattr(vr, "render_html")
    print("html fn:", html.__name__, "has render_html:", hasattr(vr, "render_html"), "has render_review_html:", hasattr(vr, "render_review_html"))
    for kind, path in zip(("ok", "partial", "failed"), sys.argv[2:5]):
        rv = VideoReview.model_validate_json(Path(path).read_text("utf-8"))
        put(f"review-{kind}.html", html(rv)); put(f"review-{kind}.md", vr.render_markdown(rv))
except ImportError as e:
    print("no video_review_render:", e)
try:
    from autotester.schema.unified_report import *
    from autotester.stages.unified_report_render import render_html
except ImportError as e:
    print("no unified report module:", e); json.dump(res, open(out / "hashes.json", "w"), indent=1, sort_keys=True); sys.exit(0)
def mk(full):
    if not full:
        u = lambda: dict(unavailable="no data")
        return UnifiedReport(project="demo", run_id="r1", regression=RegressionSection(**u()),
            api=ApiSection(**u()), workflows=WorkflowSection(**u()), history=HistorySection(**u()), coverage=CoverageSection(**u()))
    return UnifiedReport(project="demo", run_id="r2",
        regression=RegressionSection(release_run_id="rel1", git_sha="abc1234", finished=True, flagged_bad=True, flagged_reason="2 flows <regressed> & more"),
        api=ApiSection(failures=[ApiFailure(source="run:c1", method="GET", url="https://x.test/a?b=1&c=2", status=500, raw="boom <b>")], sources_read=["run:c1"]),
        workflows=WorkflowSection(run_id="r2", cases=[CaseLine(case_id="c1", title="Login <ok>", flow_id="f1", result="failed", outcome="bug", scoreboard="1/2",
            reason="nope", failures=[FailureLine(criterion_id="C1", reason="wrong & bad", fix_hint="fix it")], repro_steps=["open", "click"]),
            CaseLine(case_id="c2", title="Other", result="passed")]),
        history=HistorySection(), coverage=CoverageSection(crawl_id="cr1", rows=[("home", "reached"), ("x<y", "z")], unreached=[("admin", "locked")], incomplete=True))
for full in (False, True):
    try:
        put(f"unified-{'full' if full else 'empty'}.html", render_html(mk(full)))
    except Exception as e:
        put(f"unified-{'full' if full else 'empty'}.html", "ERR " + type(e).__name__ + str(e)[:300])
json.dump(res, open(out / "hashes.json", "w"), indent=1, sort_keys=True)
print(json.dumps(res, indent=1))
