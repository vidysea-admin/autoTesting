import hashlib
import itertools
import struct
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from zip_fixtures import make_store
from zipcraft import (CDH_F, EOCD_F, LFH_F, MAXV, build, entry, healthy_entries, raw_deflate,
                      video)

from autotester.core.paths import ENV_ROOT
from autotester.schema.project import Project
from autotester.sources.zip_intake import expand_zip
from autotester.store.project_store import ProjectStore

CASES: list[tuple[str, bytes]] = []


def add(cid, data):
    CASES.append((cid, data))


H = healthy_entries


def hv(**over):
    return H()


# ---- class 1: flag bits, UTF-8 names (central / local / both) ------------------------------
BADU = [b"\xff.mp4", b"\xed\xa0\x80.mp4", b"\xc0\xaf.mp4", b"\xf8\x88\x80\x80\x80.mp4", b"a\xe2\x82.mp4"]
for i, bad in enumerate(BADU):
    for where in ("cd", "local", "both"):
        es = [entry(bad if where != "local" else b"zz.mp4", video("x")), entry("ok.mp4", video("y"))]
        if where == "local":
            es[0]["name"] = bad
            es[0]["lfh"] = {"nlen": len(bad)}
        data = None
        flags = 0x800
        for e in es:
            e["flag"] = flags
        if where == "cd":
            # local header name valid ascii, central invalid
            es[0]["name"] = b"zz.mp4"
            data = build(es, cd_name=None)
            # patch: rebuild with differing names via direct bytes edit
            data = data.replace(b"PK\x01\x02", b"PK\x01\x02")
            # swap central name only
            ci = data.rfind(b"PK\x01\x02", 0, data.rfind(b"PK\x05\x06"))
            first_cd = data.find(b"PK\x01\x02")
            nm = data.find(b"zz.mp4", first_cd)
            nb = bytearray(data)
            pad = bad[:6].ljust(6, b"a")
            nb[nm:nm + 6] = pad
            data = bytes(nb)
        else:
            data = build(es)
        add(f"utf8-{where}-{i}", data)

for flag in (0x1, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800, 0x1000, 0x2000,
             0x4000, 0x8000, 0xFFFF, 0x0801, 0x0809, 0x0041, 0x2001):
    for which in ("cdlocal", "cdonly", "localonly"):
        es = H()
        for e in es:
            if which == "cdlocal":
                e["flag"] = flag
            elif which == "cdonly":
                e["cdh"] = {"flag": flag}
            else:
                e["lfh"] = {"flag": flag}
        add(f"flag-{flag:04x}-{which}", build(es))

# ---- class 2: extra fields -------------------------------------------------------------------
def ex(i, d):
    return struct.pack("<HH", i, len(d)) + d


extras = {
    "z64-short": ex(1, b"\x01\x00"),
    "z64-empty": ex(1, b""),
    "z64-full": ex(1, struct.pack("<QQQ", 1 << 62, 1 << 62, 1 << 60)),
    "len-too-long": struct.pack("<HH", 0x7075, 0xFFFF) + b"abc",
    "trunc-hdr": b"\x01",
    "trunc-hdr3": b"\x01\x00\x00",
    "z64-id-only": struct.pack("<H", 1),
    "unicode-path": ex(0x7075, b"\x01\x00\x00\x00\x00\xff\xfe"),
    "ntfs": ex(0x000A, b"\x00" * 3),
    "many": b"".join(ex(0x9999, b"x") for _ in range(2000)),
    "max-extra": ex(0x9999, b"x" * 65000),
}
for k, x in extras.items():
    for where in ("cd", "local", "both"):
        for sent in (False, True):
            es = H()
            for e in es:
                if where in ("cd", "both"):
                    e["cextra"] = x
                if where in ("local", "both"):
                    e["lextra"] = x
                if sent:
                    e["cdh"] = {"usize": 0xFFFFFFFF, "csize": 0xFFFFFFFF, "offset": 0xFFFFFFFF}
                    e["lfh"] = {"usize": 0xFFFFFFFF, "csize": 0xFFFFFFFF}
            add(f"extra-{k}-{where}-{'sent' if sent else 'plain'}", build(es))

# ---- class 3: EOCD ---------------------------------------------------------------------------
EOCD_VALS = [0, 1, 2, 5, 0x7FFF, 0xFFFE, 0xFFFF]
for field, f in EOCD_F[1:]:
    vals = EOCD_VALS if f == "H" else [0, 1, 20, 0x7FFFFFFF, 0xFFFFFFFE, 0xFFFFFFFF]
    for v in vals:
        add(f"eocd-{field}-{v:x}", build(H(), eocd={field: v}))
