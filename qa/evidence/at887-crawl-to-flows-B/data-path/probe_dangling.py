"""Referential integrity when the spec already holds a video-learned screen at the same pattern+name."""
import sys, tempfile
from pathlib import Path
import autotester; print(autotester.__file__)
sys.argv = [sys.argv[0], sys.argv[1]]
from autotester.schema.flowspec import FlowSpec, Screen
from autotester.stages.explore_merge import merge_stored_crawl, screen_from
exec(open(Path(__file__).with_name("probe_datapath.py")).read().split("def sha")[0].split("PROJECT =")[0])
PROJECT = Project(slug="demo", name="Demo", base_url="https://app.test", allowed_domains=["app.test"])
src = open(Path(__file__).with_name("probe_datapath.py")).read()
exec("def node" + src.split("def node",1)[1].split("def sha")[0])
with tempfile.TemporaryDirectory(dir=sys.argv[1]) as td:
    s = build(Path(td), "crawl_v")
    home = [n for n in s.list_nodes("crawl_v") if n.name == "Home"][0]
    vs = screen_from(home).model_copy(update={"id": "scr_from_video_home"})
    spec = FlowSpec(project="demo", screens=[vs])
    out = merge_stored_crawl(s, spec, "demo", "crawl_v")
    ids = {x.id for x in out.screens}
    print("screens", sorted(ids))
    for f in out.flows:
        refs = [f.entry_screen, f.exit_screen] + [st.screen_id for st in f.steps]
        print("REFINT", f.name, "dangling:", [r for r in refs if r not in ids])
