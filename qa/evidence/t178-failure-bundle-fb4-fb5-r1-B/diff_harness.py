"""Differential harness for the expand review path. Run with PYTHONPATH at a src copy.
Prints JSON {scenario: {exit, out, calls, files}} with timestamps normalised."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from typer.testing import CliRunner

import autotester
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.stages import expand as expand_stage

BASE = Path(sys.argv[1])
runner = CliRunner()
TS = re.compile(r"\d{4}-\d\d-\d\dT[\d:.]+(Z|\+00:00)?")


def flow(fid: str, name: str) -> Flow:
    return Flow(id=fid, name=name, entry_screen="scr", steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://demo.test/x"),
        Step(order=2, action=Action.FILL, target="Email", value="a@demo.test"),
        Step(order=3, action=Action.CLICK, target="Go")])


def seed(root: Path, slug="demo", flows=("flow-a", "flow-b")) -> ProjectStore:
    store = ProjectStore(slug, root)
    store.save_project(Project(slug=slug, name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.save_flowspec(FlowSpec(project=slug, review=Review(status=ReviewStatus.APPROVED),
                                 flows=[flow(f, f.upper()) for f in flows]))
    return store


def mock(monkeypatch_target=None):
    prov = MockProvider(responses={"agent": [ExpandedSteps(
        steps=[Step(order=1, action=Action.CLICK, target="Go")], rationale="r")] * 200})
    import autotester.cli as cli
    cli.providers.get = lambda _id, **_kw: prov
    return prov


def snap(root: Path) -> dict:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            txt = p.read_text(encoding="utf-8", errors="replace")
            txt = TS.sub("<TS>", txt)
            out[str(p.relative_to(root)).replace("\\", "/")] = txt
    return out


def cli(args):
    from autotester.cli import app
    r = runner.invoke(app, args, catch_exceptions=True)
    exc = repr(r.exception) if r.exception and not isinstance(r.exception, SystemExit) else None
    return {"exit": r.exit_code, "out": TS.sub("<TS>", r.output), "exc": exc}


results = {}


def scenario(name, fn):
    root = Path(tempfile.mkdtemp(prefix="t178r1b-", dir=BASE))
    os.environ["AUTOTESTER_ROOT"] = str(root)
    prov = mock()
    store = seed(root)
    try:
        res = fn(store, root, prov)
    except BaseException as e:  # noqa
        res = {"scenario_exc": repr(e)}
    res["calls"] = len(prov.prompts)
    res["files"] = snap(root)
    results[name] = res
    shutil.rmtree(root, ignore_errors=True)


def ids(store):
    spec = store.load_flowspec()
    rows = expand_stage.propose_cases(spec)
    return [p.id for p in rows], rows


def s_nostage(st, root, prov):
    return {"r": cli(["expand", "demo"])}


def s_proposals(st, root, prov):
    return {"r": cli(["expand", "demo", "--proposals"]), "r2": cli(["expand", "demo", "--proposals"])}


def s_approve_all(st, root, prov):
    i, _ = ids(st)
    a = []
    for x in i:
        a += ["--approve", x]
    return {"r": cli(["expand", "demo", *a, "--by", "alice"]), "g": cli(["expand", "demo"])}


def s_approve_some_prune_rest(st, root, prov):
    i, rows = ids(st)
    a = []
    for x in i[:3]:
        a += ["--approve", x]
    for x in i[3:]:
        a += ["--prune", x]
    return {"r": cli(["expand", "demo", *a, "--by", "alice"]), "g": cli(["expand", "demo"])}


def s_no_by(st, root, prov):
    i, _ = ids(st)
    return {"r": cli(["expand", "demo", "--approve", i[1]]),
            "r2": cli(["expand", "demo", "--approve", i[1], "--by", "   "]),
            "g": cli(["expand", "demo"])}


def s_both(st, root, prov):
    i, _ = ids(st)
    return {"r": cli(["expand", "demo", "--approve", i[1], "--prune", i[1], "--by", "a"])}


def s_unknown(st, root, prov):
    return {"r": cli(["expand", "demo", "--approve", "nope", "--by", "a"]),
            "g": cli(["expand", "demo"])}


def s_prune_only(st, root, prov):
    i, _ = ids(st)
    return {"r": cli(["expand", "demo", "--prune", i[1], "--by", "a"]), "g": cli(["expand", "demo"])}


def s_prune_after_approve(st, root, prov):
    i, _ = ids(st)
    a = []
    for x in i:
        a += ["--approve", x]
    r1 = cli(["expand", "demo", *a, "--by", "alice"])
    p = []
    for x in i:
        p += ["--prune", x]
    r2 = cli(["expand", "demo", *p, "--by", "bob"])
    return {"r1": r1, "r2": r2, "g": cli(["expand", "demo"])}


def s_approve_then_prune_one(st, root, prov):
    i, _ = ids(st)
    a = []
    for x in i:
        a += ["--approve", x]
    cli(["expand", "demo", *a, "--by", "alice"])
    r2 = cli(["expand", "demo", "--prune", i[2], "--by", "bob"])
    return {"r2": r2, "g": cli(["expand", "demo"])}


def s_stale_spec(st, root, prov):
    i, _ = ids(st)
    a = []
    for x in i:
        a += ["--approve", x]
    cli(["expand", "demo", *a, "--by", "alice"])
    spec = st.load_flowspec()
    spec.flows.append(flow("flow-c", "C"))
    st.save_flowspec(spec)
    return {"g": cli(["expand", "demo"]), "rv": cli(["expand", "demo", "--approve", i[0], "--by", "z"])}


def s_malformed(st, root, prov):
    i, _ = ids(st)
    a = []
    for x in i:
        a += ["--approve", x]
    cli(["expand", "demo", *a, "--by", "alice"])
    f = st.paths.case_proposals
    f.write_text(f.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
    return {"g": cli(["expand", "demo"]), "p": cli(["expand", "demo", "--proposals"])}


def s_forged_approved(st, root, prov):
    """Hand-edit the file: status approved with no reviewer."""
    i, _ = ids(st)
    cli(["expand", "demo", "--proposals"])
    f = st.paths.case_proposals
    lines = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    for row in lines:
        row["status"] = "approved"
    f.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    return {"g": cli(["expand", "demo"])}


def s_other_batch(st, root, prov):
    """Approvals from a different project's spec copied in."""
    other = seed(root, slug="other", flows=("flow-x",))
    oi, orows = ids(other)
    for x in oi:
        other.review_case_proposal  # noqa
    other.stage_case_proposals(orows)
    for x in oi:
        other.review_case_proposal(x, by="mallory", approved=True)
    cli(["expand", "demo", "--proposals"])
    f = st.paths.case_proposals
    f.write_text(other.paths.case_proposals.read_text(encoding="utf-8"), encoding="utf-8")
    return {"g": cli(["expand", "demo"])}


