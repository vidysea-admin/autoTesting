"""Checker B probe: synthetic leak record with a fake secret + fake email through the real stage code."""
import base64
import hmac
import io
import logging
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"D:\autoTesting\.worktrees\t209-leak-severity\src")
from PIL import Image  # noqa: E402

from autotester.core import image_privacy as privacy  # noqa: E402
from autotester.schema.multi_role_enums import FindingClass  # noqa: E402
from autotester.schema.multi_role_finding import MultiRoleFinding  # noqa: E402
from autotester.stages import leak_evidence as stage  # noqa: E402

MASTER = "SYNTH-MASTER-KEY-qa7Zk2Lm9"
os.environ[stage.LEAK_KEY_ENV] = MASTER
stage.load_repo_env = lambda *a, **k: []  # never touch a real .env

NAME, EMAIL, PHONE = "Fakeperson Zzyzx", "fakeperson.zzyzx@canary.invalid", "+1 (555) 013-7788"
SECRET = "sk-FAKE-SECRET-9f8e7d6c5b4a"
rows = [{"id": f"STU-{n}", "name": NAME, "email": EMAIL, "phone": PHONE, "api_secret": SECRET}
        for n in range(8)]
run = Path(r"D:\chk-scratch-t209b\probe-run")
shutil.rmtree(run, ignore_errors=True)
run.mkdir(parents=True)

buf = io.StringIO()
h = logging.StreamHandler(buf)
logging.getLogger().addHandler(h)
logging.getLogger().setLevel(logging.DEBUG)

HEADER = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
          "left\ttop\twidth\theight\tconf\ttext\n")
privacy._local_ocr = lambda p: HEADER + "5\t1\t1\t1\t1\t1\t10\t10\t35\t10\t97\tFakeperson\n"
png_path = run.parent / "probe-raw.png"
Image.new("RGB", (100, 60), "white").save(png_path)
raw = png_path.read_bytes()

url = f"https://app.example.test/students/{SECRET}?token={SECRET}&email={EMAIL}#frag"
try:
    ev = stage.collect_leak_evidence(project_slug="demo", run_dir=run, finding_id="probe-1",
                                     rows=rows, id_field="id", url=url, screenshot_png=raw)
    print("collect ok; url_template =", ev.url_template, "| ids", len(ev.hashed_ids))
    f = MultiRoleFinding(finding_id="probe-1", finding_class=FindingClass.DATA_LEAK, title="t",
                         role="Parent", platform_id="parent", url_template=ev.url_template,
                         steps=["login as Parent", "goto /students/{id}"],
                         count=ev.foreign_row_count, leak_evidence=ev)
    stage.write_finding(run, f)
except Exception as exc:  # noqa: BLE001
    print("collect/write raised:", type(exc).__name__, "(message withheld from the sweep below)")
    print("exception text contains secret/email/key:",
          any(s in str(exc) for s in (SECRET, EMAIL, NAME, MASTER)))

derived = stage.project_key("demo")
needles = {"name": NAME, "email": EMAIL, "phone": PHONE, "phone-tail": "013-7788", "secret": SECRET,
           "master-key": MASTER, "derived-key-hex": derived.hex(),
           "derived-key-b64": base64.b64encode(derived).decode(), "raw-id": "STU-3"}
blobs = [p.read_bytes() for p in run.rglob("*") if p.is_file()]
files = sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file())
print("files under run dir:", files)
log_text = buf.getvalue()
for label, n in needles.items():
    in_files = any(n.encode() in b or n.encode("utf-16-le") in b for b in blobs)
    print(f"  {label:16s} in run-dir files: {in_files}  in log: {n in log_text}")
print("raw png bytes in any run file:", any(raw in b for b in blobs))
print("log lines:", [ln[:90] for ln in log_text.splitlines()])
print("hmac check:", all(len(x) == 64 for x in ev.hashed_ids) if 'ev' in dir() else "n/a",
      hmac.compare_digest(stage.hash_id(derived, "STU-0").encode(), ev.hashed_ids[0].encode())
      if 'ev' in dir() else "")

# token-like path segment probe (no digits run, no long hex)
for u in ("https://a.test/invite/xQzLmPwRtYuIoPaSdFgHjK", "https://a.test/students/zorblax-quimby",
          "https://a.test/r/Zk3jQmVxLmPw9RtYu1IoPa5S?x=1"):
    print("templatise", u, "->", stage.templatise_url(u))
