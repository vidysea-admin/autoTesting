"""Real browser, local fixture only: unauth deeplink lands on login; collapsed menus expand."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path

from test_session_survives_failure_live import _skip_if_no_chromium

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project
from autotester.ui.run_execution import _wipe_entry_profile

SITE = Path(__file__).parent / "fixtures" / "guard_menu_site"
HEADED = os.environ.get("AUTOTESTER_HEADED_TESTS") == "1"


def _session(tmp_path: Path, base: str, slug: str) -> BrowserSession:
    project = Project(slug="gm", name="t", base_url=base, allowed_domains=["127.0.0.1"],
                      headed=HEADED)
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    return BrowserSession(project, secrets, tmp_path / "runs",
                          ProjectPaths(slug, tmp_path), record_video=True)


def test_unauth_deeplink_lands_on_login_in_a_wiped_profile(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    _skip_if_no_chromium()
    base = serve_dir(SITE)
    signed_in = _session(tmp_path, base, "gm").start()
    try:
        signed_in.goto(f"{base}/login.html")
        signed_in.click("#go")
        signed_in.page.wait_for_url("**/dashboard.html")
        signed_in.goto(f"{base}/dashboard.html")
        assert signed_in.page.url.endswith("/dashboard.html")  # the leak the fix removes
    finally:
        signed_in.close()
    entry_paths = ProjectPaths("gm-entry-test", tmp_path)
    shutil.copytree(ProjectPaths("gm", tmp_path).profile_dir, entry_paths.profile_dir)  # stale
    _wipe_entry_profile(entry_paths.profile_dir)
    fresh = _session(tmp_path, base, "gm-entry-test").start()
    try:
        fresh.goto(f"{base}/dashboard.html")
        fresh.page.wait_for_url("**/login.html")
        assert fresh.page.locator("#login").is_visible()
    finally:
        fresh.close()


def test_click_expands_a_collapsed_submenu_and_a_covering_menu_button(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    _skip_if_no_chromium()
    base = serve_dir(SITE)
    session = _session(tmp_path, base, "gm").start()
    try:
        session.goto(f"{base}/menu.html")
        session.click("#child")
        assert session.page.url.endswith("#done")
        session.click("#under")
        assert session.page.url.endswith("#covered")
        notes = [e.path for e in session.state.evidence if "before clicking" in e.path]
        assert any("expanded parent menu" in n for n in notes), notes
    finally:
        session.close()
