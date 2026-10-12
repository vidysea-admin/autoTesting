"""Seat B hostile-zip attack against expand_zip. Run: python -I zip_attack.py <scratch>"""
import json
import os
import shutil
import stat
import struct
import sys
import time
import tracemalloc
import warnings
import zipfile
from pathlib import Path

scr = Path(sys.argv[1])
base = scr / "zipwork"
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True)
from autotester.core.paths import ENV_ROOT
from autotester.schema.intake import ZipLimits
from autotester.schema.project import Project
from autotester.sources.zip_intake import expand_zip
from autotester.store.project_store import ProjectStore


def video(tag, n=4096):
    return (f"MP4-{tag}|".encode() * (n // 8 + 1))[:n]


def add(zf, name, data=b"", mode=None, comp=zipfile.ZIP_STORED):
    zi = zipfile.ZipInfo("placeholder")
    zi.filename = name
    zi.compress_type = comp
    if mode is not None:
        zi.create_system = 3
        zi.external_attr = mode << 16
    zf.writestr(zi, data)


def fresh(case):
    root = base / case / "root"
    root.mkdir(parents=True)
    os.environ[ENV_ROOT] = str(root)
    st = ProjectStore("demo", root)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                            allowed_domains=["demo.test"]))
    (base / case / "SENTINEL_above.txt").write_bytes(b"sentinel")
    return st, root


def snapshot(case_dir):
    return {str(p.relative_to(case_dir)): p.stat().st_size
            for p in case_dir.rglob("*") if p.is_file()}


results = {}


def run(case, build, **kw):
    st, root = fresh(case)
    case_dir = base / case
    z = case_dir / "in.zip"
    build(z)
    t0 = time.time()
    rep = expand_zip(st, z, **kw)
    dt = time.time() - t0
    snap = snapshot(case_dir)
    outside = [k for k in snap if not k.replace("\\", "/").startswith("root/")
               and k not in ("in.zip", "SENTINEL_above.txt")]
    norm = {k.replace("\\", "/"): v for k, v in snap.items()}
    leftovers = [k for k in norm if "/intake/" in k or "upload.part" in k or ".tmp-" in k
                 or "download.part" in k or ".intake.lock" in k]
    recs = [k for k in norm if "/recording." in k]
    sent_ok = (case_dir / "SENTINEL_above.txt").read_bytes() == b"sentinel"
    rows_on_disk = len(st.list_sources())
    results[case] = dict(status=rep.status.value,
                         rows=[(m.member, m.outcome.value, m.reason) for m in rep.members],
                         notes=rep.notes, outside=outside, leftovers=leftovers,
                         n_recordings=len(recs), n_source_rows=rows_on_disk,
                         sentinel_ok=sent_ok, secs=round(dt, 2))
    return st, rep


def zipof(members, **k):
    def b(p):
        with zipfile.ZipFile(p, "w") as zf:
            for item in members:
                add(zf, item[0], item[1], **k)
    return b


hostile = {
    "dotdot_fwd": "../evil.mp4", "dotdot_back": "..\\evil.mp4", "mid_fwd": "a/../../evil.mp4",
    "mid_back": "a\\..\\..\\evil.mp4", "abs_fwd": "/abs.mp4", "abs_back": "\\abs.mp4",
    "drive_slash": "C:\\x.mp4", "drive_noslash": "C:x.mp4", "unc": "\\\\host\\share\\x.mp4",
    "ads": "a.mp4:evil", "ads2": "a.mp4::$DATA", "con": "CON.mp4", "nul": "NUL",
    "aux_ext": "aux.txt", "dir_con": "ok/CON/x.mp4", "com1": "com1.mp4", "lpt1_sp": "LPT1 .mp4",
    "con_dot": "con..mp4", "nulbyte": "a.mp4\x00.exe", "rlo": "\u202e4pm.exe",
    "bidi_in_video": "clip\u202e4pm.mp4", "ctrl": "a\x07b.mp4", "newline": "a\nb.mp4",
    "trail_dot": "clip.mp4.", "trail_space": "clip.mp4 ", "nfkc_dots": "\uff0e\uff0e/evil.mp4",
    "fullwidth_slash": "..\uff0fevil.mp4", "long": "x" * 5000 + ".mp4",
    "unicode_nfd": "e\u0301\u0301.mp4", "html": "<script>alert(1)</script>.mp4",
    "img": "<img src=x onerror=alert(1)>.mp4", "dotdir": "./././evil.mp4",
    "empty_part": "a//b.mp4",
}
for k, name in hostile.items():
    def b(p, name=name, k=k):
        with zipfile.ZipFile(p, "w") as zf:
            add(zf, name, video(k))
            add(zf, "benign.mp4", video("benign"))
    run("h_" + k, b)

