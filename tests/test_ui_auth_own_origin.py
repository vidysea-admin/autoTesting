"""AU20 second clause: "the server's own origin must be an allowed one; otherwise startup
raises". Startup and the request-time guard (AU18 origin, AU19 host) must agree: for every
configuration the test client asks the real app, from the Host and Origin a browser at the bind
would send, and startup raises exactly when no such request is served. The wildcard bind
(`0.0.0.0`, `::`) is HELD on `qa/gates/t204-au20-wildcard-bind.md` and keeps today's rule."""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, gate_on
from fastapi.testclient import TestClient

from autotester.auth.config import AuthConfigError, bind_host, check_startup
from autotester.ui.app import app

H = ["--host", "10.0.0.5"]
P = ["--port", "8443"]
V6 = ["--host", "2001:db8::5"]
INTRA = "intranet.example"

# (id, argv, UVICORN_PORT, hosts, origins, bracketed name, port, starts)
CASES = [
    ("repro1-bare-host-custom-port", H + P, "", "10.0.0.5", "", "10.0.0.5", "8443", False),
    ("repro2-bare-origin-custom-port", H + P, "", "", "https://10.0.0.5", "10.0.0.5", "8443",
     False),
    ("repro3-hosts-only-no-origin", H + P, "", "10.0.0.5:8443", "", "10.0.0.5", "8443", False),
    ("repro4-default-8000-bare-host", H, "", "10.0.0.5", "", "10.0.0.5", "8000", False),
    ("repro5-port80-hosts-only", [*H, "--port", "80"], "", "10.0.0.5", "", "10.0.0.5", "80",
     False),
    ("port-in-origin-https", H + P, "", "", "https://10.0.0.5:8443", "10.0.0.5", "8443", True),
    ("port-in-origin-http", H + P, "", "", "http://10.0.0.5:8443", "10.0.0.5", "8443", True),
    ("hosts-and-origin", H + P, "", "10.0.0.5:8443", "https://10.0.0.5:8443", "10.0.0.5",
     "8443", True),
    ("origin-with-slash-and-caps", H + P, "", "", "HTTPS://10.0.0.5:8443/", "10.0.0.5", "8443",
     True),
    ("default-8000-origin", H, "", "", "http://10.0.0.5:8000", "10.0.0.5", "8000", True),
    ("port80-http-origin", [*H, "--port", "80"], "", "", "http://10.0.0.5", "10.0.0.5", "80",
     True),
    ("port80-https-origin-no", [*H, "--port", "80"], "", "", "https://10.0.0.5", "10.0.0.5",
     "80", False),
    ("port443-https-origin", [*H, "--port", "443"], "", "", "https://10.0.0.5", "10.0.0.5",
     "443", True),
    ("port443-http-origin-no", [*H, "--port", "443"], "", "", "http://10.0.0.5", "10.0.0.5",
     "443", False),
    ("other-host-listed", H + P, "", "at.example", "https://at.example", "10.0.0.5", "8443",
     False),
    ("ipv6-bracketed", [*V6, "--port", "9000"], "", "[2001:db8::5]:9000",
     "https://[2001:db8::5]:9000", "[2001:db8::5]", "9000", True),
    ("ipv6-unbracketed-entry-no", [*V6, "--port", "9000"], "", "2001:db8::5:9000",
     "https://2001:db8::5:9000", "[2001:db8::5]", "9000", False),
    ("ipv6-default-https", [*V6, "--port", "443"], "", "", "https://[2001:db8::5]",
     "[2001:db8::5]", "443", True),
    ("hostname", ["--host", INTRA], "", "", f"http://{INTRA}:8000", INTRA, "8000", True),
    ("hostname-bind-uppercase", ["--host", "INTRANET.Example"], "", "", f"http://{INTRA}:8000",
     INTRA, "8000", True),
    ("hostname-trailing-dot-unlisted", ["--host", INTRA + "."], "", "", f"http://{INTRA}:8000",
     INTRA + ".", "8000", False),
    ("hostname-trailing-dot-listed", ["--host", INTRA + "."], "", "",
     f"http://{INTRA}.:8000", INTRA + ".", "8000", True),
    ("loopback-always-allowed", ["--host", "127.0.0.1", *P], "", "at.example", "", "127.0.0.1",
     "8443", True),
    ("loopback-v6", ["--host", "::1", *P], "", "at.example", "", "[::1]", "8443", True),
    ("loopback-range-not-special", ["--host", "127.0.0.2"], "", "at.example", "", "127.0.0.2",
     "8000", False),
    ("uvicorn-port-env", H, "8443", "", "https://10.0.0.5:8443", "10.0.0.5", "8443", True),
    ("uvicorn-port-env-wrong", H, "8443", "", "https://10.0.0.5:8000", "10.0.0.5", "8443",
     False),
    ("argv-port-beats-env", [*H, "--port=8443"], "9", "", "https://10.0.0.5:8443", "10.0.0.5",
     "8443", True),
    ("last-host-wins", ["--host", "10.9.9.9", "--host=10.0.0.5", *P], "", "",
     "https://10.0.0.5:8443", "10.0.0.5", "8443", True),
    ("first-host-is-not-the-bind", ["--host", "10.0.0.5", "--host", "10.9.9.9", *P], "", "",
     "https://10.0.0.5:8443", "10.9.9.9", "8443", False),
    ("last-port-wins", [*H, "--port", "1", "--port", "8443"], "", "", "https://10.0.0.5:8443",
     "10.0.0.5", "8443", True),
]


