"""Container smoke workflow shape, and the DIAGNOSIS/redact functions of the diagnose script.

No docker: the script is sourced under bash and fed canned log snippets."""
# ruff: noqa: E501  (the SHAPES table keeps one secret shape per line)

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
def test_redaction():
    text = ("OPENAI_API_KEY=sk-abcdefghijklmnop1234\nAUTOTESTER_APPROVAL_KEY=hunter2\n"
            'x {"password": "s3cr3t!"}\nAuthorization: Bearer abc.def-ghi\n'
            "DB_PASSWORD: pw99\nPORT=8000\n")
    cmd = f'source "{SCRIPT.as_posix()}"; redact'
    r = subprocess.run([BASH, "-c", cmd], input=text, capture_output=True, text=True, check=True)
    for leaked in ("sk-abcdefghijklmnop1234", "hunter2", "s3cr3t", "abc.def-ghi", "pw99"):
        assert leaked not in r.stdout
    assert "PORT=8000" in r.stdout and "AUTOTESTER_APPROVAL_KEY=<redacted>" in r.stdout


def redact_text(text):
    cmd = f'source "{SCRIPT.as_posix()}"; redact'
    r = subprocess.run([BASH, "-c", cmd], input=text, capture_output=True, text=True, check=True)
    return r.stdout


PEM = ("-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\nZZtopsecretbody123\n"
       "-----END PRIVATE KEY-----")
GH = "a1B2c3D4e5F6g7H8i9J0k1L2m3"
# name -> (input line, secrets that must vanish, text that must survive: the key name)
SHAPES = {
    "url-userinfo": ("pull from https://deploy:Sup3rPw@git.example.com/r.git", ["Sup3rPw"], "git.example.com"),
    "basic-auth": ("Authorization: Basic dXNlcjpzZWNyZXRwdw==", ["dXNlcjpzZWNyZXRwdw"], "Authorization"),
    "bearer": ("authorization: bearer abc.def-ghi", ["abc.def-ghi"], "authorization"),
    "pwd": ("pwd=hunter22", ["hunter22"], "pwd"),
    "passwd": ("passwd: hunter23", ["hunter23"], "passwd"),
    "auth": ("auth=hunter24", ["hunter24"], "auth"),
    "credential": ("credential=hunter25", ["hunter25"], "credential"),
    "credentials": ("CREDENTIALS: hunter26", ["hunter26"], "CREDENTIALS"),
    "flag-password": ("docker login --password hunter27 --user bob", ["hunter27"], "--password"),
    "flag-token": ("tool --token hunter28 run", ["hunter28"], "--token"),
    "flag-eq": ("tool --api-key=hunter29 run", ["hunter29"], "--api-key"),
    "ghp": ("GITHUB_TOKEN=ghp_" + GH, [GH], "GITHUB_TOKEN"),
    "gho": ("cloned with gho_" + GH, [GH], "gho_"),
    "ghs": ("ghs_" + GH + " end", [GH], "ghs_"),
    "github-pat": ("x github_pat_" + "11ABCDEFG0abcdefghij_klmnopqrstuv", ["11ABCDEFG0abcdefghij"], "github_pat_"),
    "quoted-space": ('token = "alpha beta gamma"', ["alpha", "beta", "gamma"], "token"),
    "single-quoted-space": ("secret: 'one two three'", ["one", "two", "three"], "secret"),
    "aws": ("aws id AKIA" + "IOSFODNN7EXAMPLE here", ["IOSFODNN7EXAMPLE"], "AKIA"),
    "aws-secret": ("aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCY", ["wJalrXUtnFEMI"], "aws_secret_access_key"),
    "gcp-json": ('{"type": "service_account", "private_key": "' + PEM.replace("\n", "\\n") + '", "x": 1}',
                 ["MIIEvQIB", "ZZtopsecretbody123", "BEGIN PRIVATE"], "private_key"),
    "gcp-json-escaped": ('textPayload: {\\"private_key\\": \\"-----BEGIN PRIVATE KEY-----\\nMIIEescaped\\n\\"}',
                         ["MIIEescaped", "BEGIN PRIVATE"], "private_key"),
    "pem-multiline": ("before\n" + PEM + "\nafter", ["MIIEvQIB", "ZZtopsecretbody123", "BEGIN PRIVATE"], "after"),
    "pem-with-key": ("private_key=" + PEM, ["MIIEvQIB", "ZZtopsecretbody123"], "private_key"),
    "jwt": ("id=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.sigPart_123",
            ["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiJ1c2VyIn0", "sigPart_123"], "id="),
    "google-key": ("maps AIza" + "SyA1234567890abcdefghijklmnopqrstu", ["SyA1234567890abcdefghijklmnopqrstu"], "AIza"),
    "slack": ("hook xoxb-" + "123456789012-abcdefABCDEF", ["123456789012-abcdefABCDEF"], "xoxb-"),
    "generic-api-key-eq": ("ApiKey=zzTopSecret11", ["zzTopSecret11"], "ApiKey"),
    "generic-api-dash": ("x-api-key: zzTopSecret12", ["zzTopSecret12"], "x-api-key"),
    "generic-secret-json": ('{"Client_Secret": "zzTopSecret13"}', ["zzTopSecret13"], "Client_Secret"),
    "generic-token-colon": ("TOKEN: zzTopSecret14", ["zzTopSecret14"], "TOKEN"),
    "session-eq": ("SESSION_ID=zzTopSecret15", ["zzTopSecret15"], "SESSION_ID"),
    "session-json": ('{"session": "zzTopSecret16"}', ["zzTopSecret16"], "session"),
    "cookie": ("Cookie: sid=zzTopSecret17; theme=dark", ["zzTopSecret17", "theme=dark"], "Cookie"),
    "set-cookie": ("Set-Cookie: sid=zzTopSecret18; HttpOnly; Path=/", ["zzTopSecret18"], "Set-Cookie"),
    "cookie-json": ('{"cookie": "sid=zzTopSecret19; a=b"}', ["zzTopSecret19"], "cookie"),
}


@needs_bash
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_redaction_shapes(name):
    line, secrets, keep = SHAPES[name]
    out = redact_text(line + "\n")
    for s in secrets:
        assert s not in out, out
    assert keep in out and "redacted" in out, out


@needs_bash
def test_redaction_leaves_ordinary_log_lines_alone():
    text = ("bash: /opt/venv/bin/python: Permission denied\n"
            "uid=10001(app) gid=10001(app) groups=10001(app)\n"
            "readlink -f: /opt/uv-python/cpython-3.12.4-linux-x86_64/bin/python3.12\n"
            "-rwxr-xr-x 1 root root 1234 Oct 16 /opt/venv/bin/python\n"
            "Python 3.12.4 uvicorn 0.30.1 pydantic 2.8.2\n"
            "State: ExitCode=126 OOMKilled=false Error= Status=exited\n"
            "READINESS: NOT READY after 240s (limit 240s)\n"
            "PORT=8000\nPREFLIGHT FAIL: cannot exec /opt/venv/bin/python\n"
            "gcsfuse: failed to mount gs://bucket: permission denied\n")
    assert redact_text(text) == text


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