for clen_lie in (1, 100, 0xFFFF):
    add(f"eocd-comment-lie-{clen_lie}", build(H(), comment=b"hi", eocd={"clen": clen_lie}))
add("eocd-comment-containing-eocd", build(H(), comment=b"PK\x05\x06" + b"\x00" * 18))
add("eocd-comment-fake-sig-big", build(H(), comment=(b"PK\x05\x06" + b"\xff" * 18) * 100))
add("eocd-no-cd", build(H(), skip_cd=True))
add("prefix-garbage", build(H(), prefix=b"GARBAGE" * 50))
add("tail-garbage", build(H(), tail=b"\x00" * 5000))
add("zip64-locator-bad", build(H(), tail=b"") .replace(b"PK\x05\x06", b"PK\x06\x07" + b"\xff" * 16 + b"PK\x05\x06", 1))
add("zip64-eocd-fake", build(H()).replace(b"PK\x05\x06", b"PK\x06\x06" + b"\xff" * 52
                                                + b"PK\x06\x07" + b"\x00" * 16 + b"PK\x05\x06", 1))
add("zip64-eocd-sentinel-fields", build(H(), eocd={"n": 0xFFFF, "nd": 0xFFFF, "cdsize": 0xFFFFFFFF, "cdoff": 0xFFFFFFFF}))

# ---- class 4/5: sweep every CDH and LFH field with boundary values ----------------------------
def vals_for(f):
    return [0, 1, 2, 0x7F, 0x80, 0x7FFF, 0x8000, 0xFFFE, 0xFFFF] if f == "H" else \
           [0, 1, 20, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFE, 0xFFFFFFFF, 0xDEADBEEF]


for fields, tag in ((CDH_F, "cdh"), (LFH_F, "lfh")):
    for field, f in fields[1:] if tag == "cdh" else fields:
        if field == "sig" and tag == "lfh":
            pass
        for v in vals_for(f):
            for target in (0, 1, 2, 3):
                es = H()
                es[target][tag] = {field: v}
                add(f"{tag}-{field}-{v:x}-m{target}", build(es))
for v in (0xDEADBEEF, 0x0, 0x01020304, 0x04034B51):  # corrupt signatures
    es = H(); es[1]["lfh"] = {"sig": v}; add(f"lfh-sig-{v:x}", build(es))
    es = H(); es[1]["cdh"] = {"sig": v}; add(f"cdh-sig-{v:x}", build(es))

# versions
for vn in (0, 10, 20, 45, 51, 62, 63, 64, 99, 255, 256, 0x0A00, 0xFFFF):
    es = H()
    for e in es:
        e["vneed"] = vn
    add(f"vneed-{vn}", build(es))
    es = H()
    for e in es:
        e["vmade"] = vn
    add(f"vmade-{vn}", build(es))

# ---- class 6: compression methods with garbage ------------------------------------------------
GARBAGE = [b"", b"\x00", b"\xff" * 64, bytes(range(256)) * 4, b"\x00" * 5000, b"\x5d\x00\x00\x00\x01"]
for m in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 18, 19, 20, 93, 94, 95, 96, 97, 98, 99, 0xFFFF):
    for gi, g in enumerate(GARBAGE):
        es = [entry("bad.mp4", video("z"), m, comp=g, flag=0), entry("ok.mp4", video("k"))]
        es[0]["csize"] = len(g)
        add(f"method-{m}-garb{gi}", build(es))
# lzma headers: props sizes, lc/lp/pb, dict sizes
for dict_sz in (0, 1, 4096, 1 << 26, 1 << 30, 0x7FFFFFFF, 0xFFFFFFFF, 0xFFFFFFFE):
    for pb in (0x5D, 0xE1, 0xFF, 0x00, 0xE0):
        for psz in (5, 0, 4, 6, 0xFFFF):
            body = struct.pack("<BBH", 9, 4, psz) + struct.pack("<BI", pb, dict_sz) + b"\x00" * 40
            es = [entry("l.mp4", video("z"), 14, comp=body), entry("ok.mp4", video("k"))]
            add(f"lzma-d{dict_sz:x}-pb{pb:x}-ps{psz:x}", build(es))
