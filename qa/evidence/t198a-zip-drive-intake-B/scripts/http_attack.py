"""Seat B attack on the upload stream, Drive link route and gate seam. python -I http_attack.py <scratch>"""
import asyncio
import io
import json
import os
import shutil
import sys
import threading
import zipfile
from pathlib import Path

scr = Path(sys.argv[1])
base = scr / "httpwork"
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True)
root = base / "root"
root.mkdir()
os.environ["AUTOTESTER_ROOT"] = str(root)
from autotester.core.paths import ENV_ROOT

os.environ[ENV_ROOT] = str(root)
from fastapi.testclient import TestClient

from autotester.schema.project import Project
from autotester.schema.server_settings import ServerSettings
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
BOUNDARY = "xBOUNDARYx"
CT = f"multipart/form-data; boundary={BOUNDARY}"
UP = "/projects/demo/sources/upload"
DR = "/projects/demo/sources/drive"
R = {}


class Gate:
    def __init__(self, email="dev@vidysea.test", refuse=None, refuse_recheck=None):
        self.email, self.refuse, self.refuse_recheck = email, refuse, refuse_recheck
        self.checks, self.rechecks = 0, 0

    def check(self, request, slug):
        self.checks += 1
        if self.refuse:
            raise IntakeRefused(*self.refuse)
        return IntakeActor(email=self.email)

    def recheck(self, actor, slug):
        self.rechecks += 1
        if self.refuse_recheck:
            raise IntakeRefused(*self.refuse_recheck)


gate = Gate()
intake_gate.set_gate(gate)


def head(filename, label="x", extra=None, field="recording", cd_extra=""):
    parts = []
    for n, v in {**({"label": label} if label is not None else {}), **(extra or {})}.items():
        parts.append(f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n')
    parts.append(f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{field}"; '
                 f'filename="{filename}"{cd_extra}\r\nContent-Type: application/octet-stream\r\n\r\n')
    return "".join(parts).encode("utf-8")


TAIL = f"\r\n--{BOUNDARY}--\r\n".encode()


def chunked(data, size=65536):
    for i in range(0, len(data), size):
        yield data[i:i + size]


class Served:
    bytes = 0


async def _post(path, chunks, headers):
    served = Served()
    it = iter(chunks)
    sent = []
    done = {"b": False}

    async def receive():
        if done["b"]:
            await asyncio.sleep(0)
            return {"type": "http.disconnect"}
        try:
            c = next(it)
        except StopIteration:
            done["b"] = True
            return {"type": "http.request", "body": b"", "more_body": False}
        served.bytes += len(c)
        return {"type": "http.request", "body": c, "more_body": True}

    async def send(m):
        sent.append(m)

    raw = [(k.lower().encode(), v.encode("latin-1")) for k, v in headers.items()]
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
             "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
             "scheme": "http", "headers": raw, "server": ("localhost", 80),
             "client": ("127.0.0.1", 50000), "state": {}}
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    hdrs = dict((k.decode(), v.decode()) for m in sent if m["type"] == "http.response.start"
                for k, v in m["headers"])
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, body, served.bytes, hdrs


def post(path, chunks, ct=CT, cl=None, host="localhost", extra=None):
    h = {"content-type": ct, "host": host, **(extra or {})}
    if cl is not None:
        h["content-length"] = str(cl)
    return asyncio.run(_post(path, chunks, h))


