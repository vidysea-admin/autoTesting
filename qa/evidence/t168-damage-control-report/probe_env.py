import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from seed import *
from autotester.stages.report_export import _load_redactor, _repro_steps
d = Path(tempfile.mkdtemp()); os.environ["AUTOTESTER_ROOT"] = str(d)
s = mk_project(d)
r = _load_redactor(s)
print("redactor holds SPECIAL:", SPECIAL in r._values, "| holds PLAIN:", PLAIN in r._values)
print("env file:", (d/".env").read_text().replace(PLAIN,"<P>"))
print("scrub raw ->", r.scrub(f"x {SPECIAL} y"))
import html
print("scrub after html.escape ->", r.scrub(html.escape(f"x {SPECIAL} y")))
