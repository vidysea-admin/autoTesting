"""Seat B: single-writer job file, fault injection, Drive lies, memory slope of the entry parse."""
import ctypes
import ctypes.wintypes as wt
import json
import os
import shutil
import sys
import threading
import time
import zipfile
from pathlib import Path

scr = Path(sys.argv[1])
base = scr / "miscwork"
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True)
root = base / "root"
root.mkdir()
os.environ["AUTOTESTER_ROOT"] = str(root)
from autotester.core.paths import ENV_ROOT

os.environ[ENV_ROOT] = str(root)
sys.path.insert(0, "D:/autoTesting/.worktrees/t198a-zip-drive-intake/tests")
from drive_fakes import FakeDrive

from autotester.schema.intake import DriveJob, DriveRef
from autotester.schema.project import Project
from autotester.sources import drive_jobs
from autotester.sources.drive_intake import intake_drive
from autotester.sources.zip_intake import expand_zip
from autotester.store.project_store import ProjectStore

st = ProjectStore("demo", root)
st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                        allowed_domains=["demo.test"]))
R = {}


def data(n, tag):
    unit = f"MP4-{tag}|".encode()
    return (unit * (n // len(unit) + 1))[:n]


# single writer + polling reader (the real flow)
job = DriveJob(id="01M4M62SK47SH3SXBPAF6RNYMB", project="demo", drive_id="ABCDEF123")
drive_jobs.save_job(root, job)
errs, none_reads, stop = [], [0], [False]


def writer():
    for i in range(400):
        try:
            drive_jobs.save_job(root, job.model_copy(update={"message": f"m{i}"}))
        except Exception as e:
            errs.append(type(e).__name__)


def reader():
    while not stop[0]:
        if drive_jobs.load_job(root, "demo", job.id) is None:
            none_reads[0] += 1


rd = threading.Thread(target=reader)
w = threading.Thread(target=writer)
rd.start()
w.start()
w.join()
stop[0] = True
rd.join()
R["job_single_writer"] = dict(writer_errors=errs[:5], n_err=len(errs), reader_none=none_reads[0],
                              leftovers=[p.name for p in (root / ".work" / "drive-jobs" / "demo").iterdir() if p.suffix != ".json"])

# fault injection: add_source raises on 2nd member
zp = base / "three.zip"
with zipfile.ZipFile(zp, "w") as zf:
    for t in "abc":
        zf.writestr(f"{t}.mp4", data(4000, t))
calls = [0]
orig = ProjectStore.add_source


def flaky(self, source):
    calls[0] += 1
    if calls[0] == 2:
        raise OSError("boom")
    return orig(self, source)


ProjectStore.add_source = flaky
rep = expand_zip(st, zp)
ProjectStore.add_source = orig
rows = st.list_sources()
files = [p for p in root.rglob("recording.*")]
R["fault_member2"] = dict(status=rep.status.value, outcomes=[m.outcome.value for m in rep.members],
                          rows=len(rows), files=len(files),
                          row_without_file=[r.id for r in rows if not Path(r.path).is_file()],
                          staging_left=[str(p) for p in (root / ".work").rglob("*") if p.is_file() and p.name != "server_settings.json"])
rep = expand_zip(st, zp)
R["rerun_converges"] = dict(outcomes=[m.outcome.value for m in rep.members], rows=len(st.list_sources()),
                            files=len(list(root.rglob("recording.*"))))
# kill-window: a file without a row (simulate), next intake sweeps it
orphan_dir = st.paths.sources_dir / "src_orphanxxxxxx"
orphan_dir.mkdir(parents=True)
(orphan_dir / "recording.mp4").write_bytes(b"x")
expand_zip(st, zp)
R["orphan_swept"] = not orphan_dir.exists()

# Drive lies: wrong md5, short read, no checksums, huge declared size
fd = FakeDrive()
good = data(3000, "lie")
fd.add("LIEMD5AAAA", good)
fd.lie["LIEMD5AAAA"] = {"md5": "0" * 32}
fd.add("SHORTREAD1", good)
fd.lie["SHORTREAD1"] = {"size": 99999}
before = len(st.list_sources())
for fid in ("LIEMD5AAAA", "SHORTREAD1"):
    rep = intake_drive(st, DriveRef(id=fid), fd, uploaded_by="u@x")
    R[f"drive_{fid}"] = [(m.outcome.value, m.reason) for m in rep.members]
R["drive_lies_rows_added"] = len(st.list_sources()) - before
R["drive_lies_leftovers"] = [str(p) for p in (root / ".work").rglob("*") if p.is_file() and p.name != "server_settings.json" and "drive-jobs" not in str(p)]
R["drive_downloads_closed"] = all(d.closed for d in fd.downloads)


# memory slope of the central-directory parse (entries cap is 1000; zip is parsed in full first)
class PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def peak_mb():
    pmc = PMC()
    pmc.cb = ctypes.sizeof(pmc)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), wt.DWORD]
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.PeakWorkingSetSize / 1e6


N = int(sys.argv[2]) if len(sys.argv) > 2 else 300_000
mz = base / "many.zip"
import subprocess
_gen = ("import zipfile,sys\nN=int(sys.argv[2])\nzf=zipfile.ZipFile(sys.argv[1],'w')\n"
        "for i in range(N): zf.writestr(zipfile.ZipInfo('d/%d.txt'%i), b'')\nzf.close()")
subprocess.run([sys.executable, "-I", "-c", _gen, str(mz), str(N)], check=True)
base_mb = peak_mb()
t0 = time.time()
rep = expand_zip(st, mz)
R["many_entries"] = dict(entries=N, zip_mb=round(mz.stat().st_size / 1e6, 1), secs=round(time.time() - t0, 1),
                         peak_ws_before_mb=round(base_mb), peak_ws_after_mb=round(peak_mb()),
                         bytes_per_entry_mem=round((peak_mb() - base_mb) * 1e6 / N),
                         zip_bytes_per_entry=round(mz.stat().st_size / N), result=rep.members[0].reason)
print(json.dumps(R, indent=1, default=str))
