import io, os, random, sys, zipfile, struct
from pathlib import Path
from autotester.store.project_store import ProjectStore
from autotester.sources.zip_intake import expand_zip
DATA = Path(sys.argv[1]); ROOT = DATA/"root"; ROOT.mkdir(exist_ok=True)
os.environ["AUTOTESTER_ROOT"] = str(ROOT)
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    zi = zipfile.ZipInfo("a.mp4"); zi.compress_type = zipfile.ZIP_LZMA
    z.writestr(zi, os.urandom(3000) + b"x"*5000)
    z.writestr("b.mp4", b"B"*500)
base = buf.getvalue(); print("len", len(base))
random.seed(7); outs = {}
n = 0
for k in range(60):
    b = bytearray(base); i = 49+random.randrange(0, 300); b[i] ^= 0xFF
    p = DATA/f"l{k}.zip"; p.write_bytes(bytes(b)); n += 1
    try:
        expand_zip(ProjectStore(f"p{n}", ROOT), p, max_file_bytes=5*1024*1024); outs["handled"] = outs.get("handled",0)+1
    except BaseException as e:
        key = f"UNHANDLED {type(e).__module__}.{type(e).__name__}"; outs[key] = outs.get(key,0)+1
print(outs)
# extract_version patch
b = bytearray(base); b[4:6] = struct.pack("<H", 99)       # local header version
cd = b.rfind(b"PK\x01\x02"); 
cds = [m for m in range(len(b)) if b[m:m+4]==b"PK\x01\x02"]
for c in cds: b[c+6:c+8] = struct.pack("<H", 99)
p = DATA/"ver.zip"; p.write_bytes(bytes(b)); n+=1
try:
    r = expand_zip(ProjectStore(f"p{n}", ROOT), p, max_file_bytes=5*1024*1024); print("ver:", r.status)
except BaseException as e: print("ver: UNHANDLED", type(e).__name__, e)