for label, mode in (("symlink", stat.S_IFLNK | 0o777), ("chr", stat.S_IFCHR | 0o666),
                    ("fifo", stat.S_IFIFO | 0o666), ("sock", stat.S_IFSOCK | 0o666)):
    def b(p, mode=mode):
        with zipfile.ZipFile(p, "w") as zf:
            add(zf, "link.mp4", b"/etc/passwd", mode=mode)
            add(zf, "benign.mp4", video("benign"))
    run("mode_" + label, b)


def dup(p):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(p, "w") as zf:
            add(zf, "same.mp4", video("one"))
            add(zf, "same.mp4", video("two"))
            add(zf, "SAME.mp4", video("three"))


run("dup_names", dup)


def dupbytes(p):
    with zipfile.ZipFile(p, "w") as zf:
        add(zf, "a/clip.mp4", video("same"))
        add(zf, "b/clip.mp4", video("same"))


st, _ = run("dup_bytes", dupbytes)
rep2 = expand_zip(st, base / "dup_bytes" / "in.zip")
results["dup_bytes_second_upload"] = [m.outcome.value for m in rep2.members]

run("notzip_garbage", lambda p: p.write_bytes(os.urandom(5000)))
run("notzip_text", lambda p: p.write_text("hello"))
run("notzip_empty", lambda p: p.write_bytes(b""))
run("nonvideo", zipof([("run.exe", b"MZ"), (".env", b"SECRET=1"), ("x.ps1", b"calc"),
                       ("doc.pdf", b"%PDF"), ("noext", b"a"), ("dir/", b""),
                       ("ok.mp4", video("ok"))]))
run("nested", zipof([("inner.zip", b"PK\x03\x04aaaa"), ("a.tar", b"x"), ("b.7z", b"7z"),
                     ("c.gz", b"\x1f\x8b"), ("sneaky.mp4", b"PK\x03\x04" + b"x" * 50),
                     ("gz.mp4", b"\x1f\x8b\x08" + b"x" * 50), ("ok.mp4", video("ok"))]))
run("entries_cap", zipof([(f"f{i}.txt", b"x") for i in range(30)]),
    limits=ZipLimits(max_entries=20))


def ratio(p):
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.mp4", b"\0" * (30 * 1024 * 1024))
        add(zf, "ok.mp4", video("ok"))


run("ratio_bomb", ratio)
run("perfile", zipof([("big.mp4", video("big", 200_000)), ("ok.mp4", video("ok"))]),
    max_file_bytes=100_000)
run("total_cap", zipof([(f"v{i}.mp4", video(f"v{i}", 60_000)) for i in range(5)]),
    limits=ZipLimits(max_total_bytes=150_000))
run("video_count", zipof([(f"v{i}.mp4", video(f"v{i}")) for i in range(25)]))
run("archive_size", zipof([("ok.mp4", video("ok", 100_000))]),
    limits=ZipLimits(max_archive_bytes=10_000))


