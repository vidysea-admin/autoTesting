"""Container smoke workflow shape, and the DIAGNOSIS/redact functions of the diagnose script.

No docker: the script is sourced under bash and fed canned log snippets."""
# ruff: noqa: E501

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/container_diagnose.sh"
WORKFLOW = ROOT / ".github/workflows/container-smoke.yml"
BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(BASH is None, reason="bash not installed")
PATHS = {"Dockerfile", "docker/**", "scripts/container_diagnose.sh", "pyproject.toml",
         "uv.lock", "src/**", ".github/workflows/container-smoke.yml"}


@pytest.fixture(scope="module")
def wf():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_triggers(wf):
    on = wf[True] if True in wf else wf["on"]  # YAML 1.1 parses the key `on` as True
    assert set(on["push"]["paths"]) == PATHS and on["push"]["branches"] == ["master"]
    assert set(on["pull_request"]["paths"]) == PATHS
    assert "workflow_dispatch" in on and "pull_request_target" not in on


def test_permissions_timeout_and_pins(wf):
    assert wf["permissions"] == {"contents": "read"}
    job = wf["jobs"]["smoke"]
    assert job["timeout-minutes"] == 40
    uses = [s["uses"] for s in job["steps"] if "uses" in s]
    assert uses == ["actions/checkout@v4", "actions/upload-artifact@v4"]


def test_always_upload_and_summary(wf):
    steps = wf["jobs"]["smoke"]["steps"]
    upload = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    assert upload["if"] == "always()"
    assert upload["with"]["name"] == "container-smoke-evidence"
    assert upload["with"]["retention-days"] == 14
    path = upload["with"]["path"]
    assert "container-debug-*.log" in path and "summary.md" in path
    summary = next(s for s in steps if "GITHUB_STEP_SUMMARY" in s.get("run", ""))
    assert summary["if"] == "always()"
    run_step = next(s for s in steps if "container_diagnose" in s.get("run", ""))
    assert "container_diagnose.sh" in run_step["run"]


def test_no_secrets_or_env_dump():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text and "pull_request_target" not in text
    assert "printenv" not in text and "env |" not in text and "set -x" not in text


def diagnose(tmp_path, snippet):
    log = tmp_path / "in.log"
    log.write_bytes(snippet.encode())
    cmd = f'source "{SCRIPT.as_posix()}"; diagnose "{log.as_posix()}"; echo "rc=$?"'
    r = subprocess.run([BASH, "-c", cmd], capture_output=True, text=True, check=True)
    return r.stdout


@needs_bash
def test_script_syntax_and_line_endings():
    assert subprocess.run([BASH, "-n", str(SCRIPT)]).returncode == 0
    assert b"\r" not in SCRIPT.read_bytes()


@needs_bash
@pytest.mark.parametrize("snippet,cause", [
    ("/entrypoint.sh: line 10: /opt/venv/bin/python: Permission denied", "perm-denied"),
    ("State: ExitCode=126 OOMKilled=false", "perm-denied"),
    ("PREFLIGHT FAIL: cannot exec /opt/venv/bin/python\n  uid=10001 gid=10001",
     "preflight"),
    ("State: ExitCode=137 OOMKilled=true Error=", "at least 4 GiB"),
    ("READINESS: NOT READY after 240s (limit 240s)", "raise the startup-probe timeout"),
    ("OSError: [Errno 98] error while attempting to bind: Address already in use", "port-in-use"),
    ("gcsfuse: failed to mount gs://bucket: permission denied", "gcs-or-env"),
    ("FileNotFoundError: [Errno 2] No such file or directory: '/data/.env'", "gcs-or-env"),
    ("Xvfb failed to start\ncontainer service exited; restarting stack", "display"),
    ("exec /entrypoint.sh: exec format error", "linux/amd64"),
    ("/usr/bin/env: 'bash\r': bad interpreter", "crlf"),
])
def test_signature_cause(tmp_path, snippet, cause):
    out = diagnose(tmp_path, snippet)
    assert cause in out and "[FAIL]" in out and not out.rstrip().endswith("rc=0")


@needs_bash
def test_preflight_prints_uid_and_path_lines(tmp_path):
    snippet = ("PREFLIGHT FAIL: x\n  uid=10001 gid=10001\n"
               "  readlink -f: /root/.local/bin/python3.12\n")
    out = diagnose(tmp_path, snippet)
    assert "uid=10001" in out and "/root/.local/bin/python3.12" in out


@needs_bash
def test_clean_log_and_env_absent_is_info(tmp_path):
    out = diagnose(tmp_path, "READINESS: READY after 12s\n/app/.env is absent\nState: ExitCode=0\n")
    assert "[OK]" in out and "[INFO] env-absent" in out and out.rstrip().endswith("rc=0")


@needs_bash
@pytest.mark.parametrize("snippet", [
    "PermissionError: [Errno 13] Permission denied: '/app/.work'",
    "mkdir: cannot create directory '/app/.work': Permission denied",
])
def test_app_level_permission_error_is_a_failure(tmp_path, snippet):
    out = diagnose(tmp_path, snippet)
    assert "[FAIL] app-perm" in out and "/data" in out and "perm-denied" not in out
    assert not out.rstrip().endswith("rc=0")


@needs_bash
@pytest.mark.parametrize("snippet", [
    "access denied by policy; request denied for user",
    "Denied: nothing to do\nconsent denied by the user",
    "/entrypoint.sh: line 10: /opt/venv/bin/python: Permission denied",
])
def test_benign_denied_text_does_not_fire_app_perm(tmp_path, snippet):
    assert "app-perm" not in diagnose(tmp_path, snippet)


@needs_bash
def test_exit_trap_removes_container_without_unbound_error(tmp_path):
    """Regression: the EXIT trap used a main()-local $cname under set -u ('cname: unbound variable')."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    calls = tmp_path / "calls.txt"
    fake = bindir / "docker"
    fake.write_text(f'#!/bin/sh\necho "$@" >> "{calls.as_posix()}"\nexit 0\n', encoding="utf-8", newline="\n")
    fake.chmod(0o755)
    cmd = (f'export PATH="$(cd "{bindir.as_posix()}" && pwd):$PATH"; source "{SCRIPT.as_posix()}"; '
           f'main --image x --timeout 1 --out "{tmp_path.as_posix()}/out"')
    r = subprocess.run([BASH, "-c", cmd], capture_output=True, text=True, timeout=90)
    assert "unbound variable" not in r.stderr, r.stderr
    assert "rm -f autotester-smoke-" in calls.read_text(encoding="utf-8")
