"""Seat B: Drive seam, job page, gate recheck, job file writes, big-body and boundary retests."""
import asyncio
import hashlib
import json
import os
import shutil
import sys
import threading
import time
from pathlib import Path

scr = Path(sys.argv[1])
base = scr / "drivework"
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True)
root = base / "root"
root.mkdir()
os.environ["AUTOTESTER_ROOT"] = str(root)
from autotester.core.paths import ENV_ROOT

os.environ[ENV_ROOT] = str(root)
sys.path.insert(0, "D:/autoTesting/.worktrees/t198a-zip-drive-intake/tests")
from drive_fakes import FakeDrive
from fastapi.testclient import TestClient
from gws_fakes import CANARY, FakeRunner, error, meta, ok_json

from autotester.schema.intake import DriveJob, DriveRef
from autotester.schema.project import Project
from autotester.schema.server_settings import ServerSettings
from autotester.sources import drive_jobs
from autotester.sources.drive_intake import intake_drive
from autotester.sources.gws_drive import GwsDrive
from autotester.sources.gws_runner import SubprocessGwsRunner
from autotester.store.project_store import ProjectStore
from autotester.store.server_settings import save_server_settings
from autotester.ui import intake_gate, routes_intake
from autotester.ui.app import app
from autotester.ui.intake_gate import IntakeActor, IntakeRefused

st = ProjectStore("demo", root)
st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                        allowed_domains=["demo.test"]))
MIB = 1024 * 1024
save_server_settings(ServerSettings(max_upload_bytes=5 * MIB), root)
R = {}
BOUNDARY = "xBx"
tc = TestClient(app, base_url="http://localhost", raise_server_exceptions=False)


class Gate:
    def __init__(self):
        self.email = "dev@vidysea.test"
        self.refuse_recheck = None
        self.rechecks = 0

    def check(self, request, slug):
        return IntakeActor(email=self.email)

    def recheck(self, actor, slug):
        self.rechecks += 1
        if self.refuse_recheck:
            raise IntakeRefused(*self.refuse_recheck)


gate = Gate()
intake_gate.set_gate(gate)


