"""TA1: the rig is honest (CRITICAL egress half). Closed seam set, the real app, auth ON, an
egress guard that can fire."""

from __future__ import annotations

import ast
import os
import socket
from pathlib import Path

import pytest

import autotester.ui.app as app_module
from autotester.ui.app import app

HERE = Path(__file__).parent
# The only callables a scenario may replace: the named seams (contract "Seams").
CLOSED_SEAMS = (
    "autotester.ui.routes_intake.drive_factory",        # DriveClient / gws runner
    "autotester.ui.routes_runs.for_role",               # the model Provider (judge)
    "autotester.ui.run_execution.run_and_grade_case_resilient",   # browser+grader on the stub
    "autotester.browser.session.BrowserSession",        # no real browser (CPU)
    "autotester.auth.passwords._HASHER",                # cheap hasher, same algorithm
    "autotester.ui.run_queue._QUEUE",                   # the queue's worker spawner (held jobs)
)


def _setattr_targets(tree: ast.AST) -> list[str]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "setattr":
            first = node.args[0] if node.args else None
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                out.append(first.value)
    return out


def test_a_no_scenario_patches_an_autotester_callable_outside_the_seams() -> None:
    offenders = []
    for path in sorted(HERE.glob("*.py")):
        for target in _setattr_targets(ast.parse(path.read_text(encoding="utf-8"))):
            if target.startswith("autotester.") and target not in CLOSED_SEAMS:
                offenders.append(f"{path.name}: {target}")
    assert offenders == [], offenders


def test_b_the_app_under_test_is_the_real_one_not_a_rebuild() -> None:
    assert app is app_module.app and app_module.__name__ == "autotester.ui.app"
    tree = ast.parse((HERE / "rig.py").read_text(encoding="utf-8"))
    built = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "id", getattr(n.func, "attr", "")) == "FastAPI"]
    assert built == []


def test_c_auth_is_on_and_the_gate_refuses_an_anonymous_visitor(cold) -> None:
    assert "AUTOTESTER_AUTH_DISABLED" not in os.environ
    resp = cold.anonymous().get("/", headers={"accept": "text/html"})
    assert resp.status_code == 302 and resp.headers["location"].startswith("/auth/login")


def test_d_setup_writes_files_only_for_the_stub_page_and_the_stub_dir() -> None:
    """The rig's own direct file writes are outside the data root; everything inside it comes
    from the app's routes or the repo's account/store functions."""
    tree = ast.parse((HERE / "rig.py").read_text(encoding="utf-8"))
    writers = {fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
               and any(getattr(c.func, "attr", "") in {"write_text", "write_bytes", "mkdir"}
                       for c in ast.walk(fn) if isinstance(c, ast.Call))}
    assert writers == {"set_stub", "build_world"}


def test_e_the_egress_guard_fires_and_logs_a_non_loopback_connect(cold) -> None:
    probe = socket.socket()
    try:
        with pytest.raises(OSError, match="egress guard"):
            probe.connect(("203.0.113.9", 443))
    finally:
        probe.close()
    assert cold.egress.blocked == ["203.0.113.9"]
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    peer = socket.socket()
    peer.connect(server.getsockname())           # loopback is allowed
    peer.close()
    server.close()
    assert cold.egress.blocked == ["203.0.113.9"] and "127.0.0.1" in cold.egress.attempts
