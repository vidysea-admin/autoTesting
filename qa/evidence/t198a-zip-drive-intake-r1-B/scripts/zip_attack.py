"""Seat B r1: hostile-zip battery against expand_zip.

usage: python zip_attack.py <SRC dir containing autotester/> <WORK dir (empty)> <out.json>
"""
import bz2
import hashlib
import json
import struct
import sys
import traceback
import zipfile
import zlib
from pathlib import Path

SRC, WORK, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(SRC))
import autotester  # noqa: E402

assert str(SRC.resolve()) in str(Path(autotester.__file__).resolve()), autotester.__file__
from autotester.sources.zip_intake import expand_zip  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402


def noise(tag, size=6000):
    out, n = b"", 0
    while len(out) < size:
        out += hashlib.sha256(f"{tag}{n}".encode()).digest()
        n += 1
    return out[:size]


METHODS = {"stored": zipfile.ZIP_STORED, "deflate": zipfile.ZIP_DEFLATED,
           "bzip2": zipfile.ZIP_BZIP2, "lzma": zipfile.ZIP_LZMA}


def healthy(path, method, names=("a.mp4", "b.mp4", "c.mp4"), **kw):
    with zipfile.ZipFile(path, "w", compression=method) as zf:
        for n in names:
            info = zipfile.ZipInfo("x")
            info.filename = n
            info.compress_type = method
            for k, v in kw.items():
                setattr(info, k, v)
            zf.writestr(info, noise(n))
    return path


def read_raw(path):
    members = []
    raw = Path(path).read_bytes()
    with zipfile.ZipFile(path) as zf:
        for i in zf.infolist():
            nl, el = struct.unpack("<HH", raw[i.header_offset + 26:i.header_offset + 30])
            start = i.header_offset + 30 + nl + el
            members.append(dict(name=i.orig_filename.encode(), method=i.compress_type,
                                flags=i.flag_bits, ver=i.extract_version, crc=i.CRC,
                                csize=i.compress_size, usize=i.file_size,
                                data=raw[start:start + i.compress_size],
                                lextra=b"", cextra=b""))
    return members


def write_raw(path, members, *, cd_mutate=None, eocd_mutate=None, trunc_cd=0):
    out = bytearray()
    offs = []
    for m in members:
        offs.append(len(out))
        out += struct.pack("<4sHHHHHIIIHH", b"PK\3\4", m["ver"], m["flags"], m["method"], 0, 0x21,
                           m["crc"], m.get("lcsize", m["csize"]), m.get("lusize", m["usize"]),
                           len(m["name"]), len(m["lextra"]))
        out += m["name"] + m["lextra"] + m["data"]
    cd_start = len(out)
    for m, off in zip(members, offs):
        out += struct.pack("<4sHHHHHHIIIHHHHHII", b"PK\1\2", 63, m.get("cver", m["ver"]), m["flags"],
                           m["method"], 0, 0x21, m["crc"], m.get("ccsize", m["csize"]),
                           m.get("cusize", m["usize"]), len(m["name"]), len(m["cextra"]), 0, 0, 0, 0,
                           m.get("coff", off))
        out += m["name"] + m["cextra"]
    cd_size = len(out) - cd_start
    n = len(members)
    eocd = struct.pack("<4sHHHHIIH", b"PK\5\6", 0, 0, n, n, cd_size, cd_start, 0)
    if eocd_mutate:
        eocd = eocd_mutate(eocd, cd_start, cd_size, n)
    if cd_mutate:
        out = cd_mutate(out, cd_start)
    out += eocd
    if trunc_cd:
        out = out[:-trunc_cd - len(eocd)] + eocd if False else out
    Path(path).write_bytes(bytes(out))
    return path


CASES = {}  # name -> builder(path) ; each builds in WORK/<name>.zip


def case(name):
    def deco(fn):
        CASES[name] = fn
        return fn
    return deco


POS = {"first": 0, "middle": 1, "last": 2}

# --- healthy archives (differential old vs new)
for mname, mid in METHODS.items():
    CASES[f"healthy-{mname}"] = (lambda p, mid=mid: healthy(p, mid))
CASES["healthy-zip64-forced"] = None  # filled below


def _healthy_zip64(p):
    with zipfile.ZipFile(p, "w") as zf:
        for n in ("a.mp4", "b.mp4", "c.mp4"):
            info = zipfile.ZipInfo("x")
            info.filename = n
            with zf.open(info, "w", force_zip64=True) as f:
                f.write(noise(n))
    return p


CASES["healthy-zip64-forced"] = _healthy_zip64
CASES["healthy-ver63"] = lambda p: healthy(p, zipfile.ZIP_STORED, extract_version=63)


