import sys, pathlib
root = pathlib.Path(sys.argv[1]); name = sys.argv[2]
def sub(rel, old, new):
    p = root / rel; t = p.read_text(encoding="utf-8")
    assert t.count(old) == 1, (rel, old, t.count(old))
    p.write_text(t.replace(old, new), encoding="utf-8", newline="")
O = "src/autotester/stages/orchestrate.py"
PF = "    release_preflight(project, ctx)\n"
M = {
 "rr1": lambda: sub("src/autotester/stages/orchestrate_gate.py", 'if c.status in ("failed", "running")', 'if c.status in ("failed", "running", "done")'),
 "rr2a": lambda: sub(O, PF, ""),
 "rr2b": lambda: (sub(O, PF, ""), sub(O, "    graph = _compile(ctx, saver)\n", "    graph = _compile(ctx, saver)\n" + PF)),
 "rr2c": lambda: (sub(O, PF, ""), sub(O, "    check_lineage(project, ctx, state)\n", "    check_lineage(project, ctx, state)\n" + PF)),
 "rr2d": lambda: (sub(O, PF, ""), sub(O, "    graph.invoke(payload, config=config, durability=\"sync\")\n", PF + "    graph.invoke(payload, config=config, durability=\"sync\")\n")),
 "rr3": lambda: sub("src/autotester/schema/release.py", "self.finished and not self.flagged_bad and not self.issues", "self.finished and not self.issues"),
 "rr4": lambda: sub("src/autotester/stages/release.py", "from datetime import datetime\n", "from datetime import datetime\nfrom autotester.schema.enums import Result\n_DECIDED = Result.PASS\n"),
 "rr4b": lambda: sub("src/autotester/stages/release_compare.py", "detail=verdict.note or verdict.scoreboard or str(verdict.result.value)", 'detail="failed"'),
 "rr5": lambda: sub("pyproject.toml", '    "langgraph==1.2.14",  # T-167/D-041: release-regression graph (checkpointer + interrupt)\n', ""),
 "rr6": lambda: sub("src/autotester/stages/release_compare.py", "for flow_id in scope.expected_flow_ids:", "for flow_id in scope.expected_flow_ids[:1]:"),
}
M[name](); print("mutated", name)
