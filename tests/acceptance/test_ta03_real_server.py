"""TA3: the deployment under test is a real server process. Starts the same ASGI app the launcher
script serves (`uvicorn autotester.ui.app:app`, T-203) on a free loopback port over a fresh data
root with auth ON, and replays the core path over real HTTP with real Host and Origin headers.
The Test press inside the server process is xfail(run=False): it would start a real browser."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from auth_harness import PASSWORD

from autotester.auth import accounts, groups

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "serve_windows.ps1"
SCRUB = ("AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_TEST_NO_AUTO_LOGIN", "PYTEST_CURRENT_TEST",
         "AUTOTESTER_AUTH_DIR", "AUTOTESTER_HOSTED", "AUTOTESTER_FIRST_ADMIN_EMAIL")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Server:
    def __init__(self, port: int, root: Path) -> None:
        self.port, self.root = port, root
        self.base = f"http://127.0.0.1:{port}"
        self.origin = {"origin": self.base}

    def browser(self) -> httpx.Client:
        return httpx.Client(base_url=self.base, follow_redirects=False, timeout=20,
                            headers=self.origin)


@pytest.fixture
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Server]:
    port, root = free_port(), tmp_path / "data"
    root.mkdir()
    env = {k: v for k, v in os.environ.items() if k not in SCRUB}
    env |= {"AUTOTESTER_ROOT": str(root), "AUTOTESTER_ALLOWED_ORIGINS": f"http://127.0.0.1:{port}"}
    log = (tmp_path / "server.log").open("wb")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "autotester.ui.app:app", "--host", "127.0.0.1",
         "--port", str(port)], cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
    started = Server(port, root)
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                if httpx.get(started.base + "/healthz", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.3)
        else:
            pytest.fail("server did not answer /healthz")
        monkeypatch.setenv("AUTOTESTER_ROOT", str(root))        # in-process reads the same store
        yield started
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


def test_the_documented_start_command_serves_the_app_with_auth_on() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "autotester.ui.app:app" in text and "127.0.0.1" in text
    assert "AUTOTESTER_AUTH_DISABLED" in text and "Remove-Item Env:AUTOTESTER_AUTH_DISABLED" in text


def test_core_path_over_real_http_with_real_host_and_origin(server: Server) -> None:
    admin = server.browser()
    assert admin.get("/auth/login").status_code == 200
    anonymous = admin.get("/", headers={"accept": "text/html"})
    assert anonymous.status_code == 302 and anonymous.headers["location"].startswith("/auth/login")

    signup = admin.post("/auth/signup", data={"email": "admin@team.test", "password": PASSWORD})
    assert signup.status_code in (302, 303), signup.text[:300]
    login = admin.post("/auth/login", data={"email": "admin@team.test", "password": PASSWORD})
    assert login.status_code == 303 and admin.cookies
    made = admin.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "http://127.0.0.1:9",
        "allowed_domains": "127.0.0.1"})
    assert made.status_code in (200, 302, 303), made.text[:300]
    assert admin.get("/projects/demo").status_code == 200

    dev = server.browser()
    assert dev.post("/auth/signup", data={"email": "dev@team.test", "password": PASSWORD}
                    ).status_code in (302, 303)
    assert dev.post("/auth/login", data={"email": "dev@team.test", "password": PASSWORD}
                    ).status_code == 303
    waiting = dev.get("/projects/demo", headers={"accept": "text/html"})
    assert waiting.status_code in (302, 403, 404)                  # signed up, no group yet
    user = accounts.find_user("dev@team.test")
    seed = next(g.id for g in groups.list_groups() if g.seed == "developer")
    assert user is not None
    placed = admin.post(f"/admin/users/{user.id}/groups", data={"group_id": str(seed)})
    assert placed.status_code == 303
    assert dev.get("/", headers={"accept": "text/html"}).status_code == 200   # next click works


def test_a_foreign_host_and_a_foreign_origin_post_are_refused(server: Server) -> None:
    client = server.browser()
    foreign_host = client.get("/auth/login", headers={"host": "evil.example"})
    assert foreign_host.status_code in (400, 403, 421)
    foreign_origin = client.post("/auth/login", headers={"origin": "http://evil.example"},
                                 data={"email": "x@team.test", "password": "x"})
    assert foreign_origin.status_code == 403
    assert client.get("/auth/login").status_code == 200


@pytest.mark.xfail(run=False, strict=True, reason="blocked: a Test press inside the separate "
                   "server process would start a real browser; the press path is proved "
                   "in-process by TA6 and TA7 with the browser as a named seam")
def test_dev_presses_test_in_the_server_process_and_the_report_opens(server: Server) -> None:
    raise AssertionError("not run")