# deflate bomb inside (lying sizes)
bomb = raw_deflate(b"\x00" * 50_000_000)
es = [entry("bomb.mp4", b"x", 8, comp=bomb), entry("ok.mp4", video("k"))]
es[0]["usize"] = 5; es[0]["crc"] = 0
add("deflate-bomb-understated", build(es))
es = [entry("bomb.mp4", b"x", 8, comp=bomb), entry("ok.mp4", video("k"))]
es[0]["usize"] = 50_000_000; es[0]["crc"] = zlib.crc32(b"\x00" * 50_000_000)
add("deflate-bomb-honest", build(es))
# stored with sizes disagreeing
for cs, us in ((10, 4096), (4096, 10), (0, 4096), (4096, 0), (0xFFFFFFFF, 4096), (4096, 0xFFFFFFFF),
               (1 << 31, 1 << 31)):
    es = [entry("a.mp4", video("a")), entry("ok.mp4", video("k"))]
    es[0]["cdh"] = {"csize": cs, "usize": us}
    es[0]["lfh"] = {"csize": cs, "usize": us}
    add(f"stored-sizes-{cs:x}-{us:x}", build(es))
    es = [entry("a.mp4", video("a")), entry("ok.mp4", video("k"))]
    es[0]["cdh"] = {"csize": cs, "usize": us}
    add(f"stored-sizes-cdonly-{cs:x}-{us:x}", build(es))
# data descriptor flag with no descriptor
es = H()
for e in es:
    e["flag"] = 0x8
    e["lfh"] = {"crc": 0, "csize": 0, "usize": 0}
add("datadesc-nodescriptor", build(es))
# zero length
add("zero-length-video", build([entry("e.mp4", b""), entry("ok.mp4", video("k"))]))
add("zero-length-deflate", build([entry("e.mp4", b"", 8), entry("ok.mp4", video("k"))]))
add("zero-entries", build([]))
add("only-eocd", b"PK\x05\x06" + b"\x00" * 18)
add("empty-file", b"")
add("one-byte", b"P")
add("sig-only", b"PK\x03\x04")

# ---- class 7: names ---------------------------------------------------------------------------
NAMES = [b"", b"/", b"//", b"a.mp4/", b"./", b"..", b"../x.mp4", b"..\\x.mp4", b"/abs.mp4", b"\\abs.mp4",
         b"C:\\x.mp4", b"C:x.mp4", b"\\\\h\\s\\x.mp4", b"a.mp4:evil", b"con.mp4", b"NUL", b"aux.x.mp4",
         b"a\x00.mp4", b"a\x00../../x.mp4", b"\x00", b"\x00.mp4", b"x\x07.mp4", b"x\x7f.mp4",
         b"a" * 65535, b"a" * 300 + b".mp4", b"d/" * 30000 + b"x.mp4", "é.mp4".encode(), "\u202e4pm.mp4".encode(),
         "\ud7ff.mp4".encode(), "\U0010ffff.mp4".encode(), b" .mp4", b". .mp4", b"a. ", b"x.mp4.", b"x.mp4 ",
         b"\xff\xfe.mp4", b"\xed\xa0\x80.mp4", b".env", b"a.zip", b"a.mp4.zip", b"x.MP4", b"x.mP4"]
for i, nm in enumerate(NAMES):
    for fl in (0, 0x800):
        for method in (0, 8):
            es = [entry(nm, video("n"), method, flag=fl), entry("ok.mp4", video("k"))]
            add(f"name-{i}-fl{fl:x}-m{method}", build(es))
# duplicate names, case collisions
add("dup-names", build([entry("a.mp4", video("1")), entry("a.mp4", video("2")), entry("A.MP4", video("1"))]))
add("dup-nested", build([entry("d/a.mp4", video("1")), entry("d\\a.mp4", video("2"))]))
# mode / attr
for mode in (0o120777, 0o020666, 0o010666, 0o140666, 0o060666, 0o040755, 0o100000):
    for vm in (0x0314, 0x0014, 0x0A14, 0x0000):
        es = [entry("l.mp4", video("l")), entry("ok.mp4", video("k"))]
        es[0]["eattr"] = mode << 16
        es[0]["vmade"] = vm
        add(f"mode-{mode:o}-{vm:x}", build(es))
add("dos-dir-attr-with-data", build([entry("x.mp4", video("l"), eattr=0x10), entry("ok.mp4", video("k"))]))
add("eattr-ffff", build([entry("x.mp4", video("l"), eattr=0xFFFFFFFF), entry("ok.mp4", video("k"))]))

# ---- class 8: nested zips ----------------------------------------------------------------------
inner = build(H())
add("nested-by-name", build([entry("inner.zip", inner), entry("ok.mp4", video("k"))]))
add("nested-by-content-mp4", build([entry("inner.mp4", inner), entry("ok.mp4", video("k"))]))
add("nested-by-content-deflate", build([entry("inner.mp4", inner, 8), entry("ok.mp4", video("k"))]))
add("nested-gz", build([entry("g.mp4", b"\x1f\x8b" + b"\x00" * 100), entry("ok.mp4", video("k"))]))
add("nested-7z", build([entry("g.mp4", b"7z\xbc\xaf\x27\x1c" + b"\x00" * 100)]))
add("nested-short-head", build([entry("g.mp4", b"PK"), entry("ok.mp4", video("k"))]))
add("self-embed", build([entry("self.mp4", inner * 3)]))

