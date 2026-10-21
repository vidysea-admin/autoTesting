import sys, os, csv, io, subprocess, tempfile, json, glob
from pathlib import Path
src = sys.argv[1]; label = sys.argv[2]
sys.path.insert(0, src)
from autotester.core import image_privacy as P
from PIL import Image
TESS = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
def read(img, psm, scale):
    im = Image.open(img).convert("RGB")
    if scale != 1:
        im = im.resize((im.width*scale, im.height*scale), Image.LANCZOS)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)/"a.png"; im.save(p)
        subprocess.run([TESS, str(p), str(Path(d)/"o"), "--psm", str(psm), "tsv"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t = (Path(d)/"o.tsv").read_text(encoding="utf-8")
    out = []
    for r in csv.DictReader(io.StringIO(t), delimiter="\t", quoting=csv.QUOTE_NONE):
        if r.get("level") != "5": continue
        txt = (r.get("text") or "").strip(); c = float(r["conf"])
        if not txt: continue
        x,y,w,h = [int(r[k])//scale for k in ("left","top","width","height")]
        box=(x,y,x+max(w,1),y+max(h,1))
        cr = Image.open(img).convert("L").crop(box)
        if cr.getextrema()[1] == 0: continue
        alnum = sum(ch.isalnum() for ch in txt)
        out.append((c, txt, alnum))
    return out
files = sorted(glob.glob(sys.argv[3] + "/**/*.png", recursive=True))
res = []
for f in files:
    with P.sanitized_images([Path(f)]) as b:
        if b.withheld:
            res.append({"f": f, "kept": False, "reason": b.reasons[0]}); continue
        kept = b.paths[0]
        det = {}
        for psm, sc in ((3,1),(11,1),(11,2)):
            w = read(kept, psm, sc)
            det[f"psm{psm}x{sc}"] = {"n_any": sum(1 for c,t,a in w if a>=3), "n_conf60": sum(1 for c,t,a in w if a>=3 and c>=60)}
        res.append({"f": f, "kept": True, **det})
json.dump(res, open(sys.argv[4], "w"), indent=1)
k = [r for r in res if r["kept"]]
print(label, "images", len(res), "kept", len(k), "withheld", len(res)-len(k))
from collections import Counter
print(Counter(r.get("reason") for r in res if not r["kept"]))
for key in ("psm3x1","psm11x1","psm11x2"):
    print(key, "kept images with >=1 conf60 word:", sum(1 for r in k if r[key]["n_conf60"]>0), "with >=1 any word:", sum(1 for r in k if r[key]["n_any"]>0), "total conf60 words", sum(r[key]["n_conf60"] for r in k))
