"""Behavioural tests: run the real docker/entrypoint.sh and the Dockerfile's
/startup-diagnostics.sh with bash in a sandbox (hardcoded paths rewritten, services stubbed)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash not available; cannot run scripts")

PY_STUB = (
    '#!/bin/sh\nif [ "$1" = "-c" ] || [ "$1" = "--version" ]; then exit 0; fi\n'
    'echo "STUB-ARGS $*"\n'
)


def posix(path: Path) -> str:
    cyg = shutil.which("cygpath")
    if cyg:
        return subprocess.run([cyg, "-u", str(path)], capture_output=True, text=True).stdout.strip()
    return path.as_posix()


def make_stub(path: Path, body: str, executable: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")
    path.chmod(0o755 if executable else 0o644)
    return path


def sandbox(tmp_path: Path, script: str, repl: dict[str, str]) -> Path:
    """Rewrite only the listed hardcoded absolute paths in the script text."""
    for old, new in repl.items():
        script = script.replace(old, new)
    out = tmp_path / "script.sh"
    out.write_text(script, encoding="utf-8", newline="\n")
    return out


def run(script: Path, tmp_path: Path, *args: str, env: dict | None = None):
    full = {k: v for k, v in os.environ.items() if k != "PORT"}
    full.update(env or {})
    return subprocess.run([BASH, posix(script), *args], capture_output=True, text=True,
                          env=full, timeout=30, cwd=tmp_path)


@pytest.fixture
def entry(tmp_path):
    """Sandboxed entrypoint.sh plus the path of its python stub."""
    root = posix(tmp_path)
    text = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
    script = sandbox(tmp_path, text, {
        "/opt/venv/bin/python": f"{root}/venv/bin/python", "/opt/uv-python": f"{root}/uv-python",
        "/opt/venv": f"{root}/venv", "/app/docker": f"{root}/app", "/tmp/.X": f"{root}/.X"})
    (tmp_path / "uv-python").mkdir()
    return script, tmp_path / "venv/bin/python"


def test_preflight_fails_126_on_non_executable_python(entry, tmp_path):
    script, py = entry
    make_stub(py, PY_STUB, executable=False)
    if subprocess.run([BASH, "-c", f'[ -x "{posix(py)}" ]']).returncode == 0:
        pytest.skip("filesystem reports a mode-644 file as executable; cannot test non-exec python")
    r = run(script, tmp_path)
    assert r.returncode == 126
    assert "PREFLIGHT FAIL" in r.stderr and "uid=" in r.stderr


def test_preflight_fails_126_when_python_missing(entry, tmp_path):
    script, _ = entry
    r = run(script, tmp_path)
    assert r.returncode == 126
    assert "PREFLIGHT FAIL" in r.stderr and "uid=" in r.stderr


def test_preflight_passes_and_reports_port(entry, tmp_path):
    script, py = entry
    make_stub(py, PY_STUB)
    r = run(script, tmp_path, env={"PORT": "9123"})
    assert r.returncode == 0, r.stderr
    assert "app port=9123 (PORT=9123)" in r.stdout and "tcp:9123" in r.stdout
    r = run(script, tmp_path)
    assert r.returncode == 0 and "app port=8000 (PORT=unset)" in r.stdout and "tcp:8000" in r.stdout


def diag_body() -> str:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    block = re.search(r"printf '%s\\n' \\\r?\n(.*?)\s*> /startup-diagnostics\.sh", text, re.S)
    assert block, "diagnostics wrapper not found in Dockerfile"
    lines = re.findall(r"^\s*'(.*)' \\\r?$", block.group(1), re.M)
    return "\n".join(lines) + "\n"


def test_diagnostics_wrapper_execs_entrypoint_and_propagates_rc(tmp_path):
    root = posix(tmp_path)
    make_stub(tmp_path / "venv/bin/python", PY_STUB)
    make_stub(tmp_path / "entrypoint.sh", '#!/bin/bash\necho "ENTRYPOINT-RAN $*"\nexit 5\n')
    make_stub(tmp_path / "bin/namei", "#!/bin/sh\nexit 0\n")
    script = sandbox(tmp_path, diag_body(), {
        "/opt/venv/bin/python": f"{root}/venv/bin/python",
        "/entrypoint.sh": f"{root}/entrypoint.sh", "/app/.env": f"{root}/app.env"})
    r = run(script, tmp_path, "bash", "-c", "echo hi; exit 5",
            env={"PATH": f"{root}/bin:{os.environ['PATH']}"})
    assert "EXECUTING APPLICATION ENTRYPOINT" in r.stdout and "ENTRYPOINT-RAN" in r.stdout
    assert r.returncode == 5, r.stderr
