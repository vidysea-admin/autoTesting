"""Checker falsification driver: copy tree outside the worktree, green-before, mutate, red-after."""
import os, shutil, subprocess, sys, pathlib

W = pathlib.Path("D:/autoTesting/.worktrees/g11-port-wiring")
SC = pathlib.Path("C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad")
PY = str(W / ".venv/Scripts/python.exe")
T1 = "tests/test_role_session_port.py::"
T2 = "tests/test_role_session_port_login.py::"

CASES = {
    "pw1": dict(
        file="src/autotester/stages/role_session_port.py",
        old="if not host_in_platform(platform, host_of(url)):",
        new="if False:",
        node=T1 + "test_pw1_a_target_outside_the_roles_platform_is_refused_before_the_browser_moves"),
    "pw2": dict(
        file="src/autotester/browser/role_probe.py",
        old="success = next((s for s in success_selectors if resolve(page, s).first.is_visible()), None)",
        new="success = None",
        node=T1 + "test_pw2_api_error_finds_the_failed_save_behind_the_success_screen"),
    "pw3": dict(
        file="src/autotester/stages/role_session_port.py",
        old="text=self._redactor.scrub(snap.text)))",
        new="text=snap.text))",
        node=T1 + "test_pw3_observations_and_screen_text_are_scrubbed"),
    "pw4": dict(
        file="src/autotester/stages/role_port_state.py",
        old="broken = sorted(rid for rid, st in self._states.items() if st.failed)",
        new="broken = []",
        node=T2 + "test_pw4_a_failed_login_errors_every_oracle_and_yields_no_findings"),
}


def run(cwd, node, log):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(cwd / "src"), str(cwd / "scripts")]), TMP="D:/autoTesting/.work/tmp",
               TEMP="D:/autoTesting/.work/tmp")
    pkg = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], cwd=cwd, env=env,
                         capture_output=True, text=True).stdout.strip()
    log.write(f"PKG {pkg}\n")
    p = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", node], cwd=cwd, env=env,
                       capture_output=True, text=True, timeout=900)
    tail = (p.stdout + p.stderr)[-2500:]
    log.write(f"EXIT {p.returncode}\n{tail}\n")
    return p.returncode


def main(name):
    c = CASES[name]
    copy = SC / f"fal_{name}"
    if copy.exists():
        shutil.rmtree(copy)
    copy.mkdir()
    for d in ("src", "tests", "scripts"):
        shutil.copytree(W / d, copy / d, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    shutil.copy(W / "pyproject.toml", copy / "pyproject.toml")
    with open(SC / f"fal_{name}.log", "w", encoding="utf-8") as log:
        log.write(f"== GREEN-BEFORE {c['node']}\n")
        g = run(copy, c["node"], log)
        target = copy / c["file"]
        text = target.read_text(encoding="utf-8")
        assert text.count(c["old"]) == 1, (name, text.count(c["old"]))
        target.write_text(text.replace(c["old"], c["new"]), encoding="utf-8")
        log.write(f"== RED-AFTER (edit {c['file']}: {c['old']!r} -> {c['new']!r})\n")
        r = run(copy, c["node"], log)
        log.write(f"RESULT {name} green_exit={g} red_exit={r}\n")


main(sys.argv[1])
