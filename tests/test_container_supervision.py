"""Synthetic service lifecycle and runtime ownership checks; no Docker/browser needed."""

import importlib.util
import re
import signal
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("container_supervise", ROOT / "docker/supervise.py")
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


@pytest.fixture
def children(monkeypatch):
    launched = []
    original = subprocess.Popen

    def launch(*args, **kwargs):
        child = original(*args, **kwargs)
        launched.append(child)
        return child

    monkeypatch.setattr(supervisor.subprocess, "Popen", launch)
    yield launched
    for child in launched:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=3)


def sleeper():
    return [sys.executable, "-c", "import time; time.sleep(5)"]


@pytest.mark.parametrize("status", [0, 7])
def test_any_exit_fails_stack_and_reaps_other_services(children, status):
    exiting = [sys.executable, "-c", f"import time; time.sleep(.1); raise SystemExit({status})"]
    assert supervisor.run_stack([("", sleeper()), ("", exiting)], grace=.1) == 1
    assert len(children) == 2 and all(child.returncode is not None for child in children)


def test_readiness_timeout_stops_stack_before_dependent_service(children, monkeypatch):
    monkeypatch.setattr(supervisor, "endpoint_ready", lambda _: False)
    assert supervisor.run_stack([("tcp:1", sleeper()), ("", sleeper())],
                                timeout=.1, grace=.1) == 1
    assert len(children) == 1 and children[0].returncode is not None


def test_signal_during_startup_drains_children_and_restores_handler(children, monkeypatch):
    previous = signal.getsignal(signal.SIGTERM)

    def request_stop(_):
        signal.raise_signal(signal.SIGTERM)
        return False

    monkeypatch.setattr(supervisor, "endpoint_ready", request_stop)
    assert supervisor.run_stack([("tcp:1", sleeper())], grace=.1) == 128 + signal.SIGTERM
    assert children[0].returncode is not None
    assert signal.getsignal(signal.SIGTERM) == previous


def test_failed_spawn_cleans_started_services_without_logging_command(children, capsys):
    services = [("", sleeper()), ("", ["unavailable-container-canary-value"])]
    assert supervisor.run_stack(services, grace=.1) == 1
    assert children[0].returncode is not None
    assert "unavailable-container-canary-value" not in capsys.readouterr().err


def test_readiness_requires_a_real_listener():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        endpoint = f"tcp:{listener.getsockname()[1]}"
        assert supervisor.endpoint_ready(endpoint) is False
        listener.listen()
        assert supervisor.endpoint_ready(endpoint) is True
    assert supervisor.endpoint_ready(endpoint) is False


def test_posix_cleanup_signals_groups_even_after_leader_exits(monkeypatch):
    calls = []
    monkeypatch.setattr(supervisor, "os", SimpleNamespace(
        name="posix", killpg=lambda *args: calls.append(args)))
    child = type("ExitedChild", (), {"pid": 12345, "returncode": 0})()
    supervisor.signal_children([child], signal.SIGTERM)
    assert calls == [(12345, signal.SIGTERM)]


def test_image_runs_unprivileged_with_frozen_environment_outside_source():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER 10001:10001" in dockerfile
    assert "UV_PROJECT_ENVIRONMENT=/opt/venv" in dockerfile
    assert "UV_NO_SYNC=1" in dockerfile and "PYTHONDONTWRITEBYTECODE=1" in dockerfile
    assert "build-essential" in dockerfile
    entrypoint = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")
    assert "exec /opt/venv/bin/python /app/docker/supervise.py" in entrypoint
    assert "--no-access-log" in entrypoint and "chown" not in entrypoint


def test_posix_reaper_preserves_exit_status_and_collects_orphans(monkeypatch):
    statuses = iter([(999, 0), (12345, 7 << 8), (0, 0)])
    monkeypatch.setattr(supervisor, "os", SimpleNamespace(
        name="posix", waitpid=lambda *_: next(statuses), WNOHANG=1,
        waitstatus_to_exitcode=lambda status: status >> 8))
    child = type("Child", (), {"pid": 12345, "returncode": None})()
    supervisor.reap_children([child])
    assert child.returncode == 7
    assert next(statuses, None) is None


def test_cleanup_escalates_to_kill_and_waits_for_children(monkeypatch):
    calls = []
    child = type("Child", (), {"wait": lambda _: calls.append("wait")})()
    monkeypatch.setattr(supervisor, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(supervisor.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(supervisor, "signal_children", lambda _, sig: calls.append(sig))
    monkeypatch.setattr(supervisor, "reap_children", lambda _: calls.append("reap"))
    supervisor.stop_children([child], grace=0)
    assert calls == [signal.SIGTERM, 9, "wait", "reap"]


def test_deploy_is_self_diagnosing_and_honours_cloud_run_port():
    entrypoint = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")
    assert "${PORT:-8000}" in entrypoint and "--port ${APP_PORT}" in entrypoint
    assert "PREFLIGHT FAIL" in entrypoint and "exit 126" in entrypoint
    assert entrypoint.index("PREFLIGHT FAIL") < entrypoint.index("exec ")
    assert "\r" not in entrypoint
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "UV_PYTHON_PREFERENCE=only-managed" in dockerfile
    assert "UV_PYTHON_DOWNLOADS=manual" in dockerfile
    lines = dockerfile.splitlines()
    users = [(n, ln.split()[1]) for n, ln in enumerate(lines) if ln.startswith("USER ")]
    assert users and users[-1][1] not in ("root", "0", "0:0"), "final USER must be non-root"
    first_nonroot = next(n for n, u in users if u not in ("root", "0", "0:0"))
    after_user = "\n".join(lines[first_nonroot:])
    assert re.search(r"import [^\"\n]*\bautotester\b", after_user), "no non-root import"
    assert "readlink -f /opt/venv/bin/python" in after_user
    assert "ENTRYPOINT" in dockerfile
    body = re.findall(r"^\s*'(.*)' \\\r?$", dockerfile, re.M)
    assert body and body[-1].strip() in ('exec "$@"', "exec /entrypoint.sh"), "wrapper must exec"