def _hosted(monkeypatch: pytest.MonkeyPatch, argv: list[str], hosts: str, origins: str,
            uvicorn_port: str = "") -> None:
    monkeypatch.setenv("AUTOTESTER_HOSTED", "1")
    monkeypatch.setenv("AUTOTESTER_FIRST_ADMIN_EMAIL", "boss@at.example")
    monkeypatch.setenv("AUTOTESTER_ALLOWED_HOSTS", hosts)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", origins)
    monkeypatch.setattr("sys.argv", ["uvicorn", *argv])
    if uvicorn_port:
        monkeypatch.setenv("UVICORN_PORT", uvicorn_port)
    else:
        monkeypatch.delenv("UVICORN_PORT", raising=False)


def _served(scheme: str, host_header: str) -> bool:
    """A browser at `scheme://host_header`: the login page loads and the login POST, which
    carries `Origin`, is not refused. Asks the real app, not a helper."""
    # starlette's TestClient cannot split an IPv6 netloc, so the Host is set as a header
    c = TestClient(app, base_url=f"{scheme}://testserver", follow_redirects=False,
                   headers={"host": host_header})
    page = c.get("/auth/login")
    posted = c.post("/auth/login", data={"email": ADMIN, "password": PASSWORD},
                    headers={"origin": f"{scheme}://{host_header}"})
    return page.status_code == 200 and posted.status_code == 303


def _browser_forms(name: str, port: str) -> list[tuple[str, str]]:
    """What a browser sends: the port is omitted only when it is the scheme's default."""
    return [(scheme, name if port == default else f"{name}:{port}")
            for scheme, default in (("http", "80"), ("https", "443"))]


@pytest.mark.parametrize(("argv", "uvicorn_port", "hosts", "origins", "name", "port", "starts"),
                         [pytest.param(*c[1:], id=c[0]) for c in CASES])
def test_au20_startup_agrees_with_the_request_time_guard(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str], uvicorn_port: str,
        hosts: str, origins: str, name: str, port: str, starts: bool) -> None:
    gate_on(tmp_path, monkeypatch)
    account(ADMIN)
    _hosted(monkeypatch, argv, hosts, origins, uvicorn_port)
    served = [_served(s, h) for s, h in _browser_forms(name, port)]
    assert any(served) == starts, (served, starts)
    if starts:
        check_startup()
    else:
        with pytest.raises(AuthConfigError, match="own origin"):
            check_startup()


@pytest.mark.parametrize(("hosts", "origins", "starts"), [
    ("*", "", False), (",", "", False), ("", "*", False), (" , * ", " ,", False),
    ("*,at.example", "", True), ("", "https://at.example", True),
])
def test_au20_at_least_one_means_a_parsed_entry_not_a_non_empty_string(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hosts: str, origins: str,
        starts: bool) -> None:
    """`*` is never a wildcard (the list parser drops it) so it cannot satisfy "set"."""
    gate_on(tmp_path, monkeypatch)
    _hosted(monkeypatch, [], hosts, origins)
    if starts:
        check_startup()
    else:
        with pytest.raises(AuthConfigError, match="needs"):
            check_startup()


@pytest.mark.parametrize("wildcard", ["0.0.0.0", "::", "*", ""])
def test_au20_wildcard_bind_is_held_and_keeps_todays_rule(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wildcard: str) -> None:
    """HELD on qa/gates/t204-au20-wildcard-bind.md: a wildcard bind needs a parsed, non-empty
    list and no own-origin check (none is defined there). The owner's answer replaces this."""
    gate_on(tmp_path, monkeypatch)
    _hosted(monkeypatch, ["--host", wildcard, "--port", "8000"], "at.example", "")
    check_startup()
    _hosted(monkeypatch, ["--host", wildcard], "*", "")
    with pytest.raises(AuthConfigError, match="needs"):
        check_startup()


def test_au20_the_last_host_option_is_the_bind(monkeypatch: pytest.MonkeyPatch) -> None:
    """uvicorn takes the last `--host`, in either spelling; `UVICORN_HOST` is the fallback."""
    monkeypatch.setenv("UVICORN_HOST", "10.1.1.1")
    monkeypatch.setattr("sys.argv", ["uvicorn"])
    assert bind_host() == "10.1.1.1"
    monkeypatch.setattr("sys.argv", ["uvicorn", "--host", "a", "--host=b", "--host", "c"])
    assert bind_host() == "c"
    monkeypatch.setattr("sys.argv", ["uvicorn", "--host", "a", "--host=b"])
    assert bind_host() == "b"
