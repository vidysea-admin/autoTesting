import io, json, os, sys, zipfile
from harness import *
V1, V2 = MEDIA.read_bytes(), MEDIA2.read_bytes()
def zipbytes(members):
    def f(world):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            for n, d in members: z.writestr(n, d)
        return b.getvalue()
    return f
rows = []
def add(id, args, variant="emptyproject", files=None, **kw):
    rows.append({"id": id, "args": args, "variant": variant, "files": files or {}, **kw})
F = "{WORLD}/files/"
add("m01-register-ok", ["ingest", "register", "demo", F + "a.mp4", "--label", "lab", "--recorded-on", "2026-08-18"], files={"a.mp4": V2})
add("m02-register-missing", ["ingest", "register", "demo", F + "nope.mp4"])
add("m03-register-notrec", ["ingest", "register", "demo", F + "a.txt"], files={"a.txt": b"hello"})
add("m04-register-dir", ["ingest", "register", "demo", F + "d.mp4"], files={"d.mp4/x": b"x"})
add("m05-register-twice", ["ingest", "register", "demo", F + "a.mp4"], files={"a.mp4": V2}, then=[["ingest", "register", "demo", F + "a.mp4"]])
add("m06-register-noproject", ["ingest", "register", "demo", F + "a.mp4"], variant="noproject", files={"a.mp4": V2})
add("m07-list-noproject", ["ingest", "list", "demo"], variant="noproject")
add("m08-list-empty", ["ingest", "list", "demo"])
add("m09-list-with-source", ["ingest", "list", "demo"], variant="approved")
zok = zipbytes([("one.mp4", V1), ("two.mp4", V2)])
add("z01-zip-ok-text", ["ingest", "zip", "demo", F + "z.zip"], files={"z.zip": zok})
add("z02-zip-ok-json", ["ingest", "zip", "demo", F + "z.zip", "--json", "--uploaded-by", "dev@x.test"], files={"z.zip": zok})
zbad = zipbytes([("fine.mp4", V1), ("notes.txt", b"hi"), ("../evil.mp4", V2), ("dir/", b""), ("dup.mp4", V1)])
add("z03-zip-mixed-text", ["ingest", "zip", "demo", F + "z.zip"], files={"z.zip": zbad})
add("z03b-zip-mixed-json", ["ingest", "zip", "demo", F + "z.zip", "--json"], files={"z.zip": zbad})
add("z04-zip-missing", ["ingest", "zip", "demo", F + "none.zip"])
add("z05-zip-noproject", ["ingest", "zip", "demo", F + "z.zip"], variant="noproject", files={"z.zip": zok})
add("z06-zip-notazip", ["ingest", "zip", "demo", F + "z.zip", "--json"], files={"z.zip": b"not a zip file"})
add("z07-zip-twice", ["ingest", "zip", "demo", F + "z.zip", "--json"], files={"z.zip": zok}, then=[["ingest", "zip", "demo", F + "z.zip", "--json"]])
add("z08-zip-empty", ["ingest", "zip", "demo", F + "z.zip", "--json"], files={"z.zip": zipbytes([])})
add("z09-zip-corrupt-member", ["ingest", "zip", "demo", F + "z.zip", "--json"], files={"z.zip": zipbytes([("a.mp4", b"")])})
def drv(world):
    return {"files": {"FILE000001": {"path": str(MEDIA2), "name": "clip.mp4", "mime": "video/mp4"},
                      "GOODVID001": {"path": str(MEDIA), "name": "g.mp4", "mime": "video/mp4"},
                      "BADVID0001": {"path": str(MEDIA2), "name": "b.mp4", "mime": "video/mp4"}},
            "folders": {"FOLDER0001": ["GOODVID001", "BADVID0001"]}, "lie": {"BADVID0001": {"md5": "f" * 32}}}
link = "https://drive.google.com/file/d/FILE000001/view?usp=sharing"
add("d01-drive-hostile", ["ingest", "fetch-drive", "demo", "http://127.0.0.1/x"], drive=drv)
add("d01b-drive-hostile2", ["ingest", "fetch-drive", "demo", "https://drive.google.com.evil.io/file/d/FILE000001"], drive=drv)
add("d02-drive-file-json", ["ingest", "fetch-drive", "demo", link, "--uploaded-by", "dev@x.test", "--json"], drive=drv)
add("d02b-drive-file-text", ["ingest", "fetch-drive", "demo", link], drive=drv)
add("d03-drive-folder-partial", ["ingest", "fetch-drive", "demo", "FOLDER0001"], drive=drv)
add("d03b-drive-folder-partial-json", ["ingest", "fetch-drive", "demo", "FOLDER0001", "--json"], drive=drv)
add("d04-drive-noproject", ["ingest", "fetch-drive", "demo", link], variant="noproject", drive=drv)
add("d05-drive-twice", ["ingest", "fetch-drive", "demo", link, "--json"], drive=drv, then=[["ingest", "fetch-drive", "demo", link, "--json"]])
add("p01-prep", ["ingest", "prep", "demo", "{SRC}", "--no-whisper"], variant="approved")
add("p02-prep-unknown", ["ingest", "prep", "demo", "src_deadbeef", "--no-whisper"], variant="approved")
add("p03-prep-chunk", ["ingest", "prep", "demo", "{SRC}", "--no-whisper", "--chunk-minutes", "0.5"], variant="approved")
add("f01-frames-noanalysis", ["ingest", "frames", "demo", "{SRC}"], variant="approved")
add("f02-frames-unknown", ["ingest", "frames", "demo", "src_deadbeef"], variant="approved")
add("u01-run-mock", ["ingest", "run", "demo", "{SRC}", "--provider", "mock"], variant="approved")
add("u02-run-opposites", ["ingest", "run", "demo", "{SRC}", "--merge", "--replace"], variant="approved")
add("u03-run-unknown-src", ["ingest", "run", "demo", "src_deadbeef", "--provider", "mock"], variant="approved")
add("u04-run-unknown-provider", ["ingest", "run", "demo", "{SRC}", "--provider", "nonesuch"], variant="approved")
add("a01-analyze-mock", ["ingest", "analyze", "demo", "{SRC}", "--models", "mock"], variant="approved")
add("a02-analyze-unknown", ["ingest", "analyze", "demo", "src_deadbeef"], variant="approved")
add("g01-map-empty", ["ingest", "map", "demo"], variant="approved")
add("g02-map-noproject", ["ingest", "map", "demo"], variant="noproject")
add("h01-ingest-help", ["ingest", "--help"], variant="noproject")
add("h02-zip-help", ["ingest", "zip", "--help"], variant="noproject")
add("h03-drive-help", ["ingest", "fetch-drive", "--help"], variant="noproject")
if __name__ == "__main__":
    which = sys.argv[1]
    res = run_all(which, rows, workers=int(os.environ.get("W", "6")))
    json.dump(res, open(PR / f"res-master-{which}.json", "w"), indent=1, sort_keys=True)
    print(which, len(res), "rows done", sum(1 for r in res if not r["at_file_ok"]), "at_file_bad")
