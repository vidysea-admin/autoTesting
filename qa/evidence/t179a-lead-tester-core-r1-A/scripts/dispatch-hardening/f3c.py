"""F3c: u_escape on disk, plus _children expand-before-check cost."""
import sys, tempfile, time, tracemalloc, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa
spy = Spy()
root = Path(tempfile.mkdtemp()) / "d"
ctx = make_ctx(root, spy)
case = add_case(ctx, rubric=True, result=True)
BS = chr(92)
esc = "".join(f"{BS}u{ord(c):04x}" for c in CANARY)
restore = patch_stages(spy, lambda c: RawResult(case_id=c.id, outcome=Outcome.ERRORED, error=f"x {esc} y"))
out = tools.dispatch(ctx, "run_case", {"case_id": case.id})
restore()
print("u_escape: ok=", out.ok, "refusal=", out.refusal)
f = next(root.rglob(f"{case.id}.json"))
data = json.loads(f.read_text("utf-8"))
decoded = re.sub(BS + BS + "u([0-9a-f]{4})", lambda m: chr(int(m.group(1), 16)), data["error"])
print("stored error field:", data["error"][:60], "... decodes to canary:", CANARY in decoded)
print("released summary decodes to canary:", CANARY in re.sub(BS + BS + "u([0-9a-f]{4})", lambda m: chr(int(m.group(1), 16)), out.summary))
# expand-before-check cost for a big (caller-built) dict
d = {str(i): 1 for i in range(3_000_000)}
tracemalloc.start()
t0 = time.perf_counter()
res = tools.dispatch(ctx, "get_catalog", d)
dt = time.perf_counter() - t0
cur, peak = tracemalloc.get_traced_memory()
print(f"3M-key dict: refusal={res.refusal.value} secs={dt:.2f} peak_extra_MB={peak/1e6:.0f}")
tracemalloc.stop()
