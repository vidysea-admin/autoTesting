import json, tempfile, pathlib, sys, datetime as dt
sys.path.insert(0, r"C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\e46c0e51-15e9-4a31-a0b0-cf49de9d445f\scratchpad\b")
from autotester.core.redact import Redactor
from autotester.core import trace as new
import old_trace as old
from autotester.schema.run_state import StageCheckpoint, StageName
import autotester.schema.base as b
fixed = dt.datetime(2026,10,19,1,2,3,456789,tzinfo=dt.UTC)
import autotester.schema.trace as st
for m in (st,):
    pass
def go(mod, secrets, **kw):
    d = pathlib.Path(tempfile.mkdtemp(dir=r"D:\autoTesting\.work\tmp"))
    w = mod.TraceWriter(d/"t.jsonl","run-é",redactor=Redactor(secrets))
    w.record_llm(provider="p:m", role="judge", prompt_file="a.md", input_tokens=3, output_tokens=None, latency_s=kw.get("lat",float("nan")), retries=1, fallback_hops=0, fed_id="é\u2028\"x")
    w.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="failed", error="ünï <>&", started=fixed, finished=fixed))
    w.record_tool(seq=1, op="plan", name="lead")
    return [json.loads(l) for l in (d/"t.jsonl").read_text(encoding="utf-8").split(chr(10)) if l], (d/"t.jsonl").read_text(encoding="utf-8")
strip=lambda rows:[{k:v for k,v in r.items() if k!="recorded_at"} for r in rows]
no, rawo = go(old, {}); nn, rawn = go(new, {})
print("equal no-secret:", strip(no)==strip(nn), "nan->", nn[0]["latency_s"], old and no[0]["latency_s"])
# raw formatting identical except recorded_at?
import re
f=lambda s: re.sub(r'"recorded_at":"[^"]*"','',s)
print("bytes equal:", f(rawo)==f(rawn))
# enum-valued secret
for sec in ("done","failed","execute"):
    rows, raw = go(new, {"K": sec})
    print(sec, "on disk status/stage:", [(r.get("stage"), r.get("status")) for r in rows if r.get("kind")=="stage"] )
