"""Seat A r1 F1 fuzz: flip bytes in the middle member of a 3-member zip, per compression method."""
import sys, os, shutil, tempfile, zipfile, hashlib, json, struct
from pathlib import Path
tree = Path(sys.argv[1]); work = Path(sys.argv[2])
sys.path[:0] = [str(tree / "src"), str(tree / "tests")]
import autotester, zip_fixtures as zf
from zip_fixtures import add_member, make_store
from autotester.sources.zip_intake import expand_zip
assert str(tree) in autotester.__file__, autotester.__file__

def noise(tag, size=6000):
    out, n = b"", 0
    while len(out) < size:
        out += hashlib.sha256(f"{tag}{n}".encode()).digest(); n += 1
    return out[:size]

def build(path, method):
    with zipfile.ZipFile(path, "w") as z:
        for t in "abc":
            add_member(z, f"{t}.mp4", noise(t), compress=method)

def central_span(raw, name):
    i = raw.find(b"PK\x01\x02")
    while i != -1:
        n, m, k = struct.unpack("<HHH", raw[i+28:i+34])
        if raw[i+46:i+46+n] == name.encode(): return i, i+46+n+m+k
        i = raw.find(b"PK\x01\x02", i+4)
    raise SystemExit("no central record")

results = []
for mname, method in (("LZMA", zipfile.ZIP_LZMA), ("BZIP2", zipfile.ZIP_BZIP2), ("DEFLATE", zipfile.ZIP_DEFLATED), ("STORED", zipfile.ZIP_STORED)):
    base = work / f"base-{mname}.zip"; build(base, method)
    with zipfile.ZipFile(base) as z:
        info = z.getinfo("b.mp4")
        lh = info.header_offset; dstart = lh + 30 + len(info.orig_filename.encode()) + len(info.extra)
        dend = dstart + info.compress_size
    raw0 = base.read_bytes()
    cs, ce = central_span(raw0, "b.mp4")
    positions = {}
    step = 1000000
    for p in list(range(dstart, dstart+48))+list(range(dend-48, dend)): positions[p] = "data"
    pass
    pass
    for p, region in sorted(positions.items()):
        d = Path(tempfile.mkdtemp(dir=work)); arch = d / "in.zip"
        raw = bytearray(raw0); raw[p] ^= 0xFF; arch.write_bytes(bytes(raw))
        store = make_store(d)
        try:
            rep = expand_zip(store, arch, max_file_bytes=1 << 20)
            rows = sorted(s.label for s in store.list_sources())
            fails = [m.member for m in rep.members if m.outcome.value == "failed"]
            rec = dict(method=mname, pos=p, region=region, status=rep.status.value, exit=rep.exit_code, failed=fails, rows=rows,
                       leftovers=len(list((d/".work"/"intake").glob("*/*"))) if (d/".work"/"intake").exists() else 0)
        except BaseException as e:
            rec = dict(method=mname, pos=p, region=region, CRASH=f"{type(e).__name__}: {e}")
        results.append(rec)
        shutil.rmtree(d, ignore_errors=True)
json.dump(results, open(work / "fuzz_f1_edges.json", "w"), indent=0)
crash = [r for r in results if "CRASH" in r]
print("total", len(results), "crash", len(crash))
from collections import Counter
print(Counter((r["method"], r["region"], r.get("status", "CRASH")) for r in results))
for r in crash[:10]: print(r)
# data-region: earlier member registered + partial?
bad = [r for r in results if r["region"] == "data" and "CRASH" not in r and r["status"] == "partial" and "a.mp4" not in r["rows"]]
print("data-region partial but a.mp4 not registered:", len(bad))
print("leftover staging:", sum(r.get("leftovers", 0) for r in results))
