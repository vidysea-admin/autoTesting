"""Manual one-time login. Contract: qa/contracts/manual-login.md ML1-ML5.

Umesh: "for login you should only need id+password — either take it from the
user, or better, open the browser and let the human log in themselves."
This opens the real, visible browser to the project's base URL and waits for
a human to log in by hand — no `SecretRef`/`.env` value is ever read. Closing
the session persists the login into `profiles/<slug>/`, so every later run
reuses it. `.env` auto-fill (`browser/secrets.py`) and the OTP/2FA
`blocked_hitl` pause stay exactly as they are — this is a third, additive
option, not a replacement.
"""

from __future__ import annotations

from collections.abc import Callable

from autotester.browser.profiles import MAIN_ACCOUNT, capture_session
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project

WaitForHuman = Callable[[str], None]


def _default_wait(prompt: str) -> None:
    input(prompt)


def manual_login(
    project: Project,
    paths: ProjectPaths | None = None,
    *,
    wait_for_human: WaitForHuman = _default_wait,
) -> None:
    """Open `project.base_url` in a real headed browser and block until the
    human confirms they've logged in. Reads no secret (ML1)."""
    paths = paths or ProjectPaths(project.slug)
    secrets = SecretStore.load(project, paths.env_file, strict=False)
    session = BrowserSession(project, secrets, paths.runs_dir / "manual-login", paths)
    session.start()
    try:
        session.goto(project.base_url)
        wait_for_human(
            f"A browser window is open at {project.base_url}.\n"
            "Log in by hand, then press Enter here to save the session..."
        )
        capture_session(session, project, MAIN_ACCOUNT)  # U12 (M39): store on only, else a no-op
    finally:
        session.close()