def patch_sizes(path, new_usize=None, new_csize=None):
    data = bytearray(path.read_bytes())
    i = data.rfind(b"PK\x01\x02")
    if new_csize is not None:
        struct.pack_into("<I", data, i + 20, new_csize)
    if new_usize is not None:
        struct.pack_into("<I", data, i + 24, new_usize)
    path.write_bytes(bytes(data))


def lie_under(p):
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lie.mp4", video("lie", 3_000_000))
    patch_sizes(p, new_usize=100)


run("lie_understate", lie_under)


def lie_over(p):
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lie.mp4", video("lie", 3000))
    patch_sizes(p, new_usize=50_000_000)


run("lie_overstate", lie_over)


def lie_under_stored(p):
    with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("lie.mp4", video("lie", 3_000_000))
    patch_sizes(p, new_usize=100, new_csize=100)


run("lie_understate_stored", lie_under_stored)


def lie_bomb(p):
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lie.mp4", b"\0" * (30 * 1024 * 1024))
    patch_sizes(p, new_usize=900_000)


run("lie_bomb_understate", lie_bomb)


def z64(p):
    with zipfile.ZipFile(p, "w") as zf:
        with zf.open("z64.mp4", "w", force_zip64=True) as f:
            f.write(video("z64"))
        add(zf, "ok.mp4", video("ok"))


run("zip64", z64)


def enc(p):
    with zipfile.ZipFile(p, "w") as zf:
        add(zf, "secret.mp4", video("enc"))
        add(zf, "ok.mp4", video("ok"))
    d = bytearray(p.read_bytes())
    for sig, off, nlen_off, name_off in ((b"PK\x03\x04", 6, 26, 30), (b"PK\x01\x02", 8, 28, 46)):
        pos = 0
        while (pos := d.find(sig, pos)) != -1:
            n = struct.unpack_from("<H", d, pos + nlen_off)[0]
            if bytes(d[pos + name_off:pos + name_off + n]) == b"secret.mp4":
                struct.pack_into("<H", d, pos + off, struct.unpack_from("<H", d, pos + off)[0] | 1)
            pos += 4
    p.write_bytes(bytes(d))


run("encrypted", enc)


def trunc(p):
    with zipfile.ZipFile(p, "w") as zf:
        add(zf, "a.mp4", video("a", 100_000))
        add(zf, "b.mp4", video("b", 100_000))
    d = p.read_bytes()
    p.write_bytes(d[:len(d) // 2])


run("truncated", trunc)


def flip(p):
    with zipfile.ZipFile(p, "w") as zf:
        for t in "abc":
            add(zf, f"{t}.mp4", video(t, 100_000))
    d = bytearray(p.read_bytes())
    d[len(d) // 2] ^= 0xFF
    p.write_bytes(bytes(d))


run("bitflip", flip)


def mism(p):
    with zipfile.ZipFile(p, "w") as zf:
        add(zf, "aaaaaaaa.mp4", video("a"))
    d = bytearray(p.read_bytes())
    i = d.find(b"aaaaaaaa.mp4")
    d[i:i + 8] = b"..\\..\\x."[:8]
    p.write_bytes(bytes(d))


run("name_mismatch_local", mism)

N = int(sys.argv[2]) if len(sys.argv) > 2 else 100_000
case = "many_entries"
st, root = fresh(case)
z = base / case / "in.zip"
with zipfile.ZipFile(z, "w") as zf:
    for i in range(N):
        zf.writestr(zipfile.ZipInfo(f"d/{i}.txt"), b"")
tracemalloc.start()
t0 = time.time()
rep = expand_zip(st, z)
dt = time.time() - t0
cur, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
results[case] = dict(entries=N, zip_bytes=z.stat().st_size, status=rep.status.value,
                     rows=[(m.member, m.outcome.value, m.reason) for m in rep.members],
                     secs=round(dt, 2), peak_mb=round(peak / 1e6, 1))
print(json.dumps(results, indent=1, default=str))