def vid(tag, n=5000):
    return (f"MP4-{tag}|".encode() * (n // 8 + 1))[:n]


def state():
    rows = len(st.list_sources())
    files = [str(p.relative_to(root)) for p in root.rglob("*")
             if p.is_file() and ("/.work/" in str(p).replace("\\", "/")
                                 or "upload.part" in p.name or p.name.startswith(".tmp-"))]
    files = [f for f in files if "drive-jobs" not in f.replace("\\", "/")]
    recs = len([p for p in root.rglob("recording.*")])
    return dict(rows=rows, recordings=recs, leftovers=files)


def rec(name, **kw):
    R[name] = kw


def lower_has(body, *needles):
    t = body.decode("utf-8", "replace")
    return {n: (n in t) for n in needles}


# ---- gate before any byte
gate.refuse = (403, "no")
s, b, served, _ = post(UP, [head("a.mp4"), vid("a"), TAIL], cl=100)
rec("gate_refuse_upload", status=s, body_bytes_read=served, **state())
s, b, served, _ = post(DR, [b"link=abc"], ct="application/x-www-form-urlencoded")
rec("gate_refuse_drive", status=s, body_bytes_read=served, jobs=list((root / ".work").rglob("drive-jobs/**/*.json")) if (root / ".work").exists() else [])
gate.refuse = None

# ---- over limit, endless, no content-length
def endless(headb):
    yield headb
    n = 0
    while n < 200 * MIB:
        n += 65536
        yield b"z" * 65536


s, b, served, _ = post(UP, endless(head("big.mp4")))
rec("endless_no_cl", status=s, body_bytes_read=served, limit=5 * MIB, **state())
s, b, served, _ = post(UP, endless(head("big.mp4")), cl=100)
rec("endless_lying_small_cl", status=s, body_bytes_read=served, **state())
s, b, served, _ = post(UP, [head("big.mp4"), vid("x", 6 * MIB), TAIL], cl=10 * 1024**3)
rec("six_mib_lying_huge_cl", status=s, body_bytes_read=served, **state())
# exact limit ok, +1 refused
s, b, served, _ = post(UP, [head("exact.mp4"), vid("exact", 5 * MIB), TAIL])
rec("exact_limit", status=s, **state())
s, b, served, _ = post(UP, [head("plus1.mp4"), vid("plus1", 5 * MIB + 1), TAIL])
rec("limit_plus_1", status=s, **state())
# lying small CL with valid small body
s, b, served, _ = post(UP, [head("lie2.mp4"), vid("lie2", 3000), TAIL], cl=5)
rec("small_valid_lying_cl5", status=s, **state())
# truncated multipart
s, b, served, _ = post(UP, [head("trunc.mp4"), vid("trunc", 3000)])
rec("truncated_no_closing", status=s, **state())
s, b, served, _ = post(UP, [head("trunc2.mp4")[:60]])
rec("truncated_inside_head", status=s, **state())
# oversized part header
s, b, served, _ = post(UP, [head("hh.mp4", cd_extra='; x="' + "A" * 40000 + '"'), vid("hh"), TAIL])
rec("oversize_part_header", status=s, **state())
# header cap with header split into many tiny writes (value accumulates)
s, b, served, _ = post(UP, [head("hh2.mp4", cd_extra='; x="' + "A" * 30000 + '"')[i:i + 7] for i in range(0, 30100, 7)] + [vid("hh2"), TAIL])
rec("oversize_header_dribble", status=s, **state())
# missing / malformed boundary
for nm, ct in (("no_ct", ""), ("ct_text", "text/plain"), ("multipart_noboundary", "multipart/form-data"),
               ("boundary_empty", "multipart/form-data; boundary="), ("boundary_huge", "multipart/form-data; boundary=" + "b" * 5000),
               ("ct_urlencoded", "application/x-www-form-urlencoded")):
    try:
        s, b, served, _ = post(UP, [head("m.mp4"), vid("m"), TAIL], ct=ct)
    except Exception as e:
        s, b = f"EXC {type(e).__name__}: {e}"[:120], b""
    rec("ct_" + nm, status=s, **state())
# > 50 fields (non file) multipart
many = {f"f{i}": "v" for i in range(5000)}
s, b, served, _ = post(UP, [head("fields.mp4", extra=many), vid("fields"), TAIL])
rec("multipart_5000_fields", status=s, **state())
# fields after the file part
s, b, served, _ = post(UP, [head("late.mp4"), vid("late"), f"\r\n--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"uploaded_by\"\r\n\r\nevil@x\r\n--{BOUNDARY}--\r\n".encode()])
rec("field_after_file", status=s, **state())
# two files
s, b, served, _ = post(UP, [head("one.mp4"), vid("one"), b"\r\n", head("two.mp4")[len(b""):].split(b"\r\n\r\n", 1)[0].replace(b"x", b"x", 1) and f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"recording\"; filename=\"two.mp4\"\r\n\r\n".encode(), vid("two"), TAIL])
rec("two_files", status=s, **state())
# urlencoded drive form > 50 fields
s, b, served, _ = post(DR, ["&".join(f"f{i}=1" for i in range(60)).encode()], ct="application/x-www-form-urlencoded")
rec("drive_form_60_fields", status=s, body_has_trace=b"Traceback" in b)
s, b, served, _ = post(DR, [b"link=" + b"A" * (200 * 1024)], ct="application/x-www-form-urlencoded")
rec("drive_form_200k", status=s, bytes_read=served)
s, b, served, _ = post(DR, [b"\xff\xfe=\x00&link=\xc3\x28"], ct="application/x-www-form-urlencoded")
rec("drive_form_badutf", status=s)
# spoof fields
before = {s_.id for s_ in st.list_sources()}
s, b, served, _ = post(UP, [head("spoof.mp4", label="spoof", extra={"uploaded_by": "evil@x", "uploaded_at": "1999-01-01T00:00:00Z", "origin": "{}", "sha256": "0" * 64, "path": "/etc/passwd", "project": "other", "id": "SRC-EVIL"}), vid("spoof"), TAIL])
new = [x for x in st.list_sources() if x.id not in before]
rec("spoof_fields", status=s, stored=[dict(id=x.id, by=x.uploaded_by, at=str(x.uploaded_at), origin=x.origin.model_dump() if x.origin else None, path=str(x.path).replace(str(root), "ROOT"), label=x.label, sha=x.sha256[:8], project=x.project) for x in new])

# ---- filename attacks
names = ["../../evil.mp4", "..\\..\\evil.mp4", "C:\\Windows\\x.mp4", "<img src=x onerror=alert(1)>.mp4",
         "\"><script>alert(1)</script>.mp4", "a'b.mp4", "x&amp;y.mp4", "javascript:alert(1).mp4", "con.mp4", "a\u202e4pm.mp4", "x" * 3000 + ".mp4"]
fn_res = []
for i, n in enumerate(names):
    safe = n.replace('"', '\\"')
    s, b, served, _ = post(UP, [head(safe, label=f"lab{i}"), vid(f"fn{i}"), TAIL])
    fn_res.append((n[:40], s, b[:0].decode()))
rec("filename_variants", results=fn_res, **state())
# render sources page & check for raw markup
tc = TestClient(app, base_url="http://localhost")
page = tc.get("/projects/demo/sources").text
rec("sources_page_markup", raw_script=("<script>alert" in page), raw_img=("<img src=x" in page), len=len(page))
srcs = st.list_sources()
rec("stored_labels_origins", items=[(x.label and x.label[:50], x.origin.model_dump() if x.origin else None) for x in srcs][-6:], paths_under_root=all(str(root.resolve()) in str(Path(x.path).resolve()) for x in srcs if x.path))
# html in label field itself
s, b, _, _ = post(UP, [head("lbl.mp4", label="<script>alert(2)</script>"), vid("lbl"), TAIL])
page = tc.get("/projects/demo/sources").text
rec("label_script", status=s, raw_in_page=("<script>alert(2)" in page))

# ---- zip upload with hostile archive name & members
def mkzip(members):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        for n, d in members:
            zi = zipfile.ZipInfo("p")
            zi.filename = n
            zf.writestr(zi, d)
    return bio.getvalue()


zdata = mkzip([("<script>alert(3)</script>.mp4", vid("zz1")), ("<img src=x onerror=alert(4)>.txt", b"t"), ("../e.mp4", vid("zz2")), ("ok.mp4", vid("zz3"))])
for zname in ("<img src=x onerror=alert(5)>.zip", "\"><script>alert(6)</script>.zip", "a&b'c.zip"):
    s, b, _, _ = post(UP, [head(zname.replace('"', '\\"')), zdata, TAIL])
    t = b.decode("utf-8", "replace")
    rec("zip_name_" + zname[:12], status=s, raw_script=("<script>alert" in t), raw_img=("<img src=x" in t), has_escaped=("&lt;" in t))
    zdata = mkzip([("<script>alert(3)</script>.mp4", vid("zz1" + zname)), ("<img src=x onerror=alert(4)>.txt", b"t"), ("../e.mp4", vid("zz2")), ("ok.mp4", vid("zz3" + zname))])
rec("zip_state", **state())
# non-zip bytes named .zip, and .zip that is huge-empty
s, b, _, _ = post(UP, [head("fake.zip"), b"not a zip at all", TAIL])
rec("fake_zip", status=s, title_ok=(b"Nothing was added" in b), **state())

# ---- concurrency: same name at once
def concurrent(n, same_bytes):
    out = []
    def go(i):
        data = vid("conc", 20000) if same_bytes else vid(f"conc{i}", 20000)
        try:
            s, b, _, _ = post(UP, [head("same-name.mp4", label=f"c{i}"), data, TAIL])
        except Exception as e:
            s = f"EXC {e}"
        out.append(s)
    th = [threading.Thread(target=go, args=(i,)) for i in range(n)]
    [t.start() for t in th]
    [t.join() for t in th]
    return out
b0 = len(st.list_sources())
o = concurrent(6, True)
rec("conc_same_bytes", statuses=o, new_rows=len(st.list_sources()) - b0, **state())
b0 = len(st.list_sources())
o = concurrent(6, False)
rec("conc_diff_bytes_same_name", statuses=o, new_rows=len(st.list_sources()) - b0, ids_unique=len({x.id for x in st.list_sources()}) == len(st.list_sources()), **state())
# verify every row has file with matching sha
import hashlib
bad = []
for x in st.list_sources():
    if x.path:
        p = Path(x.path)
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != x.sha256:
            bad.append(x.id)
rec("rows_match_files", bad=bad, n=len(st.list_sources()))

# ---- Drive link route with fake drive
class FD:
    def __init__(self):
        self.calls = []
    def metadata(self, i):
        self.calls.append(("metadata", i)); raise RuntimeError("must not be called")
    list_folder = open = metadata


fd = FD()
routes_intake.drive_factory = lambda _s: fd
links = ["http://127.0.0.1/x", "file:///etc/passwd", "https://drive.google.com.evil.io/file/d/ABCDEF123/view",
         "https://evil.io/?u=https://drive.google.com/file/d/ABCDEF123/view", "https://user:pw@drive.google.com/file/d/ABCDEF123/view",
         "https://drive.google.com@evil.io/file/d/ABCDEF123/view", "https://drive.google.com:8443/file/d/ABCDEF123/view",
         "https://drive.google.com/uc?id=ABCDEF123&export=download&confirm=<script>alert(7)</script>",
         "https://drive.google.com/file/d/ABC%2FDEF123/view", "https://drive.google.com/file/d/ABCDEF;ls/view",
         "https://drive.google.com/file/d/../../../etc/view", "https://drive.google.com/open?id=a&id=b",
         "https://drive.google.com/file/d/AB/view", "ABCDEF123;calc", "ABCDEF123 && calc", "`calc`ABCDEF", "$(calc)ABCDEF", "ABC'DEF123",
         "ABC\"DEF123", "ABCDEF123\nrm", "<script>alert(8)</script>", "https://169.254.169.254/latest", "https://drive.google.com/drive/folders/ABCDEF123/../..",
         "https://drive.google.com\\@evil.io/file/d/ABCDEF123", "https://evil.io/redirect?to=https://drive.google.com/file/d/ABCDEF123",
         "HTTPS://DRIVE.GOOGLE.COM.:443/file/d/ABCDEF123/view", "https://drive.google.com./file/d/ABCDEF123/view",
         "https://xn--drive-google.com/file/d/ABCDEF123", "https://drive.google.com/file/d/\u0410BCDEF123/view", ""]
jobdir = root / ".work" / "drive-jobs"
echo = []
for l in links:
    from urllib.parse import urlencode
    s, b, served, hd = post(DR, [urlencode({"link": l}).encode()], ct="application/x-www-form-urlencoded")
    t = b.decode("utf-8", "replace")
    echoed = bool(l) and (l in t or l.replace("&", "&amp;") in t or l.replace("<", "&lt;") in t)
    echo.append((l[:50], s, "ECHO" if echoed else "-", hd.get("location", "")[:60]))
rec("drive_links", rows=echo, fake_drive_calls=fd.calls, jobs_made=sorted(str(p.name) for p in jobdir.rglob("*.json")) if jobdir.exists() else [])

print(json.dumps(R, indent=1, default=str))
