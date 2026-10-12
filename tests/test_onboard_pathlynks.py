"""Onboarding script. Contract: qa/contracts/pathlynks-onboarding.md O1-O4.

O1 is the load-bearing criterion here: nothing in this script may pass a raw
secret to anything but `BrowserSession.fill`/`resolve`. These tests run
against a fake session (no network) and assert on what was actually called.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import onboard_pathlynks as onboard_mod

from autotester.core.paths import ProjectPaths
from autotester.schema.enums import WritePolicy
from autotester.schema.project import Project, SecretRef
from autotester.store import ProjectStore

PASSWORD = "hunter2-trombone-staple"


def make_project() -> Project:
    return Project(
        slug="pathlynks", name="Pathlynks", base_url="https://pathlynks.vidysea.test/signin",
        allowed_domains=["vidysea.test"], write_policy=WritePolicy.READ_ONLY, headed=False,
        secrets=[
            SecretRef(key="PATHLYNKS_USER_EMAIL", domains=["pathlynks.vidysea.test"],
                      mask_in_screenshot=False),
            SecretRef(key="PATHLYNKS_USER_PASSWORD", domains=["pathlynks.vidysea.test"]),
        ],
    )


class FakePage:
    def __init__(self, url: str) -> None:
        self.url = url
        self.filled: dict[str, str] = {}

    def locator(self, selector: str):
        page = self

        class _Loc:
            def evaluate(self, script: str) -> None:
                pass

            def fill(self, value: str) -> None:
                page.filled[selector] = value

            def click(self) -> None:
                pass

        return _Loc()

    def add_style_tag(self, content: str) -> None:
        pass

    def screenshot(self, path: str, full_page: bool = False) -> None:
        Path(path).write_bytes(b"png")

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url

    def wait_for_timeout(self, ms: int) -> None:
        pass


def seed_project_and_env(tmp_path: Path) -> None:
    ProjectStore("pathlynks", tmp_path).save_project(make_project())
    env = tmp_path / ".env"
    env.write_text(
        f"PATHLYNKS_USER_EMAIL=tester@vidysea.test\nPATHLYNKS_USER_PASSWORD={PASSWORD}\n",
        encoding="utf-8",
    )


def test_onboard_calls_fill_with_placeholders_never_a_literal(tmp_path: Path, monkeypatch) -> None:
    """O1: onboard()'s OWN code must pass {{SECRET:KEY}} to fill(), never a real
    value -- what fill() does internally (resolve + type it) is T-010's contract,
    already covered there. The boundary this script owns is what IT passes in."""
    seed_project_and_env(tmp_path)

    def fake_start(self):
        self._page = FakePage(self.project.base_url)
        self.state.run_dir.mkdir(parents=True, exist_ok=True)
        return self

    fill_calls: list[tuple[str, str | None]] = []
    real_fill = onboard_mod.BrowserSession.fill

    def spying_fill(self, locator, value, **kw):
        fill_calls.append((locator, value))
        return real_fill(self, locator, value, **kw)

    monkeypatch.setattr(onboard_mod.BrowserSession, "start", fake_start)
    monkeypatch.setattr(onboard_mod.BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(onboard_mod.BrowserSession, "fill", spying_fill)

    onboard_mod.onboard("user", root=tmp_path)

    calls = dict(fill_calls)
    assert calls[onboard_mod.SIGNIN_EMAIL] == "{{SECRET:PATHLYNKS_USER_EMAIL}}"
    assert calls[onboard_mod.SIGNIN_PASSWORD] == "{{SECRET:PATHLYNKS_USER_PASSWORD}}"
    # the raw password must not appear anywhere in what onboard() itself passed
    assert PASSWORD not in repr(fill_calls)


def test_onboard_raises_when_project_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=re.escape("project.json")):
        onboard_mod.onboard("user", root=tmp_path)


def test_knowledge_file_has_the_required_sections(tmp_path: Path) -> None:
    paths = ProjectPaths("pathlynks", tmp_path)
    onboard_mod._write_knowledge(paths, "onboard-test", "user", ["landing", "post-login: x"])
    text = paths.knowledge.read_text(encoding="utf-8")
    for heading in ("Quick Re-Run", "Portal Profile", "How it works", "Screens reached",
                    "Gotchas", "History"):
        assert heading in text
    assert "**Purpose:**" in text and "**Open me when:**" in text  # L6, self-describing


def test_onboard_scrubs_the_landed_url_before_recording_it(tmp_path: Path, monkeypatch) -> None:
    """`_write_knowledge` itself has no redactor -- the caller (`onboard()`) must
    scrub before appending to `screens`. This is the actual O1 boundary: the
    redactor runs on the landed URL before it ever becomes evidence text."""
    seed_project_and_env(tmp_path)

    def fake_start(self):
        # worst case: a redirect URL that happens to embed the secret in a
        # query string -- the redactor must catch it, not just the field fill.
        self._page = FakePage(f"{self.project.base_url}?leak={PASSWORD}")
        self.state.run_dir.mkdir(parents=True, exist_ok=True)
        return self

    monkeypatch.setattr(onboard_mod.BrowserSession, "start", fake_start)
    monkeypatch.setattr(onboard_mod.BrowserSession, "close", lambda self: None)

    onboard_mod.onboard("user", root=tmp_path)

    paths = ProjectPaths("pathlynks", tmp_path)
    assert PASSWORD not in paths.knowledge.read_text(encoding="utf-8")
