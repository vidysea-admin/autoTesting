"""F2 follow-up: how many characters of a (non-raw) canary form survive the 300-char cut of _error_text?"""
import sys, csv, importlib.util
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa
OUT = ROOT / "evidence" / "dispatch-hardening"
spy = Spy()
import tempfile
ctx = make_ctx(Path(tempfile.mkdtemp()) / "d", spy)
v = variants()
forms = {"reversed": v["reversed"], "b64_std_off0": v["b64_std_off0"], "b64_url_off0": v["b64_url_off0"],
         "hex_lower": v["hex_lower"], "pct_all": v["pct_all"], "b32": v["b32"]}
rows = []
for name, val in forms.items():
    for cut in range(1, len(val) + 1):
        pad = 300 - len("RuntimeError: ") - cut
        msg = "x" * pad + val
        txt = tools._error_text(ctx, RuntimeError(msg))
        # what survives of val in the returned text, and would _release refuse it?
        out = tools._release(ctx, tools._refusal("run_case", RefusalClass.STAGE_ERROR, txt))
        survived = txt.endswith(val[:cut])
        rows.append(dict(form=name, form_len=len(val), cut=cut, survived_chars=cut if survived else 0,
                         released=out.refusal is RefusalClass.STAGE_ERROR))
by = {}
for r in rows:
    if r["released"] and r["survived_chars"]:
        by[r["form"]] = max(by.get(r["form"], 0), r["survived_chars"])
with open(OUT / "f2_truncation_leak.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("max prefix chars released (STAGE_ERROR, not SECRET) per form:", by)
print({k: len(forms[k]) for k in forms})
# the same full message without any cut (does the gate refuse it when whole?)
for name, val in forms.items():
    out = tools.dispatch(ctx, "run_case", {"case_id": "nope"})
print("control: full form inside 300 chars -> refused SECRET?")
for name, val in forms.items():
    txt = tools._error_text(ctx, RuntimeError("y " + val))
    out = tools._release(ctx, tools._refusal("run_case", RefusalClass.STAGE_ERROR, txt))
    print(" ", name, out.refusal.value)
