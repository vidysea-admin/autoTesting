"""Playwright launch options for one project's persistent browser context.

Moved out of `session.py` at B1 (D-015) — `session.py` was at its 300-line
cap and this function is self-contained. Behaviour unchanged; imported back
into `session.py` so nothing else needs to know it moved.
"""

from __future__ import annotations

import contextlib
import errno
import http.client
import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project

DEFAULT_VIEWPORT = {"width": 1366, "height": 850}
"""The desktop viewport every context launches with. `browser/conditions.py` reads this
to reset a VIEWPORT_MOBILE case back to default afterwards (D-045/AT-581)."""

RECORD_VIDEO_SIZE = {"width": 640, "height": 400}
"""T-191 plan-decision 2: scaled well below `DEFAULT_VIEWPORT` (same ~1.6:1
aspect ratio) so a 15-20 minute recording stays a manageable size. Applied
only when a caller opts in via `record_video_dir` below -- this constant is
never read unless recording is on."""


CDP_HOST = "127.0.0.1"
"""The only interface a Chrome DevTools endpoint is ever bound to (D-075, T-177 F3)."""

PORT_FILE = "DevToolsActivePort"
"""Written by Chromium itself into the profile dir once its DevTools server listens: line 1 is
the port it chose, line 2 the unguessable per-launch browser path (`/devtools/browser/<guid>`)."""

ATTACH_TIMEOUT_S = 10.0

PROBE_DEADLINE_S = 2.0
"""One monotonic deadline for the whole identity probe (connect + headers + body), not per read."""

PROBE_MAX_BYTES = 64 * 1024
"""Most bytes of a `/json/version` reply ever read (a real one is a few hundred)."""


class CdpEndpointError(RuntimeError):
    """The DevTools endpoint never appeared, is not this browser's, or reaches past loopback."""


def forget_cdp_port(profile_dir: Path) -> None:
    """Drop a port file a previous browser left behind, so it can never be read as ours."""
    with contextlib.suppress(OSError):
        (profile_dir / PORT_FILE).unlink(missing_ok=True)


def _published(profile_dir: Path, deadline: float) -> tuple[int, str]:
    """The (port, browser path) THIS launch's Chromium wrote; wait until it has finished writing."""
    while True:
        with contextlib.suppress(OSError, ValueError, IndexError):
            lines = (profile_dir / PORT_FILE).read_text(encoding="utf-8").splitlines()
            if lines[1].startswith("/devtools/browser/"):
                return int(lines[0]), lines[1].strip()
        if time.monotonic() > deadline:
            raise CdpEndpointError("the browser did not publish a DevTools port")
        time.sleep(0.05)


def _hard_close(sock: socket.socket) -> None:
    """Watchdog action: unblock whatever read is stuck on `sock`, from another thread."""
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)
    sock.close()


def _fetch_version(port: int) -> bytes:
    """The body of `GET http://127.0.0.1:<port>/json/version`, within ONE monotonic deadline
    (`PROBE_DEADLINE_S`, connect + headers + body) and at most `PROBE_MAX_BYTES` bytes.

    Talks to CDP_HOST:port only: no proxy, and no redirect is followed (only a 200 is a body).
    A watchdog closes the socket at the deadline, so a listener that trickles headers or body
    cannot outlast it. Anything else raises; the caller reads every error as "not this browser"."""
    deadline = time.monotonic() + PROBE_DEADLINE_S
    sock = socket.create_connection((CDP_HOST, port), timeout=PROBE_DEADLINE_S)
    watchdog = threading.Timer(max(deadline - time.monotonic(), 0.0), _hard_close, (sock,))
    watchdog.daemon = True
    watchdog.start()
    conn = http.client.HTTPConnection(CDP_HOST, port)
    conn.sock = sock  # the connection we made; the client never opens another
    try:
        conn.request("GET", "/json/version")
        reply = conn.getresponse()
        if reply.status != 200:
            raise ValueError(f"status {reply.status}")  # a redirect included
        if int(reply.getheader("Content-Length") or 0) > PROBE_MAX_BYTES:
            raise ValueError("reply too large")
        chunks: list[bytes] = []
        size = 0
        while time.monotonic() < deadline:
            piece = reply.read1(PROBE_MAX_BYTES + 1 - size)
            if not piece:
                if time.monotonic() >= deadline:
                    break
                return b"".join(chunks)
            chunks.append(piece)
            size += len(piece)
            if size > PROBE_MAX_BYTES:
                raise ValueError("reply too large")
        raise TimeoutError("the DevTools probe passed its deadline")
    finally:
        watchdog.cancel()
        conn.close()


