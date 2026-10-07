"""Playwright launch options for one project's persistent browser context.

Moved out of `session.py` at B1 (D-015) — `session.py` was at its 300-line
cap and this function is self-contained. Behaviour unchanged; imported back
into `session.py` so nothing else needs to know it moved.
"""

from __future__ import annotations

import os
import socket
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


def loopback_port() -> int:
    """A free TCP port on `CDP_HOST`, chosen by the OS (never a fixed or guessable one)."""
    with socket.socket() as probe:
        probe.bind((CDP_HOST, 0))
        return int(probe.getsockname()[1])


def cdp_endpoint(port: int) -> str:
    return f"http://{CDP_HOST}:{port}"


def launch_options(
    project: Project, paths: ProjectPaths, *, record_video_dir: Path | None = None,
    cdp_port: int | None = None,
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

    `cdp_port` (T-177 F3, D-075): when given, Chromium also serves DevTools on that port,
    bound to `CDP_HOST` only, so the browser-use fallback can attach to THIS browser instead
    of launching a second one. Omitted by default: no debug port exists unless a caller asks.
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
    if cdp_port is not None:
        options["args"] += [f"--remote-debugging-address={CDP_HOST}",
                            f"--remote-debugging-port={cdp_port}"]
    if record_video_dir is not None:
        record_video_dir.mkdir(parents=True, exist_ok=True)
        options["record_video_dir"] = str(record_video_dir)
        options["record_video_size"] = dict(RECORD_VIDEO_SIZE)
    return options
