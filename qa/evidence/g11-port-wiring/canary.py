"""Checker PW3 probe: re-run the PW3 tests in a copy whose planted secrets/PII are MY values."""
import os, shutil, subprocess, pathlib

W = pathlib.Path("D:/autoTesting/.worktrees/g11-port-wiring")
SC = pathlib.Path("C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad")
PY = str(W / ".venv/Scripts/python.exe")
copy = SC / "canary_copy"
if copy.exists():
    shutil.rmtree(copy)
copy.mkdir()
for d in ("src", "tests", "scripts"):
    shutil.copytree(W / d, copy / d, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
shutil.copy(W / "pyproject.toml", copy / "pyproject.toml")
app = copy / "tests/role_port_app.py"
t = app.read_text(encoding="utf-8")
for old, new in (("alice-port-pw", "zk7canaryalicepw91"), ("bob-port-pw", "qx3canarybobpw44"),
                 ("canary.person@example.org", "mallory.q.tester@vendor-example.net"),
                 ("+1 415 555 0142", "+44 20 7946 0958")):
    assert old in t, old
    t = t.replace(old, new)
app.write_text(t, encoding="utf-8")
# the test module imports its canaries from the app, so only the app needs editing
env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(copy / "src"), str(copy / "scripts")]),
           TMP="D:/autoTesting/.work/tmp", TEMP="D:/autoTesting/.work/tmp")
p = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider",
                    "tests/test_role_session_port.py::test_pw3_no_canary_reaches_findings_summary_or_disk",
                    "tests/test_role_session_port.py::test_pw3_observations_and_screen_text_are_scrubbed",
                    "tests/test_role_session_port.py::test_pw3_the_network_log_holds_templates_and_first_party_hosts_only"],
                   cwd=copy, env=env, capture_output=True, text=True, timeout=900)
print("EXIT", p.returncode)
print((p.stdout + p.stderr)[-1800:])