# --- damaged streams
def _damage(p, method, pos, frac):
    healthy(p, METHODS[method])
    ms = read_raw(p)
    m = ms[POS[pos]]
    d = bytearray(m["data"])
    idx = min(len(d) - 1, int(len(d) * frac))
    d[idx] ^= 0xFF
    m["data"] = bytes(d)
    return write_raw(p, ms)


def _trunc(p, method, pos, keep, consistent):
    healthy(p, METHODS[method])
    ms = read_raw(p)
    m = ms[POS[pos]]
    m["data"] = m["data"][:int(len(m["data"]) * keep)]
    if consistent:
        m["csize"] = len(m["data"])
    return write_raw(p, ms)


def _crc(p, method, pos):
    healthy(p, METHODS[method])
    ms = read_raw(p)
    ms[POS[pos]]["crc"] ^= 0x12345678
    return write_raw(p, ms)


for method in METHODS:
    for pos in POS:
        for frac in (0.0, 0.2, 0.5, 0.8, 0.99):
            CASES[f"flip-{method}-{pos}-{frac}"] = (lambda p, a=method, b=pos, c=frac: _damage(p, a, b, c))
        for keep in (0.0, 0.4, 0.9):
            CASES[f"trunc-consistent-{method}-{pos}-{keep}"] = (lambda p, a=method, b=pos, c=keep: _trunc(p, a, b, c, True))
            CASES[f"trunc-claimfull-{method}-{pos}-{keep}"] = (lambda p, a=method, b=pos, c=keep: _trunc(p, a, b, c, False))
        CASES[f"wrongcrc-{method}-{pos}"] = (lambda p, a=method, b=pos: _crc(p, a, b))


# --- unknown methods / flags
def _meth(p, mid, pos, flags=0):
    healthy(p, zipfile.ZIP_STORED)
    ms = read_raw(p)
    ms[POS[pos]]["method"] = mid
    ms[POS[pos]]["flags"] = flags
    return write_raw(p, ms)


for mid in (1, 6, 9, 10, 18, 19, 20, 93, 94, 95, 96, 97, 98, 99, 255, 65535):
    for pos in ("first", "middle", "last"):
        CASES[f"method-{mid}-{pos}"] = (lambda p, a=mid, b=pos: _meth(p, a, b))
for flags, label in ((0x1, "encrypted"), (0x20, "patched"), (0x40, "strong"), (0x2001, "enc+masked"),
                     (0x41, "enc+strong"), (0x2000, "masked")):
    for pos in ("first", "middle", "last"):
        CASES[f"flags-{label}-{pos}"] = (lambda p, a=flags, b=pos: _meth(p, 0, b, a))


def _central_only_enc(p, pos, cflags):
    healthy(p, zipfile.ZIP_STORED)
    ms = read_raw(p)
    ms[POS[pos]]["flags"] = 0  # local says plain
    raw = write_raw(p, ms)
    b = bytearray(Path(p).read_bytes())
    # patch central flags of member idx
    off = b.find(b"PK\1\2")
    for _ in range(POS[pos]):
        off = b.find(b"PK\1\2", off + 4)
    b[off + 8] |= 1
    Path(p).write_bytes(bytes(b))
    return p


for pos in POS:
    CASES[f"enc-central-only-{pos}"] = (lambda p, b=pos: _central_only_enc(p, b, 1))


# --- extract_version
def _ver(p, v, pos, which="both"):
    healthy(p, zipfile.ZIP_STORED)
    ms = read_raw(p)
    m = ms[POS[pos]]
    if which in ("both", "local"):
        m["ver"] = v
    if which == "central":
        m["cver"] = v
    elif which == "both":
        m["cver"] = v
    elif which == "local":
        m["cver"] = 20
    return write_raw(p, ms)


for v in (20, 63, 64, 99, 255, 0xFFFF):
    for pos in POS:
        for which in ("both", "central", "local"):
            CASES[f"ver-{v}-{pos}-{which}"] = (lambda p, a=v, b=pos, c=which: _ver(p, a, b, c))
# lzma + high version
def _ver_lzma(p, v):
    healthy(p, zipfile.ZIP_LZMA)
    ms = read_raw(p)
    ms[1]["ver"] = v
    ms[1]["cver"] = v
    return write_raw(p, ms)


CASES["ver-99-lzma-middle"] = lambda p: _ver_lzma(p, 99)


