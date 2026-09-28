"""AT-335: the modal-crawl flake, made deterministic.

`explore_return.return_to`'s ladder (back -> the node's own URL -> replaying
the edge that discovered it) used to check its fingerprint exactly once,
right after `settle()`'s fixed networkidle+500ms grace. Against a real
browser this lost the dismissed-dashboard screen about 1 run in 14 -- rare
enough that a fix written against it would be unverifiable without a fixture
that lags on purpose, every time (13 of 14 attempts to reproduce it live came
back green; see qa/issues.jsonl AT-335).

`_SlowModalPage` is a real `BrowserSession` wired to a fake `page`, in the
same style `tests/crawl_fake.py` already uses for `explore_node`/`explore`
unit tests. Its dismiss button hides the veil on the REPLAYED click only --
the first dismiss (ordinary exploration, never touches `return_to`'s ladder)
stays instant, so this isolates the one mechanism AT-335 names rather than
also perturbing `explore_node.try_action`'s own edge classification.

Contract: qa/contracts/explore.md X3, X4 (the replay chain, and now its
tolerance, are both bounded).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from crawl_fake import grant_crawl_approval

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.crawl import CrawlBounds
from autotester.schema.project import Project
from autotester.stages.explore import run_crawl
from autotester.store.project_store import ProjectStore

BASE = "https://modal.test/"

DISMISS_DELAY_S = 0.35
"""How long the REPLAYED dismiss takes to 'land'. `settle()` is faked to
finish instantly below (its fixed grace never actually sleeps), so a single
check right after it can never see this -- only a bounded retry can."""


def _element(raw: dict[str, Any], *, obscured: bool = False) -> dict[str, Any]:
    return {"role": "button", "name": "", "selector": "", "enabled": True, "visible": True,
            "obscured": obscured, "href": None, "is_form_submit": False, "in_row": False,
            "target_blank": False, "tag": "button", **raw}


class _Locator:
    def __init__(self, page: _SlowModalPage, selector: str) -> None:
        self._page, self._selector = page, selector

    def click(self) -> None:
        self._page.clicks.append(self._selector)
        if self._selector != "#skip-modal":
            return
        self._page.dismiss_clicks += 1
        # The first dismiss (ordinary exploration of the veiled screen) is
        # instant; only a REPLAYED dismiss -- the one `return_to`'s ladder
        # performs -- lags, isolating AT-335's mechanism from try_action's own
        # (separate) edge classification.
        delay = 0.0 if self._page.dismiss_clicks == 1 else DISMISS_DELAY_S
        self._page.dismissed_at = time.monotonic()
        self._page.dismiss_delay = delay

    def evaluate(self, script: str) -> None:
        return None


class _SlowModalPage:
    """Fakes exactly the `page` surface `BrowserSession` touches. `/` always
    re-renders the veiled state fresh on a real navigation (goto/back) --
    AT-227: a client-side-only dismissal has no URL that restores it -- which
    is what forces every return through this ladder onto the replay rung."""

    def __init__(self) -> None:
        self.url = BASE
        self.history = [BASE]
        self.clicks: list[str] = []
        self.dismiss_clicks = 0
        self.dismissed_at: float | None = None
        self.dismiss_delay = 0.0

    def _dismissed(self) -> bool:
        return (self.dismissed_at is not None
                and time.monotonic() - self.dismissed_at >= self.dismiss_delay)

    def locator(self, selector: str) -> _Locator:
        return _Locator(self, selector)

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url
        self.dismissed_at = None
        self.history.append(url)

    def go_back(self, wait_until: str = "") -> None:
        if len(self.history) > 1:
            self.history.pop()
        self.url = self.history[-1]
        self.dismissed_at = None

    def evaluate(self, script: str) -> list[dict[str, Any]]:
        if self.url != BASE:
            return []
        if self._dismissed():
            return [_element({"role": "link", "name": "Reports", "selector": "#reports-link",
                              "href": "/reports.html"})]
        return [
            _element({"role": "link", "name": "Reports", "selector": "#reports-link",
                      "href": "/reports.html"}, obscured=True),
            _element({"role": "button", "name": "Skip for now", "selector": "#skip-modal"}),
        ]

    def title(self) -> str:
        return self.url

    def add_style_tag(self, content: str) -> None:
        return None

    def screenshot(self, path: str, full_page: bool = False) -> None:
        Path(path).write_bytes(b"png")

    def wait_for_timeout(self, timeout: int) -> None:
        return None  # settle's fixed grace stays instant -- the point of the test

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        return None


def _session(tmp_path: Path) -> BrowserSession:
    project = Project(slug="demo", name="Modal demo", base_url=BASE,
                      allowed_domains=["modal.test"], headed=False)
    paths = ProjectPaths("demo", tmp_path)
    env = tmp_path / ".env"
    env.write_text("", encoding="utf-8")
    session = BrowserSession(project, SecretStore.load(project, env, strict=False),
                             tmp_path / "shots", paths)
    session._page = _SlowModalPage()
    session.state.run_dir.mkdir(parents=True, exist_ok=True)
    return session


def test_return_to_tolerates_a_replayed_dismiss_that_lands_late(tmp_path: Path) -> None:
    """AT-335, made deterministic. Before the bounded-retry fix this fails
    reliably (the replayed dismiss's fingerprint check ran once, before
    `DISMISS_DELAY_S` had elapsed); after it, `explore_return._matches`
    polls within its bounded window and the crawl reaches the screen behind
    the modal every time, not 13 times out of 14."""
    session = _session(tmp_path)
    project = session.project
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    crawl = run_crawl(project, session, store, observer=PageObserver(),
                      bounds=CrawlBounds(max_screens=12, max_actions=30, wall_clock_s=30.0))

    templates = {n.url_template for n in store.list_nodes(crawl.id)}
    assert "/reports.html" in templates, "never reached the page behind the modal"
    assert crawl.screens >= 3, [n.url_template for n in store.list_nodes(crawl.id)]
