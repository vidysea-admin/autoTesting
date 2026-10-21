import sys, glob, csv, io, subprocess, tempfile
from pathlib import Path
from PIL import Image
TESS = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
for f in sorted(glob.glob(sys.argv[1]+"/kept*.png")):
    im0 = Image.open(f).convert("RGB"); ws=[]
    for sc in (1,2):
        im = im0.resize((im0.width*sc, im0.height*sc), Image.LANCZOS) if sc!=1 else im0
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.png"; im.save(p)
            subprocess.run([TESS,str(p),str(Path(d)/"o"),"--psm","11","tsv"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            t=(Path(d)/"o.tsv").read_text(encoding="utf-8")
        g=im0.convert("L")
        for r in csv.DictReader(io.StringIO(t),delimiter="\t",quoting=csv.QUOTE_NONE):
            if r.get("level")!="5": continue
            tx=(r.get("text") or "").strip()
            if sum(c.isalnum() for c in tx)<3 or float(r["conf"])<40: continue
            x,y,w,h=[int(r[q])//sc for q in ("left","top","width","height")]
            if g.crop((x,y,x+max(w,1),y+max(h,1))).getextrema()[1]==0: continue
            ws.append(tx)
    print(Path(f).name, sorted(set(ws)))