# ---- class 9: offsets: overlap, into CD, out of file --------------------------------------------
for off in (0, 1, 30, 100, 0x7FFFFFFF, 0xFFFFFFFE, 0xFFFFFFFF):
    for target in (0, 2):
        es = H()
        es[target]["offset"] = off
        add(f"offset-{off:x}-m{target}", build(es))
# overlapping files: all members point at the same local header (zip-bomb style)
es = [entry(f"v{i}.mp4", video("same", 100000), 8) for i in range(3)]
for e in es:
    e["offset"] = 0
add("overlap-all-same-offset", build(es))
# offset into central directory
es = H()
data = build(es)
cdstart = data.find(b"PK\x01\x02")
es = H()
es[1]["offset"] = cdstart
add("offset-into-cd", build(es, prefix=b""))

# ---- class 10: encrypted ------------------------------------------------------------------------
enc = [entry("e.mp4", video("e"), 0, flag=0x1, comp=b"\x00" * 12 + video("e")), entry("ok.mp4", video("k"))]
add("encrypted-flag", build(enc))
enc = [entry("e.mp4", video("e"), 99, flag=0x1, comp=b"\x00" * 50), entry("ok.mp4", video("k"))]
add("encrypted-aes", build(enc))
enc = [entry("e.mp4", video("e"), 0, flag=0x1, comp=b"\x00" * 12 + video("e")), entry("ok.mp4", video("k"))]
enc[0]["cdh"] = {"flag": 0}
add("encrypted-local-only", build(enc))
enc = [entry("e.mp4", video("e"), 0, flag=0x0, comp=video("e")), entry("ok.mp4", video("k"))]
enc[0]["cdh"] = {"flag": 1}
add("encrypted-cd-only", build(enc))
enc = [entry("e.mp4", video("e"), 0, flag=0x40 | 1, comp=b"\x00" * 100)]
add("encrypted-strong", build(enc))

# ---- class 11: ratio / counts / sizes -------------------------------------------------------------
add("ratio", build([entry("z.mp4", b"\x00" * 3_000_000, 8), entry("ok.mp4", video("k"))]))
add("many-entries", build([entry(f"f{i}.txt", b"x") for i in range(1200)]))
add("many-videos", build([entry(f"f{i}.mp4", video(str(i))) for i in range(30)]))
add("many-dirs", build([entry(f"d{i}/", b"") for i in range(900)]))
add("huge-declared-total", build([entry(f"v{i}.mp4", video(str(i))) for i in range(3)]))

for i, (cid, _) in enumerate(CASES):
    pass

IDS = [c[0] for c in CASES]


def _mk(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    st = make_store(tmp_path)
    return st


def _snapshot(tmp_path):
    return {p for p in tmp_path.rglob("*") if p.is_file()}


def _check(tmp_path, store: ProjectStore, before: set, archive: Path):
    after = _snapshot(tmp_path)
    new = after - before
    srcs = store.paths.sources_dir
    idx = store.paths.sources_index
    stray = {p for p in new if srcs not in p.parents and p != idx and p != archive}
    assert not stray, f"stray files: {sorted(map(str, stray))[:5]}"
    for row in store.list_sources():
        p = Path(row.path)
        assert p.is_file(), f"row without file {row.path}"
        assert srcs.resolve() in p.resolve().parents
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row.sha256
    assert not [p for p in new if ".work" in p.parts and "intake" in p.parts]


@pytest.mark.parametrize("data", [c[1] for c in CASES], ids=IDS)
def test_expand(tmp_path, monkeypatch, data):
    store = _mk(tmp_path, monkeypatch)
    arch = tmp_path / "h.zip"
    arch.write_bytes(data)
    before = _snapshot(tmp_path)
    report = expand_zip(store, arch, max_file_bytes=1024 * 1024 * 4)
    assert report.status is not None
    _check(tmp_path, store, before, arch)


@pytest.mark.parametrize("data", [c[1] for c in CASES], ids=IDS)
def test_route(tmp_path, monkeypatch, data):
    from autotester.ui.app import app
    store = _mk(tmp_path, monkeypatch)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    client = TestClient(app, raise_server_exceptions=False)
    before = _snapshot(tmp_path)
    r = client.post("/projects/demo/sources/upload",
                    files={"recording": ("h.zip", data, "application/zip")}, data={"label": "x"})
    assert r.status_code < 500, (r.status_code, r.text[:200])
    assert "Traceback" not in r.text
    assert r.status_code not in (403, 404, 405, 422), r.status_code
    _check(tmp_path, store, before, tmp_path / "none")
