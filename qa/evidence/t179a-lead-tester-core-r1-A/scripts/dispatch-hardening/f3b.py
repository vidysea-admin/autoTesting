"""F3b: separator-split canary in a stage result / verdict / exception message vs the gates."""
from __future__ import annotations
import csv, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa
from seps import SEPS
from autotester.core.redact import assert_no_raw_secrets
from autotester.schema.verdict import Verdict

OUT = ROOT / "evidence" / "dispatch-hardening"


def refuses(text: str) -> bool:
    try:
        assert_no_raw_secrets(text, [CANARY])
        return False
    except ValueError:
        return True


def stored_text(root: Path) -> str:
    return "\n".join(p.read_bytes().decode("utf-8", "ignore") for p in root.rglob("*") if p.is_file())


def fresh():
    tmp = Path(tempfile.mkdtemp(prefix="dh-f3b-"))
    spy = Spy()
    root = tmp / "data"
    ctx = make_ctx(root, spy)
    case = add_case(ctx, rubric=True, result=True)
    return ctx, spy, case, root


rows = []
for sname, sep in SEPS.items():
    for shape in ("mid", "every"):
        text = (CANARY[:8] + sep + CANARY[8:]) if shape == "mid" else sep.join(CANARY)
        msg = f"saw {text} here"
        row = dict(sep=sname, shape=shape, real_str_gate_refuses=refuses(msg),
                   json_dump_gate_refuses=refuses(json.dumps(msg, ensure_ascii=False)),
                   pydantic_json_gate_refuses=refuses(ToolOutcome(tool="x", ok=False, summary=msg).model_dump_json()))
        # result path
        for kind in ("result", "verdict", "exception"):
            ctx, spy, case, root = fresh()
            restore = None
            if kind == "result":
                restore = patch_stages(spy, lambda c: RawResult(case_id=c.id, outcome=Outcome.ERRORED, error=msg))
                out = tools.dispatch(ctx, "run_case", {"case_id": case.id})
            elif kind == "verdict":
                restore = patch_stages(spy)
                tools.grade.grade = lambda rub, res, run_id, *a, **k: Verdict(
                    run_id=run_id, case_id=res.case_id, result=Result.FAIL, rubric_hash="h", note=msg, scoreboard=msg)
                out = tools.dispatch(ctx, "grade_case", {"case_id": case.id})
            else:
                restore = patch_stages(spy)
                def boom(*a, **k):
                    raise RuntimeError(msg)
                tools.execute.run_case = boom
                out = tools.dispatch(ctx, "run_case", {"case_id": case.id})
            restore()
            on_disk = stored_text(root)
            # recoverable = the canary re-appears once all separator/whitespace chars are removed
            def recov(t):
                import re
                t = t.replace("\\n", "").replace("\\t", "").replace("\\r", "")
                t = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)
                for ch in set(sep) | {" "}:
                    t = t.replace(ch, "")
                return CANARY in t
            row[f"{kind}_ok"] = out.ok
            row[f"{kind}_refusal"] = getattr(out.refusal, "value", "") or ""
            row[f"{kind}_released_recoverable"] = recov(out.model_dump_json()) and out.refusal is not RefusalClass.SECRET
            row[f"{kind}_disk_recoverable"] = recov(on_disk) if kind != "exception" else ""
        rows.append(row)

with open(OUT / "f3b_separators.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

print("sep/shape rows:", len(rows))
for r in rows:
    flags = []
    if r["real_str_gate_refuses"] and not r["pydantic_json_gate_refuses"]:
        flags.append("REAL-REFUSES/JSON-PASSES")
    if r["result_disk_recoverable"] or r["verdict_disk_recoverable"]:
        flags.append("DISK-RECOVERABLE")
    if r["result_released_recoverable"] or r["verdict_released_recoverable"] or r["exception_released_recoverable"]:
        flags.append("RELEASED-RECOVERABLE")
    if flags:
        print(r["sep"], r["shape"], flags, "real", r["real_str_gate_refuses"], "json", r["pydantic_json_gate_refuses"],
              "res", r["result_ok"], r["result_refusal"], "ver", r["verdict_ok"], r["verdict_refusal"], "exc", r["exception_refusal"])
print("clean rows:", sum(1 for r in rows if not (r["result_disk_recoverable"] or r["verdict_disk_recoverable"])))
