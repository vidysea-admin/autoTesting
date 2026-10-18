import json, tempfile, pathlib, sys, base64
sys.path.insert(0, r"C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\e46c0e51-15e9-4a31-a0b0-cf49de9d445f\scratchpad\b")
from autotester.core.redact import Redactor
from autotester.core import trace as new
import old_trace as old
from autotester.schema.run_state import StageCheckpoint, StageName
SECRETS = {
 "A": 'pa"ss\w0rd-Zq91',
 "B": "587",
 "C": "pä55wörd-ünï€ode",
 "D": "line1\nline2-Sekret",
 "E": "tab\there-Sekret77",
 "F": "sk-live/abc+def==XYZ123",
 "G": "<b>&amp;Secret&</b>1x",
 "H": "emoji😀Secret9",
}
def variants(s):
    return [s, "x"+s+"y", s.upper(), json.dumps(s), json.dumps(s)[1:-1], base64.b64encode(s.encode()).decode(), s[::-1],
            __import__("urllib.parse").parse.quote(s), __import__("urllib.parse").parse.quote(__import__("urllib.parse").parse.quote(s)),
            __import__("html").escape(s), s.encode().hex()]
def run(mod, secret, key, val, fld):
    d = pathlib.Path(tempfile.mkdtemp(dir=r"D:\autoTesting\.work\tmp"))
    w = mod.TraceWriter(d/"trace.jsonl", val if fld=="trace_id" else "run-1", redactor=Redactor({key:secret}))
    try:
        if fld=="error": w.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="failed", error=val))
        elif fld=="trace_id": w.record_stage(StageCheckpoint(stage=StageName.EXECUTE, status="failed"))
        elif fld=="tool_name": w.record_tool(seq=1, op="tool", name=val)
        elif fld=="refusal": w.record_tool(seq=1, op="tool", name="n", refusal=val)
        else: w.record_llm(provider=val if fld=="provider" else "p", role=val if fld=="role" else "r", prompt_file=val if fld=="prompt_file" else None, input_tokens=1, output_tokens=1, latency_s=0.5, retries=0, fallback_hops=0, fed_id=val if fld=="fed_id" else None)
    except ValueError as e:
        return "RAISED", None
    return "OK", (d/"trace.jsonl").read_text(encoding="utf-8")
leaks = []; diffs = []
for key, sec in SECRETS.items():
    r = Redactor({key: sec})
    for v in variants(sec):
        for fld in ["error","fed_id","trace_id","tool_name","refusal","provider","role","prompt_file"]:
            n_st, n_txt = run(new, sec, key, v, fld)
            o_st, o_txt = run(old, sec, key, v, fld) if fld not in ("tool_name","refusal") or hasattr(old.TraceWriter,"record_tool") else ("-",None)
            if n_txt is not None:
                # decode every string value and test raw + folded
                for line in n_txt.splitlines():
                    obj = json.loads(line)
                    for k, x in obj.items():
                        if isinstance(x, str) and (sec in x or r.contains_folded(x) or not r.is_clean(x)):
                            leaks.append((key, fld, v, k, x))
                    if sec in line: leaks.append((key,fld,v,"RAW-LINE",line))
            if (o_st, bool(o_txt and sec in o_txt)) != (n_st, bool(n_txt and sec in n_txt)):
                diffs.append((key, fld, v, o_st, n_st))
print("LEAKS", len(leaks))
for l in leaks[:20]: print(l)
print("DIFFS vs old", len(diffs))
for d in diffs:
    if d[0] not in "A" and not (d[0]=="D" and d[1]!="error"): print(d)
