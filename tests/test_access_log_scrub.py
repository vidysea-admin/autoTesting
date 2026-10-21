"""AT-1390 / AU22: the uvicorn access log D-107 keeps on never records a query string or a
`/v/<token>` path token. Real uvicorn serves the real app on a loopback socket; caplog reads it."""

from __future__ import annotations

import logging
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import uvicorn
from auth_harness import gate_on

from autotester.ui import app as ui_app
from autotester.ui.access_log_scrub import AccessLogScrub, install_access_log_scrub, scrub_target


@pytest.fixture
def served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """The real app under a real uvicorn with its access log on (as the entrypoint runs it)."""
    gate_on(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", "127.0.0.1")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(ui_app.app, log_config=None, access_log=True,
                                           lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started
    yield f"http://127.0.0.1:{sock.getsockname()[1]}"
    server.should_exit = True
    thread.join(timeout=10)
    sock.close()


def _access_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "uvicorn.access"]


def test_a_login_next_query_and_a_share_link_token_never_reach_the_access_log(
        served: str, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="uvicorn.access")
    with httpx.Client(follow_redirects=False) as http:
        login = http.get(f"{served}/auth/login?next=/x")
        share = http.get(f"{served}/v/abc123")
    assert login.status_code and share.status_code
    lines = _access_lines(caplog)
    text = "\n".join(lines)
    assert "next=/x" not in text and "abc123" not in text
    assert any('"GET /auth/login?<redacted> HTTP/1.1"' in ln for ln in lines), lines
    assert any(f'"GET /v/<redacted> HTTP/1.1" {share.status_code}' in ln for ln in lines), lines


def test_scrub_keeps_method_status_and_the_rest_of_the_path_readable() -> None:
    assert scrub_target("/projects/p1/runs") == "/projects/p1/runs"
    assert scrub_target("/v/tok_en-1/request-access") == "/v/<redacted>/request-access"
    assert scrub_target("/a?token=zzz&b=1") == "/a?<redacted>"
    assert scrub_target("/v/abc?x=1") == "/v/<redacted>?<redacted>"


def test_install_is_idempotent_so_a_second_import_adds_no_copy() -> None:
    install_access_log_scrub()
    install_access_log_scrub()
    copies = [f for f in logging.getLogger("uvicorn.access").filters
              if isinstance(f, AccessLogScrub)]
    assert len(copies) == 1