def _answers_as(port: int, browser_path: str) -> bool:
    """True when the listener on `port` is the browser that published `browser_path`.

    Any error at all (a hang past the deadline, too many bytes, a redirect, non-HTTP bytes, bad
    or absurdly nested JSON incl. `RecursionError`) is "not this browser". `Exception`, not
    `BaseException`: KeyboardInterrupt / SystemExit still propagate to the caller's cleanup."""
    try:
        body = json.loads(_fetch_version(port))
        url = body.get("webSocketDebuggerUrl", "") if isinstance(body, dict) else ""
        return str(url).endswith(browser_path)
    except Exception:  # every doubt about this endpoint is a refusal
        return False


def _reaches_past_loopback(port: int) -> bool:
    """True when `port` also accepts on 127.0.0.2, i.e. it is bound to a wildcard, not CDP_HOST.

    Fails closed on an unexpected error. Three outcomes say "no": a refusal, a timeout (measured
    on Windows: a closed loopback port refuses only after ~2 s, so at 1 s a closed port IS a
    timeout; failing closed on it would refuse every legitimate Windows host), and a host with no
    127.0.0.2 alias (the check cannot be made; Chromium's loopback bind and the identity check
    still hold). Any other error is doubt, which refuses."""
    try:
        socket.create_connection(("127.0.0.2", port), timeout=1).close()
    except (ConnectionRefusedError, TimeoutError):
        return False
    except OSError as err:
        return err.errno not in (errno.EADDRNOTAVAIL, 10049)  # 10049 = WSAEADDRNOTAVAIL
    return True


def verified_cdp_url(profile_dir: Path) -> str:
    """The DevTools URL of the browser just launched on `profile_dir`, or `CdpEndpointError`.

    Chromium is asked for port 0 and picks the port itself, so there is no gap between "found a
    free port" and "bound it" for another process to use (D-082 item 1). The port is then read
    back from the file that browser wrote, the listener must answer with that browser's own
    unguessable path, and it must not also accept beyond loopback. Any doubt refuses."""
    port, browser_path = _published(profile_dir, time.monotonic() + ATTACH_TIMEOUT_S)
    if not _answers_as(port, browser_path):
        raise CdpEndpointError(f"the DevTools listener on port {port} is not this browser")
    if _reaches_past_loopback(port):
        raise CdpEndpointError(f"the DevTools listener on port {port} reaches beyond loopback")
    return f"http://{CDP_HOST}:{port}"


def launch_options(
    project: Project, paths: ProjectPaths, *, record_video_dir: Path | None = None,
    expose_cdp: bool = False,
) -> dict[str, Any]:
    """Arguments for `launch_persistent_context` (B5): headed by default, own profile.

    `AUTOTESTER_SLOW_MO_MS` (unset/0 by default -- no behavior change) pads every
    Playwright operation by that many ms, so a human watching the noVNC live view
    can actually see a run happen instead of it completing in under a second.
    Opt-in only, never set by the app itself -- a human exports it before a demo.

    `record_video_dir` (T-191/AT-587, V1/V7): when given, every page this
    context creates is recorded to that directory at `RECORD_VIDEO_SIZE`. This
    is the ONLY place `record_video_dir`/`record_video_size` are set (V7's
    single-choke-point requirement) -- omitted by default, so every caller
    that does not pass it (crawl explorer, manual login, every existing test)
    is unchanged, no video, no behavior change (C2).

    `expose_cdp` (T-177 F3, D-075): when True, Chromium also serves DevTools on a port IT picks
    (`0`), asked to bind `CDP_HOST` only, so the browser-use fallback can attach to THIS browser
    instead of launching a second one. False by default: no debug port exists unless a caller
    asks, per run. Read the port back with `verified_cdp_url`; never pick one here.
    """
    paths.profile_dir.mkdir(parents=True, exist_ok=True)
    slow_mo_ms = int(os.environ.get("AUTOTESTER_SLOW_MO_MS", "0") or "0")
    options: dict[str, Any] = {
        "user_data_dir": str(paths.profile_dir),
        "headless": not project.headed,
        "viewport": dict(DEFAULT_VIEWPORT),
        "slow_mo": slow_mo_ms,
        "args": [
            "--disable-blink-features=AutomationControlled",
            # Found running this for real under Docker/Xvfb: screenshot capture crashed
            # intermittently ("Protocol error (Page.captureScreenshot): Unable to capture
            # screenshot") on the second persistent-context launch in a process, specifically
            # when Chromium runs as root (the container's default user) without --no-sandbox,
            # and again for the same reason --disable-dev-shm-usage helps in constrained
            # display environments. Both are no-ops on a normal host launch.
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    }
    if expose_cdp:
        options["args"] += [f"--remote-debugging-address={CDP_HOST}", "--remote-debugging-port=0"]
    if record_video_dir is not None:
        record_video_dir.mkdir(parents=True, exist_ok=True)
        options["record_video_dir"] = str(record_video_dir)
        options["record_video_size"] = dict(RECORD_VIDEO_SIZE)
    return options
