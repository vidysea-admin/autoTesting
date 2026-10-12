import json, os, re, glob
from common import *
port = 22103; root = os.path.join(B, "run3")
ck = json.load(open(EV + r"\t3-ck.json"))["ck"]
def up(grp, slug, name, content, ctype="video/mp4"):
    body, h = multipart({"label": f"t5-{grp}"}, {"recording": (name, content, ctype)})
    s, hd, d = req(port, "POST", f"/projects/{slug}/sources/upload", h, body, cookie=ck[grp])
    print("UPLOAD", grp, slug, name, s, dict(hd).get("Location"), d[:120] if s != 303 else "")
up("admin", "qa-proj", "fake-admin.mp4", b"\x00\x00\x00\x18ftypmp42ADMINbytes")
up("sub-admin", "qa-proj", "fake-sub.mp4", b"\x00\x00\x00\x18ftypmp42SUBbytes12")
up("developer", "dev-proj", "fake-dev.mp4", b"\x00\x00\x00\x18ftypmp42DEVbytes123")
# find records
for dp, dn, fn in os.walk(os.path.join(root, "projects")):
    for f in fn:
        pth = os.path.join(dp, f)
        if f.endswith((".json", ".jsonl")):
            t = open(pth, encoding="utf-8", errors="replace").read()
            if "uploaded_by" in t:
                for m in re.finditer(r'"?uploaded_by"?\s*[:=]\s*("[^"]*"|null)', t): print("REC", os.path.relpath(pth, root), m.group(0))
