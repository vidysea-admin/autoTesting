"""A short numeric .env value must not corrupt what a crawl later parses (T-136 live r5).

Live crawl_01M5A1YZHW8PE5AX8SMWHJ5PRY declared AUTOTESTER_SMTP_PORT=587 in the repo .env. The
persistence scrub (`explore_summary.scrubbed`) masked those digits inside a `ScreenEdge.created_at`
timestamp, the re-parse in `model_validate` raised, and the crawl stayed `running` and partial.
Offline: the fake site, a temp dir, no browser, network or model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from crawl_fake import BASE, grant_crawl_approval, make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.core.redact import MASK
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, CrawlStatus, EdgeOutcome
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages import explore, explore_node
from autotester.stages import explore_summary as persisted
from autotester.store.project_store import ProjectStore

KEY = "AUTOTESTER_SMTP_PORT"


def _rt(tmp_path: Path, value: str = "587") -> SimpleNamespace:
    """A runtime stand-in whose session redacts EVERY .env value (AT-004), as in the live run."""
    project = make_project()
    env = tmp_path / ".env"
    env.write_text(f"{KEY}={value}\n", encoding="utf-8")
    session = BrowserSession(project, SecretStore.load(project, env, strict=False),
                             tmp_path / "shots", ProjectPaths("demo", tmp_path))
    return SimpleNamespace(session=session)


def _edge(**over) -> ScreenEdge:
    stamp = datetime(2026, 10, 19, 5, 58, 7, 587000, tzinfo=UTC)
    fields = {"crawl_id": "crawl_X", "from_node": "node_a", "action": Action.CLICK,
              "target": "a.x", "outcome": EdgeOutcome.SAME_SCREEN, "created_at": stamp}
    return ScreenEdge(**{**fields, **over})


def test_smtp_port_587_in_env_appears_inside_a_crawl_timestamp(tmp_path: Path) -> None:
    """C1: the exact live failure -- created_at holds ...07.587000, the secret is 587."""
    edge = _edge()
    clean = persisted.scrubbed(_rt(tmp_path), edge)  # used to raise ValidationError
    assert clean.created_at == edge.created_at


def test_ids_that_contain_the_secret_digits_still_join(tmp_path: Path) -> None:
    """C1: the graph joins edges to nodes by id; masking digits inside one splits the graph."""
    edge = _edge(from_node="node_ab587cdef012", to_node="node_587000aaaa11", id="edge_5870000000aa")
    clean = persisted.scrubbed(_rt(tmp_path), edge)
    assert (clean.id, clean.from_node, clean.to_node) == (edge.id, edge.from_node, edge.to_node)
    node = ScreenNode(crawl_id="crawl_587", project="demo", url_template="/p",
                      url_example=BASE + "p", signature="sig", discovered_by="edge_1587")
    cleaned = persisted.scrubbed(_rt(tmp_path), node)
    assert (cleaned.id, cleaned.crawl_id, cleaned.discovered_by) == (
        node.id, node.crawl_id, node.discovered_by)


def test_free_text_still_masks_the_same_numeric_secret(tmp_path: Path) -> None:
    """C2: AT-1304's rule holds -- strings are scrubbed, only typed/minted fields are exempt."""
    edge = _edge(reason="smtp refused on port 587", name="Port 587", target="input[port=587]")
    clean = persisted.scrubbed(_rt(tmp_path), edge)
    assert "587" not in clean.reason + clean.name + clean.target
    assert MASK in clean.reason and clean.created_at == edge.created_at


def test_a_crawl_with_a_numeric_secret_in_every_timestamp_finishes(tmp_path: Path) -> None:
    """C1 end to end: the secret "20" sits in the year of every created_at the crawl writes."""
    project = make_project()
    session, _page = make_session(tmp_path, project)
    (tmp_path / ".env").write_text(f"{KEY}=20\n", encoding="utf-8")
    session.secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = explore.run_crawl(project, session, store, observer=PageObserver(),
                              bounds=CrawlBounds())
    assert crawl.status is CrawlStatus.COMPLETED
    assert store.load_crawl(crawl.id).status is CrawlStatus.COMPLETED
    assert store.list_edges(crawl.id) and store.list_nodes(crawl.id)


def test_a_crawl_that_raises_mid_run_ends_terminal_with_the_error_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C3: any exception from the walk leaves a terminal status, never `running`."""
    project = make_project()
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)

    def boom(rt, node) -> None:
        raise ValueError("synthetic mid-crawl failure")

    monkeypatch.setattr(explore_node, "visit_node", boom)
    crawl = explore.run_crawl(project, session, store, observer=PageObserver())
    on_disk = store.load_crawl(crawl.id)
    assert crawl.status is CrawlStatus.ABORTED and on_disk.status is CrawlStatus.ABORTED
    assert "ValueError: synthetic mid-crawl failure" in on_disk.stop_reason
    assert on_disk.finished_at is not None
    assert [s.status for s in store.list_crawl_summaries()] == [CrawlStatus.ABORTED]
