"""T-203 local Windows host (hosting.md HO39-HO46): launcher bind/config logic, the task installer's
dry run, the public health endpoint. No server process except one short loopback smoke start."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from auth_harness import gate_on
from fastapi.testclient import TestClient

from autotester.ui.app import app

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SERVE = SCRIPTS / "serve_windows.ps1"
INSTALL = SCRIPTS / "install_windows_task.ps1"
PS = shutil.which("powershell")
needs_ps = pytest.mark.skipif(PS is None, reason="Windows PowerShell not available")


def _ps(script: Path, *args: str, env: dict[str, str] | None = None) -> str:
    import os
    out = subprocess.run([PS or "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", str(script), *args], capture_output=True, text=True,
                         timeout=60, check=True, env={**os.environ, **(env or {})})
    return out.stdout


def _plan(*args: str, env: dict[str, str] | None = None) -> dict[str, str]:
    lines = _ps(SERVE, "-DryRun", *args, env=env).strip().splitlines()
    return dict(line.split("=", 1) for line in lines)


@needs_ps
def test_default_bind_is_loopback_only() -> None:  # HO44
    plan = _plan(env={"AUTOTESTER_BIND_HOST": ""})
    assert plan["bind_host"] == "127.0.0.1"
    assert "--host 127.0.0.1" in plan["command"] and "--port 8000" in plan["command"]
    assert "0.0.0.0" not in plan["command"]


@needs_ps
def test_lan_is_one_switch_or_one_env_var() -> None:  # HO44
    assert _plan("-Lan")["bind_host"] == "0.0.0.0"
    assert _plan(env={"AUTOTESTER_BIND_HOST": "0.0.0.0"})["bind_host"] == "0.0.0.0"


@needs_ps
def test_data_root_is_outside_the_code_tree_and_logs_under_it(tmp_path: Path) -> None:  # HO42
    plan = _plan(env={"AUTOTESTER_ROOT": ""})
    repo = SCRIPTS.parent.resolve()
    assert repo not in Path(plan["data_root"]).resolve().parents
    custom = _plan("-DataRoot", str(tmp_path), "-Port", "9123")
    assert custom["data_root"] == str(tmp_path) and custom["log_dir"].startswith(str(tmp_path))
    assert "--port 9123" in custom["command"]


@needs_ps
def test_allowed_origins_default_and_override() -> None:
    default = _plan(env={"AUTOTESTER_ALLOWED_ORIGINS": ""})
    assert "http://127.0.0.1:8000" in default["allowed_origins"]
    got = _plan("-AllowedOrigins", "https://qa.example", env={"AUTOTESTER_ALLOWED_ORIGINS": ""})
    assert got["allowed_origins"] == "https://qa.example"


def test_launcher_never_sets_auth_disabled() -> None:  # HO41
    text = SERVE.read_text(encoding="utf-8")
    assert "env:AUTOTESTER_AUTH_DISABLED =" not in text
    assert "Remove-Item Env:AUTOTESTER_AUTH_DISABLED" in text


@needs_ps
def test_task_installer_whatif_registers_nothing() -> None:  # HO39, HO40
    out = _ps(INSTALL, "-WhatIf")
    assert "trigger=AtStartup" in out and "restart=5x/1min" in out
    assert "serve_windows.ps1" in out
    assert "registered" not in out
    text = INSTALL.read_text(encoding="utf-8")
    assert "Register-ScheduledTask" in text and "-RestartCount" in text
    assert "New-ScheduledTaskTrigger -AtStartup" in text


def test_healthz_is_public_and_leaks_nothing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # HO43
    gate_on(tmp_path, monkeypatch)  # T-204 gate ON: the unsigned-in caller gets only {"ok": true}
    res = TestClient(app).get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert "project" not in json.dumps(res.json()).lower()


def test_unauthenticated_project_route_is_refused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # HO41
    gate_on(tmp_path, monkeypatch)
    res = TestClient(app).get("/", follow_redirects=False)
    assert res.status_code in (401, 302)


def test_smoke_start_serves_healthz_on_loopback(tmp_path: Path) -> None:  # HO43, HO44
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    import os
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "autotester.ui.app:app", "--host", "127.0.0.1",
         "--port", str(port)], env={**os.environ, "AUTOTESTER_ROOT": str(tmp_path)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 60
        body = None
        while time.time() < deadline and body is None:
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2).read()
            except OSError:
                time.sleep(0.5)
        assert body is not None, "healthz never answered"
        assert json.loads(body) == {"ok": True}  # unsigned-in caller under the T-204 gate (AU16)
    finally:
        proc.kill()
        proc.wait(timeout=10)