def data(n, tag):
    unit = f"MP4-{tag}|".encode()
    return (unit * (n // len(unit) + 1))[:n]


def mp(filename, body):
    return (f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="recording"; filename="{filename}"'
            f"\r\n\r\n").encode() + body + f"\r\n--{BOUNDARY}--\r\n".encode()


ct = {"content-type": f"multipart/form-data; boundary={BOUNDARY}"}
# 6 MiB real (limit 5 MiB) with lying huge Content-Length
r = tc.post("/projects/demo/sources/upload", content=mp("six.mp4", data(6 * MIB, "six")),
            headers={**ct})
R["six_mib_real_body"] = dict(status=r.status_code, rows=len(st.list_sources()))
# huge boundary through a real-ish client: status/body
r = tc.post("/projects/demo/sources/upload", content=b"x",
            headers={"content-type": "multipart/form-data; boundary=" + "b" * 5000})
R["boundary_5000"] = dict(status=r.status_code, body=r.text[:200])
r = tc.post("/projects/demo/sources/upload", content=b"x",
            headers={"content-type": 'multipart/form-data; boundary="a b/..\\c"'})
R["boundary_quoted_weird"] = dict(status=r.status_code, body=r.text[:120])
r = tc.post("/projects/demo/sources/upload", content=b"x",
            headers={"content-type": "multipart/form-data; boundary=" + "b" * 256})
R["boundary_256"] = dict(status=r.status_code, body=r.text[:120])
r = tc.post("/projects/demo/sources/upload", content=b"x",
            headers={"content-type": "multipart/form-data; boundary=" + "b" * 257})
R["boundary_257"] = dict(status=r.status_code, body=r.text[:120])
# cross-origin POST: refused before gate/body
r = tc.post("/projects/demo/sources/upload", content=mp("o.mp4", data(500, "o")),
            headers={**ct, "origin": "https://evil.example"})
R["cross_origin_upload"] = dict(status=r.status_code, rows=len(st.list_sources()))
r = tc.post("/projects/demo/sources/drive", data={"link": "ABCDEF123"},
            headers={"origin": "https://evil.example"})
R["cross_origin_drive"] = dict(status=r.status_code)
r = tc.post("/projects/demo/sources/upload", content=mp("o.mp4", data(500, "o2")),
            headers={**ct, "host": "evil.example"})
R["hostile_host_upload"] = dict(status=r.status_code, rows=len(st.list_sources()))
# slug attacks
for slug in ("..", "..%2f..", "demo%2f..%2fother", "nope", "DEMO", "a" * 300):
    r = tc.post(f"/projects/{slug}/sources/upload", content=mp("o.mp4", data(500, "o3")), headers=ct)
    R[f"slug_{slug[:12]}"] = r.status_code
for jid in ("..", "..%2f..%2fsecret", "0" * 26, "01M4M62SK47SH3SXBPAF6RNYM%00", "a" * 26, "%2e%2e"):
    r = tc.get(f"/projects/demo/sources/drive/{jid}")
    R[f"job_{jid[:14]}"] = r.status_code

# --- Drive with FakeDrive through the route: spoof + recheck
fd = FakeDrive()
good = data(3000, "gd")
fd.add("GOODID123", good, name="<img src=x onerror=alert(9)>.mp4")
routes_intake.drive_factory = lambda _s: fd


def run_job(link, extra=None):
    r = tc.post("/projects/demo/sources/drive", data={"link": link, **(extra or {})},
                follow_redirects=False)
    loc = r.headers.get("location", "")
    for _ in range(100):
        page = tc.get(loc) if loc else None
        if page is not None and "refresh" not in page.text[:200]:
            return r.status_code, loc, page.text
        time.sleep(0.1)
    return r.status_code, loc, page.text if page is not None else ""


s, loc, page = run_job("GOODID123", {"uploaded_by": "evil@x"})
src = [x for x in st.list_sources() if getattr(x.origin, "file_id", None) == "GOODID123"]
R["drive_good_spoof"] = dict(status=s, by=[x.uploaded_by for x in src], origin=[x.origin.model_dump() for x in src],
                             raw_img="<img src=x" in page, escaped="&lt;img" in page, rechecks=gate.rechecks)
gate.refuse_recheck = (403, "You no longer have permission")
fd.opened.clear()
fd.add("OTHERID123", data(3000, "o4"))
s, loc, page = run_job("OTHERID123")
R["drive_recheck_refused"] = dict(status=s, opened=list(fd.opened), page_has_refused=("refused" in page.lower()),
                                  rows_for=len([x for x in st.list_sources() if getattr(x.origin, 'file_id', None) == 'OTHERID123']))
gate.refuse_recheck = None

# --- gws seam: errors containing HTML/canary; folder with hostile ids and names
def on_run(args):
    pj = json.loads(args[args.index("--params") + 1])
    if "q" in pj:
        return ok_json({"files": [
            {"id": "x;calc", "name": "$(calc).mp4", "mimeType": "video/mp4", "size": "10", "md5Checksum": "0" * 32},
            {"id": "GOODFILE01", "name": "..\\..\\evil<script>.mp4", "mimeType": "video/mp4", "size": "20"},
            {"id": "-rf", "name": "a.mp4", "mimeType": "video/mp4"},
            {"id": "SUBFOLDER01", "name": "<b>sub</b>", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "DOC123456", "name": "x.pdf", "mimeType": "application/pdf"}]})
    fid = pj["fileId"]
    if fid == "BOOMERR123":
        return error(403, f"<script>alert(10)</script> Bearer {CANARY}", "forbidden")
    if fid == "GOODFILE01":
        return ok_json(meta("GOODFILE01", name="..\\..\\evil<script>.mp4", size=20, md5=hashlib.md5(b"v" * 20).hexdigest()))
    return ok_json(meta(fid, name="folder", mime="application/vnd.google-apps.folder"))


runner = FakeRunner(on_run, body=b"v" * 20)
gd = GwsDrive(runner, root / ".work" / "gwsfake", limit_bytes=lambda: 5 * MIB)
rep = intake_drive(st, DriveRef(id="FOLDERID01", kind="folder"), gd, uploaded_by="dev@vidysea.test")
R["gws_folder_hostile"] = dict(rows=[(m.member, m.outcome.value, m.reason) for m in rep.members],
                               all_argv_tokens=sorted({t for c in runner.run_calls + [d["args"] for d in runner.download_calls] for t in c if not t.startswith("{")})[:12],
                               any_arg_contains_metachar=any(any(ch in a for ch in ";&`$|") for c in runner.run_calls for a in c if not a.startswith("{")),
                               download_ids=[json.loads(d["args"][d["args"].index("--params") + 1])["fileId"] for d in runner.download_calls])
rep = intake_drive(st, DriveRef(id="BOOMERR123"), gd, uploaded_by=None)
msg = json.dumps([(m.member, m.reason) for m in rep.members])
R["gws_error_text"] = dict(rows=msg, has_canary=CANARY in msg, has_script="<script>" in msg)
# job page for that error through the route
fd2 = FakeDrive()
from autotester.sources.drive_errors import DriveError, DriveFailure

fd2.error = DriveError(DriveFailure.PERMISSION_DENIED)
routes_intake.drive_factory = lambda _s: fd2
s, loc, page = run_job("BOOMERR123")
R["job_page_typed_error"] = dict(status=s, has_fixed_msg=("refused access" in page), traceback=("Traceback" in page))

# --- real subprocess runner: argv list, no shell. Recorder script prints argv json
rec = base / "recorder.py"
rec.write_text("import sys,json\nprint(json.dumps({'id':'ABCDEF123','name':'a.mp4','mimeType':'video/mp4'}))\nopen(sys.argv[0]+'.argv','w').write(json.dumps(sys.argv[1:]))\n", encoding="utf-8")
sub = SubprocessGwsRunner(command=[sys.executable, str(rec)])
gd2 = GwsDrive(sub, root / ".work" / "gwsreal", limit_bytes=lambda: MIB)
item = gd2.metadata("-abc_DEF-1")
argv = json.loads(Path(str(rec) + ".argv").read_text())
R["real_subprocess_argv"] = dict(argv=argv, item=item.id)
try:
    gd2.metadata("abc;calc")
except Exception as e:
    R["real_subprocess_bad_id"] = type(e).__name__
sys_marker = base / "PWNED"
try:
    gd2.metadata('x"; echo y > ' + str(sys_marker))
except Exception as e:
    R["real_subprocess_inject"] = type(e).__name__
R["pwned_marker_exists"] = sys_marker.exists()

# --- job file concurrency (two writers + a reader on the same job), Windows os.replace
job = DriveJob(id="01M4M62SK47SH3SXBPAF6RNYMA", project="demo", drive_id="ABCDEF123")
drive_jobs.save_job(root, job)
errs = []
stop = False


def writer():
    for _ in range(300):
        try:
            drive_jobs.save_job(root, job)
        except Exception as e:
            errs.append(type(e).__name__ + ":" + str(e)[:60])


def reader():
    bad = 0
    while not stop:
        j = drive_jobs.load_job(root, "demo", job.id)
        if j is None:
            bad += 1
    errs.append(f"reader_none={bad}")


th = [threading.Thread(target=writer) for _ in range(2)]
rd = threading.Thread(target=reader)
rd.start()
[t.start() for t in th]
[t.join() for t in th]
stop = True
rd.join()
R["job_file_two_writers_one_reader"] = errs[:6]
R["job_dir"] = sorted(p.name for p in (root / ".work" / "drive-jobs" / "demo").iterdir())[:5]

# --- stale lock takeover race (intake_lock) quick look
from autotester.sources.intake_commit import intake_lock

R["lock_basic"] = "ok"
with intake_lock(st) as beat:
    beat()
print(json.dumps(R, indent=1, default=str))