# --- lzma header oddities
def _lzma_hdr(p, mode):
    healthy(p, zipfile.ZIP_LZMA)
    ms = read_raw(p)
    m = ms[1]
    d = bytearray(m["data"])
    if mode == "badprops":
        d[4] = 0xFF
    elif mode == "psize-huge":
        d[2:4] = struct.pack("<H", 65535)
    elif mode == "psize-zero":
        d[2:4] = b"\0\0"
    elif mode == "short3":
        d = d[:3]
    elif mode == "short5":
        d = d[:5]
    elif mode == "garbage":
        d = bytearray(noise("g", len(d)))
    elif mode == "empty":
        d = bytearray()
    m["data"] = bytes(d)
    m["csize"] = len(d)
    return write_raw(p, ms)


for mode in ("badprops", "psize-huge", "psize-zero", "short3", "short5", "garbage", "empty"):
    CASES[f"lzma-{mode}"] = (lambda p, a=mode: _lzma_hdr(p, a))


def _garbage(p, method, kind):
    healthy(p, METHODS[method])
    ms = read_raw(p)
    m = ms[1]
    m["data"] = {"noise": noise("junk", 300), "empty": b"", "zeros": b"\0" * 300}[kind]
    m["csize"] = len(m["data"])
    return write_raw(p, ms)


for method in ("deflate", "bzip2", "lzma"):
    for kind in ("noise", "empty", "zeros"):
        CASES[f"garbage-{method}-{kind}"] = (lambda p, a=method, b=kind: _garbage(p, a, b))


# --- zip64
def _z64(p, mode, pos):
    healthy(p, zipfile.ZIP_STORED)
    ms = read_raw(p)
    m = ms[POS[pos]]
    real = (m["usize"], m["csize"])
    good = struct.pack("<HHQQ", 1, 16, *real)
    m["ccsize"] = m["cusize"] = m["lcsize"] = m["lusize"] = 0xFFFFFFFF
    if mode == "ok":
        m["cextra"] = good
        m["lextra"] = good
        m["ver"] = 45
    elif mode == "extra-short":
        m["cextra"] = struct.pack("<HH", 1, 4) + b"abcd"
        m["lextra"] = struct.pack("<HH", 1, 4) + b"abcd"
    elif mode == "extra-empty":
        m["cextra"] = struct.pack("<HH", 1, 0)
        m["lextra"] = struct.pack("<HH", 1, 0)
    elif mode == "extra-huge":
        m["cextra"] = struct.pack("<HHQQ", 1, 16, 2**62, 5)
        m["lextra"] = m["cextra"]
    elif mode == "extra-wrongsize":
        m["cextra"] = struct.pack("<HHQQ", 1, 16, real[0] + 77, real[1])
        m["lextra"] = m["cextra"]
    elif mode == "extra-truncfield":
        m["cextra"] = struct.pack("<HH", 1, 40) + b"x" * 5
        m["lextra"] = m["cextra"]
    elif mode == "neg-offset":
        m["cextra"] = good
        m["lextra"] = good
        m["coff"] = 0xFFFFFFFF
    return write_raw(p, ms)


for mode in ("ok", "extra-short", "extra-empty", "extra-huge", "extra-wrongsize", "extra-truncfield", "neg-offset"):
    for pos in POS:
        CASES[f"zip64-{mode}-{pos}"] = (lambda p, a=mode, b=pos: _z64(p, a, b))


