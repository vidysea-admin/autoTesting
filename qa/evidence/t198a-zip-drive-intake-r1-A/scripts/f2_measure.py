"""Seat A r1 F2 measurement: drive the real app at ASGI level, measure tracemalloc peak vs body size."""
import sys, os, tempfile, shutil, tracemalloc, hashlib, json
from pathlib import Path
tree = Path(sys.argv[1]); work = Path(sys.argv[2])
os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
sys.path[:0] = [str(tree / "src"), str(tree / "tests")]
import autotester; assert str(tree) in autotester.__file__
from asgi_helpers import BOUNDARY, CHUNK, multipart_tail, post_stream
from autotester.core.paths import ENV_ROOT
from autotester.schema.project import Project
from autotester.schema.server_settings import ServerSettings
from autotester.store.project_store import ProjectStore
from autotester.store.server_settings import save_server_settings
UPLOAD = "/projects/demo/sources/upload"
MIB = 1 << 20

def fresh(limit=8 * MIB):
    root = Path(tempfile.mkdtemp(dir=work)); os.environ[ENV_ROOT] = str(root)
    st = ProjectStore("demo", root)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"]))
    save_server_settings(ServerSettings(max_upload_bytes=limit), root)
    return root, st

def field(name, value):
    nm = f'; name="{name}"' if name is not None else ""
    return f'--{BOUNDARY}\r\nContent-Disposition: form-data{nm}\r\n\r\n{value}\r\n'

def filepart_head(fn="a.mp4"):
    return (f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="recording"; filename="{fn}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n').encode()

def gen_fields(n, name_fn, val, enc=True, batch=2000):
    buf = []
    for i in range(n):
        buf.append(field(name_fn(i), val))
        if len(buf) >= batch:
            yield "".join(buf).encode(); buf = []
    if buf: yield "".join(buf).encode()

def filechunks(size):
    left = size
    blk = b"V" * CHUNK
    while left > 0:
        n = min(left, CHUNK); yield blk[:n]; left -= n

def leftovers(root):
    n = 0
    for area in ("intake", "drive-fetch", "gws", "uploads"):
        b = root / ".work" / area
        if b.exists(): n += sum(1 for p in b.rglob("*") if p.is_file())
    return n

def run(label, chunks_fn, limit=8 * MIB, body_size=None):
    root, st = fresh(limit)
    tracemalloc.start(); tracemalloc.reset_peak()
    status, page, served = post_stream(UPLOAD, chunks_fn())
    cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    rec = dict(case=label, status=status, served_kib=served.bytes // 1024, peak_kib=peak // 1024,
               sources=len(st.list_sources()), leftover_files=leftovers(root),
               rec_files=len(list(st.paths.sources_dir.rglob("recording.*"))) if st.paths.sources_dir.exists() else 0,
               msg=(page.decode("utf-8", "replace").split("<p")[1][:0] if False else ""))
    shutil.rmtree(root, ignore_errors=True)
    print(json.dumps(rec), flush=True)
    return rec

only = sys.argv[3] if len(sys.argv) > 3 else "all"
big = 64 * MIB  # limit for big-body cases so the body-size limit is not what stops them
# A: many tiny fields BEFORE the file (name-count cap)
for n in (1_000, 10_000, 100_000):
    run(f"A tiny fields before file n={n}", lambda n=n: iter([*gen_fields(n, lambda i: f"f{i}", "v"), filepart_head(), *filechunks(4096), multipart_tail()]) if n <= 10_000 else
        (c for g in (gen_fields(n, lambda i: f"f{i}", "v"), [filepart_head()], filechunks(4096), [multipart_tail()]) for c in g), limit=big)
# B: few large fields
for k, sz in ((2, 15 * 1024), (5, 15 * 1024), (3, 16 * 1024), (1, 16 * 1024 + 1)):
    run(f"B {k} fields x {sz}B before file", lambda k=k, sz=sz: iter([*gen_fields(k, lambda i: f"f{i}", "x" * sz), filepart_head(), *filechunks(4096), multipart_tail()]))
# C: interleaved: before + after the file part
def interleaved(nb, sb, na, sa):
    def g():
        yield "".join(field(f"b{i}", "x" * sb) for i in range(nb)).encode()
        yield filepart_head(); yield from filechunks(4096)
        yield f"\r\n".encode()  # close file part data
        yield "".join(field(f"a{i}", "y" * sa) for i in range(na)).encode()
        yield f"--{BOUNDARY}--\r\n".encode()
    return g
run("C interleaved 2x7KiB before + 2x7KiB after (ok total 28KiB)", interleaved(2, 7168, 2, 7168))
run("C interleaved 4x7KiB before + 4x7KiB after (>32KiB total)", interleaved(4, 7168, 4, 7168))
run("C interleaved 1 before + 3000 tiny after", interleaved(1, 5, 3000, 1))
run("C 0 before + 20 fields after", interleaved(0, 1, 20, 10))
# D: nameless fields
def nameless(n):
    def g():
        yield from gen_fields(n, lambda i: None, "v")
        yield filepart_head(); yield from filechunks(4096); yield multipart_tail()
    return g
for n in (1_000, 100_000):
    run(f"D nameless tiny fields before file n={n}", nameless(n), limit=big)
def nameless_big():
    yield field(None, "z" * 20000).encode(); yield filepart_head(); yield from filechunks(4096); yield multipart_tail()
run("D one nameless 20KiB field", nameless_big)
def emptyname(n):
    def g():
        yield from gen_fields(n, lambda i: "", "v")
        yield filepart_head(); yield from filechunks(4096); yield multipart_tail()
    return g
run("D empty-name tiny fields n=100000", emptyname(100_000), limit=big)
# F: repeated same name
def same(n):
    def g():
        yield from gen_fields(n, lambda i: "label", "v")
        yield filepart_head(); yield from filechunks(4096); yield multipart_tail()
    return g
run("F same-name 'label' x 100000", same(100_000), limit=big)
# G: legit form
def legit(size):
    def g():
        yield field("label", "My demo").encode(); yield filepart_head(); yield from filechunks(size); yield multipart_tail()
    return g
run("G legit label+file 1MiB", legit(1 * MIB))
run("G legit label+file 300MiB (limit 512MiB)", legit(300 * MIB), limit=512 * MIB)
