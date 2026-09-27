"""A scripted fake site for the explorer's unit tests — not a test module
itself (pytest does not collect it). Imported by `test_explore.py`.

Kept out of `test_explore.py` so both stay under the 300-line cap, and out of
`conftest.py` because it is explorer-specific, not a shared fixture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import ApprovalKind, WritePolicy
from autotester.schema.project import Project
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

BASE = "https://app.test/"

# url -> list of element dicts, as browser/enumerate.js would return them.
SITE: dict[str, list[dict[str, Any]]] = {
    "https://app.test/": [
        {"role": "link", "name": "Students", "selector": "a.students", "href": "/students/"},
        {"role": "link", "name": "Settings", "selector": "a.settings", "href": "/settings"},
        {"role": "link", "name": "External", "selector": "a.ext", "href": "https://evil.test/"},
    ],
    "https://app.test/students/": [
        {"role": "link", "name": "Open 1", "selector": "a.s1", "href": "/students/1",
         "in_row": True},
        {"role": "link", "name": "Open 2", "selector": "a.s2", "href": "/students/2",
         "in_row": True},
    ],
    "https://app.test/students/1": [
        {"role": "button", "name": "Edit", "selector": "button.edit"},
    ],
    "https://app.test/students/2": [
        {"role": "button", "name": "Edit", "selector": "button.edit"},
    ],
    "https://app.test/settings": [
        {"role": "button", "name": "Delete account", "selector": "button.del"},
        {"role": "button", "name": "Save", "selector": "button.save", "is_form_submit": True},
        {"role": "link", "name": "Log out", "selector": "a.out", "href": "/logged-out"},
        {"role": "button", "name": "", "selector": "button.icon"},
        # X10-b: post-login form fields the typing pre-pass may fill.
        {"role": "textbox", "name": "Display name", "selector": "input.displayname",
         "tag": "input"},
        {"role": "combobox", "name": "Grade", "selector": "select.grade", "tag": "select"},
    ],
    # AT-532: a form whose fill auto-submits to ANOTHER domain (a real
    # onchange auto-submit) — typing it must never create/explore the
    # off-domain node.
    "https://app.test/trap": [
        {"role": "textbox", "name": "Search", "selector": "input.offdomain"},
    ],
    "https://evil.test/trap": [],
    "https://app.test/deleted": [],
    "https://app.test/saved": [],
    "https://app.test/logged-out": [],
}

# selector -> the url a click on it navigates to (links navigate by href).
CLICK_TARGETS = {"button.del": "https://app.test/deleted",
                 "button.save": "https://app.test/saved",
                 "button.icon": "https://app.test/deleted"}

# AT-532: a fill that auto-submits — the url the browser lands on after.
FILL_TARGETS = {"input.offdomain": "https://evil.test/trap"}


def _element(raw: dict[str, Any]) -> dict[str, Any]:
    return {"role": "button", "name": "", "selector": "", "enabled": True, "visible": True,
            "href": None, "is_form_submit": False, "in_row": False, "target_blank": False,
            "tag": "button", **raw}


class FakeOption:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_attribute(self, name: str) -> str | None:
        return self._value if name == "value" else None


class FakeLocator:
    def __init__(self, page: FakeSitePage, selector: str) -> None:
        self.page, self.selector = page, selector

    def click(self) -> None:
        self.page.clicks.append(self.selector)
        target = CLICK_TARGETS.get(self.selector)
        if target:
            self.page.visit(target)

    def evaluate(self, script: str) -> None:
        return None

    def inner_text(self) -> str:
        return ""

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self.page, f"{self.selector} >> {selector}")

    def all(self) -> list[FakeOption]:
        """X10-b: a combobox's options. The fake serves one empty (placeholder)
        plus one real option for any `option` query, none otherwise."""
        if "option" in self.selector:
            return [FakeOption(""), FakeOption("grade-a")]
        return []

    def select_option(self, value: str) -> None:
        self.page.selects.append((self.selector, value))

    def fill(self, value: str) -> None:
        """AT-226's fake: a field only 'exists' where the test registers it via
        `page.fillable[url]` — mirrors a real Playwright locator timing out
        when the login form was never rendered because the browser was
        already redirected past the login page."""
        if self.selector not in self.page.fillable.get(self.page.url, set()):
            raise TimeoutError(f"locator not found: {self.selector!r} on {self.page.url!r}")
        # AT-274: recorded so a test can assert a FILL genuinely happened,
        # not merely that the crawl completed -- `crawl.status` alone cannot
        # distinguish "the login case ran" from "the login case was skipped".
        self.page.fills.append((self.selector, value))
        # AT-532: a fill whose onchange auto-submits (a real-world search box
        # with an instant-submit handler).
        target = FILL_TARGETS.get(self.selector)
        if target:
            self.page.visit(target)


class FakeSitePage:
    """A scripted site: `goto`/`click` move between urls in `SITE`."""

    def __init__(self, url: str = BASE) -> None:
        self.url = url
        self.history: list[str] = [url]
        self.clicks: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self.selects: list[tuple[str, str]] = []
        self.shots: list[str] = []
        self.redirects: dict[str, str] = {}
        """AT-226: simulates a login page redirecting away when the persistent
        profile already holds a live session — a real `goto` to `/signin` on
        an authenticated browser never lands on `/signin`."""
        self.fillable: dict[str, set[str]] = {}
        """AT-226: url -> selectors that 'exist' there, for `FakeLocator.fill`."""

    def visit(self, url: str) -> None:
        self.url = self.redirects.get(url, url)
        self.history.append(self.url)

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def goto(self, url: str, wait_until: str = "") -> None:
        self.visit(url)

    def go_back(self, wait_until: str = "") -> None:
        if len(self.history) > 1:
            self.history.pop()
        self.url = self.history[-1]

    def evaluate(self, script: str) -> list[dict[str, Any]]:
        return [_element(raw) for raw in SITE.get(self.url, [])]

    def title(self) -> str:
        return self.url

    def add_style_tag(self, content: str) -> None:
        return None

    def screenshot(self, path: str, full_page: bool = False) -> None:
        self.shots.append(path)
        Path(path).write_bytes(b"png")

    def wait_for_timeout(self, timeout: int) -> None:
        return None

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        return None


def make_project(write_policy: WritePolicy = WritePolicy.READ_ONLY) -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["app.test"],
                   write_policy=write_policy)


def make_session(tmp_path: Path, project: Project) -> tuple[BrowserSession, FakeSitePage]:
    paths = ProjectPaths("demo", tmp_path)
    env = tmp_path / ".env"
    env.write_text("", encoding="utf-8")
    session = BrowserSession(project, SecretStore.load(project, env, strict=False),
                             tmp_path / "shots", paths)
    page = FakeSitePage()
    session._page = page
    session.state.run_dir.mkdir(parents=True, exist_ok=True)
    return session, page


def grant_crawl_approval(store: ProjectStore, project: Project,
                         bounds: CrawlBounds | None = None) -> None:
    """D-018: `run_crawl` refuses without a human's `RunApproval` on disk. Tests
    grant a real one rather than bypassing the gate, so every crawl test also
    exercises the gate's happy path — a guard only the production callers pass
    through is a guard tested nowhere."""
    bounds = bounds or CrawlBounds()
    store.add_approval(RunApproval(
        project=project.slug, run_kind=ApprovalKind.CRAWL, target=project.base_url,
        scope="fixture crawl in tests", max_actions=bounds.max_actions,
        wall_clock_s=bounds.wall_clock_s, granted_by="test",
        granted_at="2026-09-08", expires_at="2099-01-01",
    ).sign())


def crawl_it(tmp_path: Path, *, project: Project | None = None,
             bounds: CrawlBounds | None = None, policy: SafetyPolicy | None = None,
             clock: Any = None) -> tuple[Any, ProjectStore, FakeSitePage]:
    project = project or make_project()
    session, page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project, bounds)
    kwargs: dict[str, Any] = {"observer": PageObserver(), "bounds": bounds or CrawlBounds(),
                              "policy": policy}
    if clock is not None:
        kwargs["clock"] = clock
    crawl = run_crawl(project, session, store, **kwargs)
    return crawl, store, page
