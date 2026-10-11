"""Differential probe (checker scratch): drive `autotester expand` through the review door and dump results."""
import json, os
from tests.test_expand_cli import _seed, _seeded_mock, runner, root  # noqa
from autotester.cli import app

def test_probe(root, monkeypatch):
    store = _seed(root, reviewed=False)
    prov = _seeded_mock(monkeypatch)
    out = {}
    def run(key, args):
        r = runner.invoke(app, args)
        out[key] = [r.exit_code, r.output.replace(str(root), "<root>")]
    run("pending_generate", ["expand", "demo"])
    run("list", ["expand", "demo", "--proposals"])
    rows = store.list_case_proposals()
    ids = [p.id for p in rows]
    out["n_rows"] = len(rows)
    run("both", ["expand", "demo", "--approve", ids[1], "--prune", ids[1], "--by", "h"])
    run("unsigned_prune", ["expand", "demo", "--prune", ids[1]])
    run("bogus", ["expand", "demo", "--approve", "nope", "--by", "h"])
    run("prune_two", ["expand", "demo", "--prune", ids[1], "--prune", ids[2], "--by", "h"])
    run("approve_rest", ["expand", "demo"] + [x for i in ids if i not in (ids[1], ids[2]) for x in ("--approve", i)] + ["--by", "h"])
    out["status"] = {p.title: p.status for p in store.list_case_proposals()}
    before = len(prov.calls) if hasattr(prov, "calls") else None
    run("generate", ["expand", "demo"])
    out["calls_attr"] = [before, len(prov.calls) if hasattr(prov, "calls") else None]
    out["n_cases"] = len(store.list_cases())
    out["case_titles"] = sorted(c.title for c in store.list_cases())
    json.dump(out, open(os.environ["PROBE_OUT"], "w"), indent=1, sort_keys=True)
