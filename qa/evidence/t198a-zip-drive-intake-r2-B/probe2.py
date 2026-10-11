import struct, tempfile, time
from pathlib import Path
from zipcraft import build, entry, healthy_entries, video
from zip_fixtures import make_store
from autotester.sources.zip_intake import expand_zip
H = healthy_entries()
lz = H[3]["comp"]
print("lzma props", lz[:9].hex())
def run(label, data):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); st = make_store(d); a = d/"h.zip"; a.write_bytes(data)
        t=time.time()
        try:
            r = expand_zip(st, a, max_file_bytes=4<<20)
            print(label, "->", r.status.value, [(m.outcome.value, m.reason) for m in r.members][:3], round(time.time()-t,1), "s")
        except BaseException as e:
            print(label, "-> RAISED", type(e).__name__, str(e)[:80])
for dsz in (1<<24, 1<<28, 1<<30, 1<<31, 0xFFFFFFF0, 0xFFFFFFFF):
    comp = bytearray(lz); comp[5:9] = struct.pack("<I", dsz)
    es = [entry("l.mp4", video("l", 3000), 14, comp=bytes(comp)), entry("ok.mp4", video("k"))]
    run(f"lzma valid stream, header dict {dsz:#x}", build(es))
# local header name invalid UTF-8 but CD valid, flag set (zf.open decode path)
es = [entry(b"zz.mp4", video("a"), flag=0x800), entry("ok.mp4", video("k"))]
data = bytearray(build(es))
i = data.find(b"zz.mp4")  # first = local header
data[i:i+6] = b"\xffz.mp4"
run("local-name invalid utf8, central valid, flag 0x800", bytes(data))
# same but deflate
es = [entry(b"zz.mp4", video("a"), 8, flag=0x800), entry("ok.mp4", video("k"))]
data = bytearray(build(es)); i = data.find(b"zz.mp4"); data[i:i+6] = b"\xed\xa0\x80.mp4"
run("local-name surrogate bytes, central valid", bytes(data))
