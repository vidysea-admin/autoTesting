"""Inputs 1, 2, 5: proposals from flow name/step text; CLI expand --by/--approve/--prune."""
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import S, mk_root, raw_in, seed  # noqa: E402

import autotester  # noqa: E402

print("autotester.__file__ =", autotester.__file__)
from typer.testing import CliRunner  # noqa: E402

from autotester.cli import app  # noqa: E402
from autotester.core.redact import Redactor  # noqa: E402
from autotester.stages.expand import propose_cases  # noqa: E402

root = mk_root("p1")
store = seed(root, f"Login {S} flow")
red = Redactor({"ZZ_PROBE_PW": S})
print("[setup] flowspec.json on disk:", raw_in(store.paths.flowspec), "(origin of the text; not this diff)")

rows = propose_cases(store.load_flowspec())
print("[1] propose_cases rows:", len(rows), "title has secret:", any(S in r.title for r in rows),
      "rationale has secret:", any(S in r.rationale for r in rows))
print("    sample title:", rows[0].title, "| rationale:", rows[0].rationale[:50])
store.stage_case_proposals(rows)
p = store.paths.case_proposals
print("[1] case_proposals.jsonl:", raw_in(p))
loaded = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
print("[1] json.loads titles carrying secret:", sum(S in r["title"] for r in loaded), "of", len(loaded))
print("[1] any other field (step text/value/target/note/precondition) in proposals file:",
      any(x in p.read_text(encoding="utf-8") for x in ("Password", "typed", "knows")))
print("[1] Redactor.scrub applied by stage/store? scrubbed-title would equal:", red.scrub(rows[0].title))

# --- CLI ---
r = CliRunner()
out = r.invoke(app, ["expand", "demo", "--proposals"])
print("[2] --proposals exit", out.exit_code, "stdout has secret:", S in out.output)
happy = next(x for x in store.list_case_proposals() if x.case_class.value == "happy")
out = r.invoke(app, ["expand", "demo", "--approve", happy.id, "--by", S])
print("[2] --approve --by <secret> exit", out.exit_code, "| stdout has secret:", S in out.output)
rows_now = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
rb = [x.get("reviewed_by") for x in rows_now if x.get("reviewed_by")]
print("[2] reviewed_by on disk:", rb, "-> STORED RAW" if S in rb else "-> not raw")
print("[2] case_proposals.jsonl raw check:", raw_in(p))

for label, args in [
    ("approve unknown id=<secret>", ["expand", "demo", "--approve", S, "--by", "x"]),
    ("prune unknown id=<secret>", ["expand", "demo", "--prune", S, "--by", "x"]),
    ("approve+prune same id=<secret>", ["expand", "demo", "--approve", S, "--prune", S, "--by", "x"]),
    ("approve valid id, blank --by", ["expand", "demo", "--approve", happy.id, "--by", ""]),
    ("unknown project name=<secret>", ["expand", S, "--proposals"]),
]:
    o = r.invoke(app, args)
    print(f"[2] {label}: exit {o.exit_code} echo-secret={S in o.output} out={o.output.strip()[:110]!r}")

# --- 5: Case.priority invalid in cases.jsonl ---
store.paths.cases.write_text(json.dumps({
    "project": "demo", "flow_id": "f", "kind": "best", "case_class": "happy",
    "title": "t", "steps": [], "priority": S}) + "\n", encoding="utf-8")
try:
    store.list_cases()
    print("[5] invalid priority row: ACCEPTED (!)")
except Exception as exc:  # noqa: BLE001
    m = str(exc)
    print("[5] invalid Case.priority row ->", type(exc).__name__, "| message echoes raw secret:", S in m)
    print("    msg head:", m[:260].replace("\n", " | "))
# same through the CLI (which surface prints it?)
o = r.invoke(app, ["expand", "demo", "--proposals"])
print("[5] CLI after bad cases row: exit", o.exit_code, "echo-secret:", S in o.output,
      "exc:", type(o.exception).__name__ if o.exception else None)
# invalid priority on case_proposals-free path: list_cases(priorities=[S])
try:
    store.paths.cases.write_text("", encoding="utf-8")
    store.list_cases(priorities=[S])
except Exception as exc:  # noqa: BLE001
    print("[5b] list_cases(priorities=[secret]) ->", type(exc).__name__, str(exc), "| echo:", S in str(exc))
