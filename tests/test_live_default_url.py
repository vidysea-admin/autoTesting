"""E6.6 (the viewer URL default on Cloud Run) and E6.8 (the seam is loopback-only)."""

from __future__ import annotations

import inspect
import re

import pytest

from autotester.ui import routes_auth, routes_live

_LOCAL = "http://localhost:6080/vnc.html?autoconnect=true&resize=scale"
_CLOUD = "/novnc/vnc.html?autoconnect=true&resize=scale&path=novnc/websockify"


@pytest.fixture(autouse=True)
def clean(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("K_SERVICE", routes_live.NOVNC_ENV, "AUTOTESTER_HOSTED"):
        monkeypatch.delenv(name, raising=False)


def test_default_is_unchanged_off_cloud_run() -> None:
    assert routes_live.novnc_url() == _LOCAL


def test_cloud_run_default_is_the_same_origin_path(monkeypatch) -> None:
    monkeypatch.setenv("K_SERVICE", "autotester")
    assert routes_live.novnc_url() == _CLOUD
    assert routes_live.viewer_url(True) == _CLOUD
    view = routes_live.viewer_url(False)
    assert view.startswith("/novnc-view/") and "path=novnc-view/websockify" in view
    assert view.endswith("view_only=1")


def test_blank_override_counts_as_unset(monkeypatch) -> None:
    monkeypatch.setenv("K_SERVICE", "x")
    monkeypatch.setenv(routes_live.NOVNC_ENV, "   ")
    assert routes_live.novnc_url() == _CLOUD


def test_explicit_override_still_wins_and_hostile_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("K_SERVICE", "x")
    monkeypatch.setenv(routes_live.NOVNC_ENV, "http://localhost:6080/x")
    assert routes_live.novnc_url() == "http://localhost:6080/x"
    monkeypatch.setenv(routes_live.NOVNC_ENV, "https://evil.example/'><script>")
    assert routes_live.novnc_url() == _CLOUD


def test_hosted_alone_does_not_switch_the_default(monkeypatch) -> None:
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    assert routes_live.novnc_url() == _LOCAL


def test_live_page_on_cloud_run_never_mentions_localhost(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from autotester.ui.app import app
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setenv("K_SERVICE", "x")
    body = TestClient(app).get("/live").text
    assert "localhost" not in body and "src='/novnc" in body


def test_production_upstreams_are_the_two_loopback_ports() -> None:
    assert routes_live.VNC_UPSTREAMS == {"/novnc": ("127.0.0.1", 6080),
                                         "/novnc-view": ("127.0.0.1", 6081)}


def test_one_function_holds_the_need_decision() -> None:
    """E6.3 / C3: the `need` decision is written once, in routes_auth, and routes_live calls it."""
    assert len(re.findall(r'need not in \("view", "control"\)',
                          inspect.getsource(routes_auth))) == 1
    assert "need not in" not in inspect.getsource(routes_live)
    assert "live_access_refusal" in inspect.getsource(routes_live)


@pytest.mark.parametrize("value,expected", [(None, False), ("", False), ("  ", False),
                                            ("autotester", True)])
def test_on_cloud_run_reads_k_service_and_blank_is_unset(monkeypatch, value, expected) -> None:
    from autotester.core.env import on_cloud_run
    if value is not None:
        monkeypatch.setenv("K_SERVICE", value)
    assert on_cloud_run() is expected
