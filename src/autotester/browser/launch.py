"""Playwright launch options for one project's persistent browser context.

Moved out of `session.py` at B1 (D-015) — `session.py` was at its 300-line
cap and this function is self-contained. Behaviour unchanged; imported back
into `session.py` so nothing else needs to know it moved.
"""

from __future__ import annotations

import os
from typing import Any

from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project

DEFAULT_VIEWPORT = {"width": 1366, "height": 850}
"""The desktop viewport every context launches with. `browser/conditions.py` reads this
to reset a VIEWPORT_MOBILE case back to default afterwards (D-045/AT-581)."""


def launch_options(project: Project, paths: ProjectPaths) -> dict[str, Any]:
    """Arguments for `launch_persistent_context` (B5): headed by default, own profile.

    `AUTOTESTER_SLOW_MO_MS` (unset/0 by default -- no behavior change) pads every
    Playwright operation by that many ms, so a human watching the noVNC live view
    can actually see a run happen instead of it completing in under a second.
    Opt-in only, never set by the app itself -- a human exports it before a demo.
    """
    paths.profile_dir.mkdir(parents=True, exist_ok=True)
    slow_mo_ms = int(os.environ.get("AUTOTESTER_SLOW_MO_MS", "0") or "0")
    return {
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
