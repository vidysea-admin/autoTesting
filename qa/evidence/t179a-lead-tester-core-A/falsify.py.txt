"""Mutation driver: one fresh copy per edit; green -> edit -> red -> restore -> green."""
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BOUND = Path("C:/Users/Lenovo/AppData/Local/Temp/chk-t177r2a-1798127267")
PY = str(BOUND / ".venv/Scripts/python.exe")
SCR = Path("C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad")
OUT = Path("D:/autoTesting/qa/evidence/t177-slice0-r2-A/falsify")
OUT.mkdir(parents=True, exist_ok=True)
REL = "src/autotester/browser/launch.py"
TF = "tests/test_browser_cdp_probe_hostile.py"
ORIG = (BOUND / REL).read_text(encoding="utf-8")


def sub_span(text, start, end_incl, new):
    i = text.index(start)
    j = text.index(end_incl, i) + len(end_incl)
    return text[:i] + new + text[j:]


def once(old, new):
    def f(t):
        assert t.count(old) == 1, (old, t.count(old))
        return t.replace(old, new)
    return f


WD = "    watchdog.start()\n"
WHILE = "        while time.monotonic() < deadline:\n"
CL = '        if int(reply.getheader("Content-Length") or 0) > PROBE_MAX_BYTES:\n            raise ValueError("reply too large")\n'
SZ = '            if size > PROBE_MAX_BYTES:\n                raise ValueError("reply too large")\n'


def m_1a_both(t):
    # one hunk: from watchdog.start() through the read-loop header
    i = t.index(WD)
    j = t.index(WHILE) + len(WHILE)
    span = t[i:j]
    new = span.replace(WD, "").replace(WHILE, "        while True:\n")
    return t[:i] + new + t[j:]


def m_1b_both(t):
    i = t.index(CL)
    j = t.index(SZ) + len(SZ)
    span = t[i:j].replace(CL, "").replace(SZ, "")
    return t[:i] + span + t[j:]


REDIR = '''        if reply.status in (301, 302, 303, 307, 308):
            import urllib.request
            return urllib.request.urlopen(reply.getheader("Location"), timeout=PROBE_DEADLINE_S).read()
        if reply.status != 200:
'''

MUT = {
    "1a-main-both": dict(point="1a", sel="drip or trickl or deadline", f=m_1a_both),
    "1a-q2-while-true-only": dict(point="1a", sel="drip or trickl or deadline", f=once(WHILE, "        while True:\n"), quality=True),
    "1a-q3-no-watchdog-start": dict(point="1a", sel="drip or trickl or deadline", f=once(WD, ""), quality=True),
    "1b-main-both": dict(point="1b", sel="padded or huge", f=m_1b_both),
    "1b-qa-no-declared-check": dict(point="1b", sel="padded or huge", f=once(CL, ""), quality=True),
    "1b-qb-no-size-check": dict(point="1b", sel="padded or huge", f=once(SZ, ""), quality=True),
    "1b-qc-readsize-65536": dict(point="1b", sel="padded or huge", f=once("reply.read1(PROBE_MAX_BYTES + 1 - size)", "reply.read1(65536)"), quality=True),
    "2-except-narrow": dict(point="2", sel="deep", f=once("    except Exception:  # every doubt", "    except (OSError, ValueError, http.client.HTTPException):  # every doubt")),
    "3-follow-redirect": dict(point="3", sel="redirect", f=once("        if reply.status != 200:\n", REDIR)),
    "q-d-status-ge-500": dict(point="d", sel="redirect", f=once("reply.status != 200", "reply.status >= 500"), quality=True),
}


def run_pytest(copy, sel, log):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(copy / p) for p in ("src", "scripts", "tests"))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [PY, "-m", "pytest", "-p", "no:cacheprovider", "-p", "no:xdist", "-o", "addopts=",
           "--rootdir", str(copy), "-v", "--tb=short", str(copy / TF)]
    if sel:
        cmd += ["-k", sel]
    t0 = time.monotonic()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(copy), timeout=200)
    dt = time.monotonic() - t0
    out = p.stdout + p.stderr
    Path(log).write_text(out, encoding="utf-8")
    ids = re.findall(r"^(\S+::\S+(?:\[[^\]]*\])?) (PASSED|FAILED|ERROR)", out, re.M)
    summ = re.findall(r"=+ (.*?) in [\d.]+s", out)
    errs = [l.strip() for l in out.splitlines() if l.startswith("E  ")]
    return dict(rc=p.returncode, secs=round(dt, 1), ids=ids, summary=summ[-1] if summ else "?", errs=errs[:6],
                rootdir=re.findall(r"^rootdir: (.*)$", out, re.M))


def one(name):
    spec = MUT[name]
    copy = Path(tempfile.mkdtemp(prefix=f"fals-{name}-", dir=str(SCR))) / "t"
    shutil.copytree(BOUND, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git"))
    d = OUT / name
    d.mkdir(exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(copy / p) for p in ("src", "scripts", "tests"))
    ident = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], capture_output=True, text=True, env=env, cwd=str(copy), timeout=60).stdout.strip()
    sel = None if spec.get("quality") and spec["point"] in ("d",) else spec["sel"]
    runs = {}
    runs["green"] = run_pytest(copy, sel, d / "1-green.log")
    f = copy / REL
    f.write_text(spec["f"](ORIG), encoding="utf-8", newline="")
    diff = "".join(difflib.unified_diff(ORIG.splitlines(True), f.read_text(encoding="utf-8").splitlines(True), "a/launch.py", "b/launch.py", n=1))
    (d / "edit.diff").write_text(diff, encoding="utf-8")
    runs["red"] = run_pytest(copy, sel, d / "2-edited.log")
    # quality probes: also the whole file
    if spec.get("quality"):
        runs["red_fullfile"] = run_pytest(copy, None, d / "2b-edited-fullfile.log")
    f.write_text(ORIG, encoding="utf-8", newline="")
    runs["restored"] = run_pytest(copy, sel, d / "3-restored.log")
    restored_same = f.read_text(encoding="utf-8") == ORIG and (BOUND / REL).read_text(encoding="utf-8") == ORIG
    res = dict(name=name, point=spec["point"], sel=sel, autotester_file=ident, copy=str(copy), runs=runs, diff=diff, restored_same=restored_same)
    (d / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    names = sys.argv[1:] or list(MUT)
    with ThreadPoolExecutor(3) as ex:
        results = list(ex.map(one, names))
    for r in results:
        print("=====", r["name"], r["autotester_file"], r["runs"]["green"]["rootdir"], "restored_same", r["restored_same"])
        for k, v in r["runs"].items():
            print(" ", k, v["summary"], v["secs"], "s")
            if k.startswith("red"):
                for i, s in v["ids"]:
                    if s != "PASSED":
                        print("    ", s, i)
                print("     E:", v["errs"][:3])
            if k == "red_fullfile":
                print("    passed-ids:", len([1 for i, s in v["ids"] if s == "PASSED"]))
        print(r["diff"])
    (OUT / "all.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