# --- central directory damage
def _cd(p, mode):
    healthy(p, zipfile.ZIP_STORED)
    ms = read_raw(p)
    if mode == "sig-middle":
        def mut(out, cd_start):
            o = out.find(b"PK\1\2", cd_start + 4)
            out[o:o + 4] = b"XXXX"
            return out
        return write_raw(p, ms, cd_mutate=mut)
    if mode == "count-high":
        return write_raw(p, ms, eocd_mutate=lambda e, s, z, n: e[:8] + struct.pack("<HH", n + 5, n + 5) + e[12:])
    if mode == "count-low":
        return write_raw(p, ms, eocd_mutate=lambda e, s, z, n: e[:8] + struct.pack("<HH", 1, 1) + e[12:])
    if mode == "cd-offset-wrong":
        return write_raw(p, ms, eocd_mutate=lambda e, s, z, n: e[:16] + struct.pack("<I", s + 40) + e[20:])
    if mode == "cd-size-wrong":
        return write_raw(p, ms, eocd_mutate=lambda e, s, z, n: e[:12] + struct.pack("<I", z + 50) + e[16:])
    if mode == "name-len-overflow":
        def mut(out, cd_start):
            o = out.find(b"PK\1\2", cd_start + 4)
            out[o + 28:o + 30] = struct.pack("<H", 60000)
            return out
        return write_raw(p, ms, cd_mutate=mut)
    if mode == "extra-len-overflow":
        def mut(out, cd_start):
            o = out.find(b"PK\1\2", cd_start + 4)
            out[o + 30:o + 32] = struct.pack("<H", 60000)
            return out
        return write_raw(p, ms, cd_mutate=mut)
    if mode == "comment-len-lies":
        return write_raw(p, ms, eocd_mutate=lambda e, s, z, n: e[:20] + struct.pack("<H", 500))
    if mode == "no-eocd":
        write_raw(p, ms)
        b = Path(p).read_bytes()
        Path(p).write_bytes(b[:-22])
        return p
    if mode == "cd-truncated":
        write_raw(p, ms)
        b = Path(p).read_bytes()
        Path(p).write_bytes(b[:-22 - 40] + b[-22:])
        return p
    if mode == "local-offset-bad":
        ms[1]["coff"] = 3
        return write_raw(p, ms)
    if mode == "local-offset-past-eof":
        ms[1]["coff"] = 10_000_000
        return write_raw(p, ms)
    if mode == "local-name-differs":
        ms[1]["name"] = b"b.mp4"
        write_raw(p, ms)
        raw = bytearray(Path(p).read_bytes())
        # change local name of member 1 only
        o = raw.find(b"PK\3\4", 4)
        raw[o + 30:o + 31] = b"z"
        Path(p).write_bytes(bytes(raw))
        return p
    if mode == "local-header-trunc":
        write_raw(p, ms)
        raw = Path(p).read_bytes()
        Path(p).write_bytes(raw)
        return p
    if mode == "utf8-flag-bad-name":
        ms[1]["flags"] = 0x800
        ms[1]["name"] = b"b\xff\xfe.mp4"
        return write_raw(p, ms)
    if mode == "nul-name":
        ms[1]["name"] = b"b\x00.mp4"
        return write_raw(p, ms)
    if mode == "csize-exceeds-file":
        ms[1]["ccsize"] = 50_000_000
        return write_raw(p, ms)
    if mode == "usize-lie-small":
        ms[1]["cusize"] = 10
        return write_raw(p, ms)
    if mode == "usize-lie-big":
        ms[1]["cusize"] = 3_000_000_000
        return write_raw(p, ms)
    raise KeyError(mode)


for mode in ("sig-middle", "count-high", "count-low", "cd-offset-wrong", "cd-size-wrong", "name-len-overflow",
             "extra-len-overflow", "comment-len-lies", "no-eocd", "cd-truncated", "local-offset-bad",
             "local-offset-past-eof", "local-name-differs", "utf8-flag-bad-name", "nul-name",
             "csize-exceeds-file", "usize-lie-small", "usize-lie-big"):
    CASES[f"cd-{mode}"] = (lambda p, a=mode: _cd(p, a))
CASES["not-a-zip-text"] = lambda p: Path(p).write_bytes(b"hello") or p
CASES["empty-file"] = lambda p: Path(p).write_bytes(b"") or p


def run_case(name, builder):
    caset = WORK / "cases" / name
    caset.mkdir(parents=True, exist_ok=True)
    arc = caset / "in.zip"
    rec = {"case": name}
    try:
        builder(arc)
    except Exception as e:
        rec["build_error"] = repr(e)
        return rec
    root = caset / "root"
    root.mkdir()
    store = ProjectStore("demo", root=root)
    store.paths.dir.mkdir(parents=True, exist_ok=True)
    try:
        rep = expand_zip(store, arc, max_file_bytes=10 * 1024 * 1024)
        rec["raised"] = None
        rec["status"] = rep.status.value
        rec["exit"] = rep.exit_code
        rec["members"] = [(m.member, m.outcome.value, m.reason) for m in rep.members]
    except BaseException as e:
        rec["raised"] = f"{type(e).__name__}: {e}"[:200]
        rec["tb"] = traceback.format_exc().splitlines()[-4:]
    rows = []
    try:
        rows = [(s.label, s.sha256) for s in store.list_sources()]
    except Exception as e:
        rec["rows_error"] = repr(e)
    rec["rows"] = sorted(rows)
    left = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
            and "sources" not in p.parts and p.name != "sources.json" and p.suffix != ".lock"]
    rec["leftover"] = sorted(left)
    # files in sources dir that have no row
    src_files = [p for p in store.paths.sources_dir.rglob("*") if p.is_file()] if store.paths.sources_dir.exists() else []
    rec["src_files"] = len(src_files)
    return rec


if __name__ == "__main__":
    res = []
    for name, builder in CASES.items():
        res.append(run_case(name, builder))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    raised = [r for r in res if r.get("raised")]
    print("cases", len(res), "raised", len(raised), "build_errors", len([r for r in res if r.get("build_error")]))
    for r in raised:
        print("RAISED", r["case"], r["raised"])
