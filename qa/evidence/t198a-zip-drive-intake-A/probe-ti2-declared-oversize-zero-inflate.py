import io, os, sys, zipfile
from pathlib import Path
DATA = Path(sys.argv[1]); ROOT = DATA/"root"; ROOT.mkdir(exist_ok=True)
os.environ["AUTOTESTER_ROOT"] = str(ROOT)
import autotester.sources.zip_intake as zi
from autotester.store.project_store import ProjectStore
calls = []
orig_inflate = zi._inflate
def spy(*a, **k):
    calls.append(1); return orig_inflate(*a, **k)
zi._inflate = spy
p = DATA/"big.zip"
with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as z:
    z.writestr("a.mp4", os.urandom(2*1024*1024))
r = zi.expand_zip(ProjectStore("p1", ROOT), p, max_file_bytes=1024*1024)
print(r.status.value, [(m.outcome.value, m.reason) for m in r.members], "inflate calls:", len(calls))
