"""Own check: KeyboardInterrupt / SystemExit raised inside the identity probe propagate out of
BrowserSession.start() AND the exposed browser is still closed and the port file removed.
Run with PYTHONPATH=<copy>/src:<copy>/tests and --rootdir <copy>."""
import threading, time
import pytest
from test_browser_session_cdp import FakeDevTools, install, session, refuses_connections
from autotester.browser import launch


@pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit])
def test_interrupt_in_probe_propagates_and_cleans_up(tmp_path, monkeypatch, exc):
    dev = FakeDevTools()
    install(monkeypatch, devtools=dev)
    real = launch._fetch_version
    def boom(port):
        # open the real socket path first so the watchdog thread exists, then interrupt mid-read
        import socket
        raise_after = exc()
        raise raise_after
    monkeypatch.setattr(launch, "_fetch_version", boom)
    s = session(tmp_path, expose_cdp=True)
    with pytest.raises(exc):
        s.start()
    assert s.cdp_url is None
    assert refuses_connections(dev.port)
    assert not (s.paths.profile_dir / launch.PORT_FILE).exists()


@pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit])
def test_interrupt_inside_real_read_cancels_watchdog(tmp_path, monkeypatch, exc):
    """Interrupt raised from inside http.client's read (watchdog thread already running)."""
    import http.client
    dev = FakeDevTools()
    install(monkeypatch, devtools=dev)
    before = {t.ident for t in threading.enumerate()}
    def bad_read1(self, *a, **k):
        raise exc()
    monkeypatch.setattr(http.client.HTTPResponse, "read1", bad_read1)
    s = session(tmp_path, expose_cdp=True)
    with pytest.raises(exc):
        s.start()
    time.sleep(0.2)
    leftovers = [t for t in threading.enumerate() if t.ident not in before and isinstance(t, threading.Timer)]
    assert not leftovers, leftovers
    assert s.cdp_url is None and refuses_connections(dev.port)
    assert not (s.paths.profile_dir / launch.PORT_FILE).exists()
