"""Redaction layers of scripts/container_diagnose.sh: name layer shapes, value layer, python layer,
fail-safe mode, PEM handling, performance, and that DIAGNOSIS signatures survive.

No docker. All shapes go through ONE bash call (bash start-up is slow on Windows); each case is
then a parametrized assertion: the secret is gone AND the key name survives."""
# ruff: noqa: E501  (the CASES table keeps one secret shape per line)

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from autotester.core.redact_cli import mask_stream

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/container_diagnose.sh"
BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(BASH is None, reason="bash not installed")
S = "S3CR3T"
PEM = ("-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7\nZZtopsecretbody1234567890abcdefghijklmnopqrstuvwxyz\n"
       "-----END PRIVATE KEY-----")
BODY = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7"
GH = "a1B2c3D4e5F6g7H8i9J0k1L2m3"


def run_redact(text, extra="", env=None, timeout=300):
    cmd = f'source "{SCRIPT.as_posix()}"; {extra} redact'
    e = {**os.environ, "REDACT_NO_PYTHON": "1", **(env or {})}
    r = subprocess.run([BASH, "-c", cmd], input=text, capture_output=True, text=True, check=True, env=e, timeout=timeout)
    return r.stdout


# name -> (input, secrets that must vanish, text that must survive: the key name)
CASES = {
    "url-userinfo": ("pull https://deploy:Sup3rPw@git.example.com/r.git", ["Sup3rPw"], "git.example.com"),
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
    "flag-short-p": (f"mysql -p {S}abc -u root", [S], "-p"),
    "pw-suffix": (f"PATHLYNKS_PW={S}", [S], "PATHLYNKS_PW"),
    "login-pw": (f"PATHLYNKS_LOGIN_PW={S}", [S], "PATHLYNKS_LOGIN_PW"),
    "pass-suffix": (f"DB_PASS={S}", [S], "DB_PASS"),
    "pass-bare": (f"pass={S}", [S], "pass"),
    "pw-bare": (f"pw={S}", [S], "pw"),
    "camel-case-key": (f"clientKey={S}", [S], "clientKey"),
    "ghp": ("GITHUB_TOKEN=ghp_" + GH, [GH], "GITHUB_TOKEN"),
    "gho": ("cloned with gho_" + GH, [GH], "gho_"),
    "ghs": ("ghs_" + GH + " end", [GH], "ghs_"),
    "github-pat": ("x github_pat_11ABCDEFG0abcdefghij_klmnopqrstuv", ["11ABCDEFG0abcdefghij"], "github_pat_"),
    "quoted-space": ('token = "alpha beta gamma"', ["alpha", "beta", "gamma"], "token"),
    "single-quoted-space": ("secret: 'one two three'", ["one", "two", "three"], "secret"),
    "dq-escaped-quote": (f'{{"password":"a\\"{S}"}}', [S], "password"),
    "dq-escaped-quote-tail": (f'{{"password": "{S} \\"quoted\\" tail"}}', [S, "tail"], "password"),
    "json-escaped-whole": (f'textPayload: {{\\"password\\": \\"{S}\\"}}', [S], "password"),
    "arrow": (f'password => "{S}"', [S], "password"),
    "arrow-bare": (f"password=>{S}", [S], "password"),
    "xml-tag": (f"<password>{S}</password>", [S], "</password>"),
    "url-encoded-eq": (f"POST body password%3D{S}", [S], "password"),
    "url-encoded-json": (f"password%22%3A%22{S}", [S], "password"),
    "oauth-code": (f"https://h/cb?code={S}abc&state=1", [S], "state=1"),
    "oauth-code-json": (f'{{"code":"{S}abc"}}', [S], '"code"'),
    "token-space": (f"token {S}abc", [S], "token"),
    "token-is": (f"the token is {S}abc", [S], "the token is"),
    "env-name-space": (f"GEMINI_API_KEY {S}abc", [S], "GEMINI_API_KEY"),
    "aws": ("aws id AKIAIOSFODNN7EXAMPLE here", ["IOSFODNN7EXAMPLE"], "AKIA"),
    "aws-secret": ("aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCY", ["wJalrXUtnFEMI"], "aws_secret_access_key"),
    "gcp-json": ('{"type": "service_account", "private_key": "' + PEM.replace("\n", "\\n") + '", "x": 1}',
                 ["MIIEvQIB", "ZZtopsecretbody123", "BEGIN PRIVATE"], "private_key"),
    "gcp-json-escaped": ('textPayload: {\\"private_key\\": \\"-----BEGIN PRIVATE KEY-----\\nMIIEescaped\\n\\"}',
                         ["MIIEescaped", "BEGIN PRIVATE"], "private_key"),
    "pem-multiline": ("before\n" + PEM + "\nafter", [BODY, "ZZtopsecretbody123"], "after"),
    "pem-with-key": ("private_key=" + PEM, [BODY, "ZZtopsecretbody123"], "private_key"),
    "pem-unterminated": ("-----BEGIN RSA PRIVATE KEY-----\n" + BODY + "\n" + BODY + "\n== 8 NEXT SECTION\nREADINESS: NOT READY", [BODY], "== 8 NEXT SECTION"),
    "jwt": ("id=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.sigPart_123", ["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiJ1c2VyIn0", "sigPart_123"], "id="),
    "google-key": ("maps AIzaSyA1234567890abcdefghijklmnopqrstu", ["SyA1234567890abcdefghijklmnopqrstu"], "AIza"),
    "slack": ("hook xoxb-123456789012-abcdefABCDEF", ["123456789012-abcdefABCDEF"], "xoxb-"),
    "sk-key": ("sk-proj-S3CR3TAAAAAAAAAAAAAAAA", [S], "sk-"),
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
MARK = "@@END {}@@"


@pytest.fixture(scope="module")
def results():
    if BASH is None:
        return {}
    text = "".join(f"{line}\n{MARK.format(name)}\n" for name, (line, _, _) in CASES.items())
    out, res, cur = run_redact(text), {}, []
    for ln in out.split("\n"):
        if ln.startswith("@@END "):
            res[ln[6:-2]] = "\n".join(cur)
            cur = []
        else:
            cur.append(ln)
    return res


@needs_bash
@pytest.mark.parametrize("name", sorted(CASES))
def test_name_layer_shapes(results, name):
    _, secrets, keep = CASES[name]
    out = results[name]
    for s in secrets:
        assert s not in out, out
    assert keep in out and "redacted" in out, out


@needs_bash
def test_ordinary_log_lines_are_not_mangled():
    text = ("bash: /opt/venv/bin/python: Permission denied\nuid=10001(app) gid=10001(app) groups=10001(app)\n"
            "readlink -f: /opt/uv-python/cpython-3.12.4-linux-x86_64/bin/python3.12\n"
            "-rwxr-xr-x 1 root root 1234 Oct 16 /opt/venv/bin/python\nPython 3.12.4 uvicorn 0.30.1 pydantic 2.8.2\n"
            "State: ExitCode=126 OOMKilled=false Error= Status=exited\nexit code 126\n"
            "READINESS: NOT READY after 240s (limit 240s)\nPORT=8000\nPREFLIGHT FAIL: cannot exec /opt/venv/bin/python\n"
            "gcsfuse: failed to mount gs://bucket: permission denied\nauthor: bob\nkeyboard: us\nkeys=3\nsession started\n"
            "/app/src/autotester/session.py and keyboard.py\ndocker run -d -p 8000:8000 image\nmkdir -p /app/.work\n")
    assert run_redact(text) == text


@needs_bash
def test_value_layer_masks_a_value_under_an_unusual_key_name(tmp_path):
    extra = f'_REDACT_VALUES="{tmp_path.as_posix()}/values"; : >"$_REDACT_VALUES"; printf "%s\\n" "Zq9xLongValue77" "abc" "true" "localhost" "8000" "/opt/venv/bin" "wEiRdSeCrEt=x1" | _redact_load;'
    text = "weird_name_xyz: Zq9xLongValue77 and raw Zq9xLongValue77\nshort abc true localhost 8000 /opt/venv/bin ok\n"
    out = run_redact(text, extra)
    assert "Zq9xLongValue77" not in out and "weird_name_xyz" in out and out.count("<redacted>") >= 2, out
    assert "short abc true localhost 8000 /opt/venv/bin ok" in out  # short and common values are not masked


@needs_bash
def test_value_layer_loads_env_and_secrets_file_forms(tmp_path):
    envf = tmp_path / "x.env"
    envf.write_text("# c\nexport MY_ODD='quoted odd value 99'\nBARE_LINE_VALUE_5\nPLAIN=plainvalue42\n", encoding="utf-8")
    extra = f'_REDACT_VALUES="{tmp_path.as_posix()}/values"; : >"$_REDACT_VALUES"; _redact_assignments <"{envf.as_posix()}" | _redact_load;'
    out = run_redact("a quoted odd value 99 b BARE_LINE_VALUE_5 c plainvalue42 d MY_ODD\n", extra)
    assert "odd value 99" not in out and "BARE_LINE_VALUE_5" not in out and "plainvalue42" not in out and "MY_ODD" in out, out


def test_python_layer_masks_value_and_its_encodings():
    secret, enc = "Zq9x/Long+Value77", "Zq9x%2FLong%2BValue77"
    out = mask_stream(f"a {secret} b {enc} c", [secret])
    assert secret not in out and enc not in out and out.count("<redacted>") == 2


@needs_bash
def test_python_layer_is_used_by_the_script(tmp_path):
    secret, enc = "Zq9x/Long+Value77", "Zq9x%2FLong%2BValue77"
    extra = f'_REDACT_VALUES="{tmp_path.as_posix()}/values"; : >"$_REDACT_VALUES"; echo {secret} | _redact_load;'
    out = run_redact(f"a {enc} b\n", extra, env={"REDACT_NO_PYTHON": "", "AUTOTESTER_PYTHON": Path(sys.executable).as_posix(),
                                                "PYTHONIOENCODING": "utf-8"})
    assert enc not in out and "<redacted>" in out, out


@needs_bash
def test_fail_safe_when_sed_is_not_gnu(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "sed").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8", newline="\n")
    (fake / "sed").chmod(0o755)
    text = ("== 5 PERMISSION CHECK\ncustom_name: hunter2value\nplain unknown line with hunter3value\n"
            "bash: /opt/venv/bin/python: Permission denied\nREADINESS: NOT READY after 1s\nCan't see this: token=abc\n")
    cmd = f'export PATH="$(cd "{fake.as_posix()}" && pwd):$PATH"; source "{SCRIPT.as_posix()}"; redact'
    r = subprocess.run([BASH, "-c", cmd], input=text, capture_output=True, text=True, check=True,
                       env=dict(os.environ, REDACT_NO_PYTHON="1"), timeout=120)
    assert "hunter2value" not in r.stdout and "hunter3value" not in r.stdout and "token=abc" not in r.stdout
    assert "== 5 PERMISSION CHECK" in r.stdout and "Permission denied" in r.stdout and "READINESS: NOT READY" in r.stdout
    assert "withheld" in r.stdout and "not GNU" in r.stdout


@needs_bash
def test_diagnosis_signatures_survive_redaction(tmp_path):
    log = ("bash: /opt/venv/bin/python: Permission denied\nState: ExitCode=126 OOMKilled=true Error=\n"
           "PREFLIGHT FAIL: cannot exec /opt/venv/bin/python\n  uid=10001 gid=10001\n  readlink -f: /root/.local/bin/python3.12\n"
           "READINESS: NOT READY after 240s (limit 240s)\nAddress already in use\ngcsfuse: failed to mount gs://b: permission denied\n"
           "Xvfb failed to start\nexec /entrypoint.sh: exec format error\n/usr/bin/env: 'bash': bad interpreter\n/app/.env is absent\n"
           "PermissionError: [Errno 13] Permission denied: '/app/.work'\n")
    f = tmp_path / "raw.log"
    f.write_bytes(log.encode())
    cmd = (f'source "{SCRIPT.as_posix()}"; diagnose "{f.as_posix()}" >"{tmp_path.as_posix()}/a.txt"; '
           f'redact <"{f.as_posix()}" >"{tmp_path.as_posix()}/r.log"; diagnose "{tmp_path.as_posix()}/r.log" >"{tmp_path.as_posix()}/b.txt"; true')
    subprocess.run([BASH, "-c", cmd], check=True, env=dict(os.environ, REDACT_NO_PYTHON="1"), timeout=300)
    a, b = (tmp_path / "a.txt").read_text(), (tmp_path / "b.txt").read_text()
    assert a == b and a.count("[FAIL]") >= 8


@needs_bash
def test_performance_300kb_log_under_10_seconds(tmp_path):
    """Times only the redact pass (bash start-up excluded): one sed pass, no per-line loop."""
    normal = ("2026-10-16T10:11:12Z INFO request handled path=/api/runs status=200 ms=12 user=anon\n"
              "uid=10001 gid=10001 readlink -f /opt/venv/bin/python Permission denied\n"
              "DB_PASSWORD=" + S + " token: " + S + " Authorization: Bearer " + S + " cookie=a=b\n")
    text = normal * 1200 + "x" * 60000 + "\n" + "key=" * 15000 + "\n" + ("a_b-" * 5000) + "\n"
    assert len(text.encode()) >= 300_000
    src, dst, secs = tmp_path / "in.log", tmp_path / "out.log", tmp_path / "secs.txt"
    src.write_text(text, encoding="utf-8", newline="\n")
    cmd = (f'source "{SCRIPT.as_posix()}"; SECONDS=0; redact <"{src.as_posix()}" >"{dst.as_posix()}"; '
           f'echo $SECONDS >"{secs.as_posix()}"')
    subprocess.run([BASH, "-c", cmd], check=True, env={**os.environ, "REDACT_NO_PYTHON": "1"}, timeout=600)
    assert S not in dst.read_text(encoding="utf-8")
    elapsed = int(secs.read_text().strip())
    assert elapsed < 10, f"redact took {elapsed}s for 300 KB"
