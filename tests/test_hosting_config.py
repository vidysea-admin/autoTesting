"""T-203 hosting seams: the data root moved to /data must not move the code, and the noVNC
viewer URL is configurable so an https server never embeds http://localhost:6080."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import autotester
from autotester.ui import routes_live
from autotester.ui.app import app


def test_healthz_watches_the_installed_package_not_the_data_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Server deploy: AUTOTESTER_ROOT=/data holds projects/, not src/ -- freshness must still
    read the code that is actually served."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    assert routes_live.package_root() == Path(autotester.__file__).resolve().parent
    assert any(routes_live.package_root().rglob("*.py"))


def test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere(
    tmp_path: Path,
) -> None:
    """AT-846/HO3: `_SRC_ROOT` is fixed at import, so a monkeypatched env in this process cannot
    prove it. A fresh interpreter started like the container (AUTOTESTER_ROOT=/data, no src there)
    must still watch the installed package; a `repo_root()/src/autotester` revert reports the
    data folder and goes red."""
    code = "from autotester.ui import routes_live as r; print(r._SRC_ROOT)"
    env = {**os.environ, "AUTOTESTER_ROOT": str(tmp_path)}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, cwd=tmp_path, timeout=60, check=True).stdout.strip()
    assert Path(out) == Path(autotester.__file__).resolve().parent


def test_live_view_defaults_to_the_local_novnc_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer running `docker compose up` on their laptop."""
    monkeypatch.delenv("AUTOTESTER_NOVNC_URL", raising=False)
    page = TestClient(app).get("/live").text
    assert "http://localhost:6080/vnc.html?autoconnect=true&amp;resize=scale" in page \
        or "http://localhost:6080/vnc.html?autoconnect=true&resize=scale" in page


def test_live_view_uses_the_operators_same_origin_url_on_a_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Behind the reverse proxy the page is https; an http iframe would be blocked as mixed
    content, so the operator points it at the proxied path."""
    monkeypatch.setenv("AUTOTESTER_NOVNC_URL",
                       "/novnc/vnc.html?autoconnect=true&path=novnc/websockify")
    page = TestClient(app).get("/live").text
    assert "src='/novnc/vnc.html?autoconnect=true&amp;path=novnc/websockify'" in page
    assert "localhost:6080" not in page


@pytest.mark.parametrize("hostile", ["javascript:alert(1)", "//evil.example/x",
                                     "http://evil.example/x'><script>"])
def test_a_hostile_viewer_url_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch, hostile: str
) -> None:
    """A mistyped or tampered server.env value must never put a foreign page in the iframe."""
    monkeypatch.setenv("AUTOTESTER_NOVNC_URL", hostile)
    page = TestClient(app).get("/live").text
    assert "evil.example" not in page and "javascript:" not in page
    assert "localhost:6080" in page


def test_entrypoint_script_is_lf_in_git_so_a_windows_checkout_still_runs_in_linux() -> None:
    """`.gitattributes` pins *.sh to LF: a CRLF shebang line makes /entrypoint.sh fail with
    'no such file or directory' in the Ubuntu container."""
    root = Path(__file__).resolve().parents[1]
    attrs = (root / ".gitattributes").read_text(encoding="utf-8")
    assert "*.sh text eol=lf" in attrs
