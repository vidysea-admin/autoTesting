"""One falsification per repaired point, each in its own throwaway copy. usage: falsify.py <name>"""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path
B = Path(os.environ["R2B_B"])
HEAD, BASE = B / "head", B / "base"
PY = str(HEAD / ".venv" / "Scripts" / "python.exe")
T = "tests/test_browser_cdp_probe_hostile.py::"

def edit_1a(s):  # no overall deadline: the watchdog never starts
    assert s.count("    watchdog.start()\n") == 1
    return s.replace("    watchdog.start()\n", "    pass  # FALSIFIED: no watchdog\n")
def edit_1b(s):  # unbounded read: neither the declared-length nor the running-size cap
    a = '        if int(reply.getheader("Content-Length") or 0) > PROBE_MAX_BYTES:\n            raise ValueError("reply too large")\n'
    b = '            if size > PROBE_MAX_BYTES:\n                raise ValueError("reply too large")\n'
    assert s.count(a) == 1 and s.count(b) == 1
    return s.replace(a, "").replace(b, "")
def edit_2(s):  # RecursionError escapes
    a = "    except Exception:  # every doubt about this endpoint is a refusal\n"
    assert s.count(a) == 1
    return s.replace(a, "    except (OSError, ValueError, http.client.HTTPException):  # FALSIFIED\n")
def edit_3(s):  # follow redirects again: the repair-base _answers_as (urllib opener)
    base = (BASE / "src/autotester/browser/launch.py").read_text(encoding="utf-8")
    m = re.search(r"def _answers_as\(.*?\n(?=\n\ndef )", base, re.S)
    cur = re.search(r"def _answers_as\(.*?\n(?=\n\ndef )", s, re.S)
    assert m and cur
    s = s.replace(cur.group(0), m.group(0))
    return s.replace("import time\n", "import time\nimport urllib.request\n", 1)

POINTS = {
 "1a": (edit_1a, [T + "test_a_trickling_listener_is_cut_off_at_the_overall_deadline[drip_headers]"]),
 "1b": (edit_1b, [T + "test_a_correct_answer_padded_past_the_byte_cap_is_refused[padded_declared]",
                  T + "test_a_correct_answer_padded_past_the_byte_cap_is_refused[padded_undeclared]"]),
 "2": (edit_2, [T + "test_a_deeply_nested_reply_is_not_this_browser_not_a_recursion_error"]),
 "3": (edit_3, [T + "test_a_redirect_is_never_followed[loopback_port]", T + "test_a_redirect_is_never_followed[other_host]"]),
}

def run(copy, nodes):
    env = {**os.environ, "PYTHONPATH": f"{copy/'src'}{os.pathsep}{copy/'tests'}", "PYTHONUNBUFFERED": "1"}
    t = time.monotonic()
    p = subprocess.run([PY, "-m", "pytest", *nodes, "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=", "--tb=short"],
                       cwd=copy, env=env, capture_output=True, text=True, timeout=300)
    return p.returncode, round(time.monotonic() - t, 1), p.stdout[-2500:]

name = sys.argv[1]
fn, nodes = POINTS[name]
copy = B / f"fals-{name}-{os.getpid()}"
shutil.copytree(HEAD, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".git"))
env = {**os.environ, "PYTHONPATH": f"{copy/'src'}{os.pathsep}{copy/'tests'}"}
w = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], cwd=copy, env=env, capture_output=True, text=True).stdout.strip()
res = {"point": name, "copy": str(copy), "autotester.__file__": w, "inside_copy": os.path.normcase(w).startswith(os.path.normcase(str(copy)))}
res["green_before"] = run(copy, nodes)
lp = copy / "src/autotester/browser/launch.py"
orig = lp.read_text(encoding="utf-8")
lp.write_text(fn(orig), encoding="utf-8")
res["red_after"] = run(copy, nodes)
lp.write_text(orig, encoding="utf-8")
res["restored"] = run(copy, nodes)
print(json.dumps(res, indent=1))
