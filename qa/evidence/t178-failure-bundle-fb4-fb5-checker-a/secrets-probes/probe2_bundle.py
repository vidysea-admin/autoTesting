"""Input 3: failure bundle. Case/result/verdict with the secret everywhere (FB3 path) + tampered manifest names."""
import json, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import S, S_NOBS, mk_root, raw_in
import autotester
print("autotester.__file__ =", autotester.__file__)
sys.path.insert(0, r"C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/t178a/base/scripts")
import check_no_secrets as cns
def echo(m):
    return any(x in m or repr(x)[1:-1] in m for x in (S, S_NOBS))
from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.run import Evidence, RawResult
from autotester.schema.run_state import StageName
from autotester.schema.trace import StageSpan
from autotester.schema.verdict import Failure, Verdict
from autotester.schema.failure_bundle import BundleFile, BundleFileKind
from autotester.stages.failure_bundle import build_failure_bundle, load_bundle, sources_from_result

root = mk_root("p2")
RUN = "run_A"
tmp = root / "work"; tmp.mkdir()
steps = [Step(order=i, action=Action.CLICK, target=f"btn {S} {i}", note=f"typed {S}", value=S) for i in range(1, 4)]
case = Case(project="demo", flow_id="login", kind=CaseKind.WORST, case_class=CaseClass.AUTH_WRONG_CREDS,
            title=f"Login {S} flow — auth", rationale=f"why {S}", steps=steps)
ev = []
for o in (1, 2, 3):
    (tmp / f"s{o}.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    ev.append(Evidence(kind=EvidenceKind.SCREENSHOT, path=f"s{o}.png", step_order=o, masked=True, label=f"lbl {S}"))
result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=f"err {S}", evidence=ev)
verdict = Verdict(run_id=RUN, case_id=case.id, result=Result.FAIL, failures=[Failure(criterion_id="c1", reason=f"r {S}")])
import os
SPAN_SECRET = os.environ.get("SPAN_SECRET", "1") == "1"
span = StageSpan(trace_id=RUN, stage=StageName.EXECUTE, status="failed", error=(f"sp {S}" if SPAN_SECRET else "sp clean"))
print("[3a] span carries secret:", SPAN_SECRET)
red = Redactor({"ZZ_PROBE_PW": S})
try:
  b = build_failure_bundle(out_dir=root / "bundles", run_id=RUN, case=case, result=result, verdict=verdict,
                         sources=sources_from_result(RUN, tmp, result), spans=[span], redactor=red, failing_step=2)
except Exception as exc:
  print("[3a] build REFUSED:", type(exc).__name__, str(exc)[:120], "| echoes raw:", S in str(exc))
  parts = list((root/"bundles").iterdir()); print("     left on disk:", [p.name[-12:] for p in parts])
  for pp in parts:
    for f in pp.rglob("*"):
      if f.is_file() and f.suffix!=".png": print("      ", f.relative_to(pp).as_posix(), raw_in(f))
  sys.exit(0)
print("[3a] bundle built:", b.name)
for p in sorted(x for x in b.rglob("*") if x.is_file()):
    if p.suffix != ".png":
        print("   ", p.relative_to(b).as_posix(), raw_in(p))
vals = cns.real_values(root)
out = cns.scan([p for p in b.rglob("*") if p.is_file()], vals)
print("[3a] check_no_secrets.scan values loaded:", len(vals), "leaks:", [str(k.name) for k, v in out.items() if not v])
m = load_bundle(b); print("[3a] load_bundle ok, files:", len(m.files))
# a JSON-escaped secret copy planted on purpose to see whether the scanner would notice it
probe = root / "esc.json"; probe.write_text(json.dumps({"x": S}), encoding="utf-8")
print("[3a'] scanner on a file holding json.dumps(secret) (escaped):", cns.scan([probe], vals)[probe], "(True=clean/miss)")

# --- 3b: tampered manifest names ---
def tamper(name_val, tag):
    d = root / "bundles" / f"t_{tag}"
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(b, d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    mf["files"][0]["name"] = name_val
    (d / "manifest.json").write_text(json.dumps(mf), encoding="utf-8")
    return d
# direct model construction
for label, nm in (("S (has : / \)", S), ("S_NOBS (legal chars)", S_NOBS)):
    try:
        bf = BundleFile(name=nm, kind=BundleFileKind.CASE, run_id=RUN, sha256="0"*64)
        print(f"[3b] BundleFile(name={label}): ACCEPTED name==secret {bf.name == nm}")
    except Exception as exc:
        print(f"[3b] BundleFile(name={label}) -> {type(exc).__name__}; str(exc) echoes secret:", echo(str(exc)))
        print("      ", str(exc).replace("\n", " | ")[:300])
for label, nm in (("S (has : / \)", S), ("S_NOBS (legal chars)", S_NOBS)):
    d = tamper(nm, "x%d" % (nm == S_NOBS))
    try:
        load_bundle(d); print(f"[3b] load_bundle tampered {label}: loaded OK")
    except Exception as exc:
        msg = str(exc)
        print(f"[3b] load_bundle tampered {label} -> {type(exc).__name__}: echoes raw: {echo(msg)}; msg={msg[:160]!r}")
        c = exc.__cause__
        if c is not None:
            print("      __cause__ str echoes raw:", echo(str(c)), "(traceback-visible only)")