def s_no_flowspec(st, root, prov):
    st.paths.flowspec.unlink() if hasattr(st.paths, "flowspec") else None
    return {"g": cli(["expand", "demo"]), "p": cli(["expand", "demo", "--proposals"])}


def s_unreviewed_spec(st, root, prov):
    spec = st.load_flowspec()
    spec.review = Review(status=ReviewStatus.DRAFT)
    st.save_flowspec(spec)
    return {"g": cli(["expand", "demo"]), "p": cli(["expand", "demo", "--proposals"])}


def s_inproc(st, root, prov):
    out = {}
    spec = st.load_flowspec()
    i, rows = ids(st)
    out["sr_none"] = [r.status for r in expand_stage.stage_and_review(st, spec, [], [], "")]
    for label, args in [("empty_by", (st, spec, [i[1]], [], "")), ("ws_by", (st, spec, [i[1]], [], "  ")),
                        ("both", (st, spec, [i[2]], [i[2]], "a")), ("unknown", (st, spec, ["zz"], [], "a"))]:
        try:
            out[label] = [r.status for r in expand_stage.stage_and_review(*args)]
        except BaseException as e:  # noqa
            out[label] = "RAISE " + type(e).__name__ + ": " + str(e)[:100]
    # direct expand with no approvals
    st2 = seed(root, slug="direct")
    for label, kw in [("expand_nostore", {}), ("expand_store_noapproval", {"store": st2})]:
        try:
            out[label] = len(expand_stage.expand(st2.load_flowspec(), prov, **kw))
        except BaseException as e:  # noqa
            out[label] = "RAISE " + type(e).__name__ + ": " + str(e)[:100]
    return out


def _split(st):
    i, rows = ids(st)
    happy=[r.id for r in rows if r.case_class.value=="happy"]
    rest=[r.id for r in rows if r.case_class.value!="happy"]
    return happy, rest


def s_partial_prune(st, root, prov):
    h, rest = _split(st)
    a=[]; 
    for x in h+rest[:2]: a+=["--approve",x]
    for x in rest[2:]: a+=["--prune",x]
    return {"r": cli(["expand","demo",*a,"--by","alice"]), "g": cli(["expand","demo"])}


def s_partial_noprune(st, root, prov):
    h, rest = _split(st)
    a=[]
    for x in h+rest[:2]: a+=["--approve",x]
    return {"r": cli(["expand","demo",*a,"--by","alice"]), "g": cli(["expand","demo"]), "g2": cli(["expand","demo"])}


def s_prune_all_nonhappy(st, root, prov):
    h, rest = _split(st)
    a=[]
    for x in h: a+=["--approve",x]
    for x in rest: a+=["--prune",x]
    return {"r": cli(["expand","demo",*a,"--by","alice"]), "g": cli(["expand","demo"])}


def s_happy_pruned_only(st, root, prov):
    h, rest = _split(st)
    a=[]
    for x in rest: a+=["--approve",x]
    for x in h: a+=["--prune",x]
    return {"r": cli(["expand","demo",*a,"--by","alice"]), "g": cli(["expand","demo"])}


def s_provider_flag_unavailable(st, root, prov):
    h, rest = _split(st)
    a=[]
    for x in h: a+=["--approve",x]
    cli(["expand","demo",*a,"--by","alice"])
    import autotester.cli as c
    c.providers.get = lambda _id, **_kw: type("P",(),{"available":lambda self: False})()
    return {"g": cli(["expand","demo"])}


for n, f in list(globals().items()):
    if n.startswith("s_"):
        scenario(n[2:], f)

print(json.dumps(results, indent=1, sort_keys=True))
