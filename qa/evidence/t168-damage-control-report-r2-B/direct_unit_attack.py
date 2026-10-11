import os, tempfile, sys
from pathlib import Path
d = Path(tempfile.mkdtemp(prefix="w"))
os.environ["AUTOTESTER_ROOT"] = str(d)
SEC = "Hunter2Pass"
(d/".env").write_text(f'DEMO_PASSWORD="{SEC}"\n')
sys.path.insert(0, str(Path(sys.argv[1])/"tests"))
from test_unified_report import _store
from autotester.stages import unified_report as ur
from autotester.schema.unified_report import UnifiedReport, HistorySection
from pydantic import ValidationError
store = _store(d)
out = []
# 1 ValidationError with an identifier-shaped dict key holding the secret
try:
    HistorySection.model_validate({"revisions":[{"revision":{"at":"x","summary":"s"},"counts":{SEC:"notint"}}]})
except ValidationError as e:
    out.append(("valerr-key", str(ur._unreadable(store, e))))
# 2 non-validation exceptions carrying the secret
for exc in (KeyError(SEC), RuntimeError(SEC), OSError(SEC), ValueError(SEC), ValueError(f"{d}/x/{SEC}.json: bad {SEC}"),
            ValueError(f"C:\a\{SEC}\release.json: {SEC}")):
    out.append((type(exc).__name__, str(ur._unreadable(store, exc))))
# 3 redactor load failing -> fallback
orig = ur._load_redactor
def boom(s): raise RuntimeError(SEC)
ur._load_redactor = boom
try:
    e = ValidationError.from_exception_data("X", [])
except Exception: e = None
try:
    HistorySection.model_validate({"revisions":[{"revision":{"at":"x","summary":"s"},"counts":{SEC:"notint"}}]})
except ValidationError as e2:
    out.append(("valerr-key-no-redactor", str(ur._unreadable(store, e2))))
ur._load_redactor = orig
for k, m in out:
    print(k, "|", m, "| LEAK" if SEC in m else "| clean")
# 4 context retained?
try:
    try:
        raise ValueError(f"{d}/release.json: input_value={SEC}")
    except Exception as exc:
        raise ur._unreadable(store, exc) from None
except ur.ReportUnreadable as r:
    print("context-retained:", repr(r.__context__)[:80], "suppress:", r.__suppress_context__)
