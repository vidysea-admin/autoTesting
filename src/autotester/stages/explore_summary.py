"""Crawl persistence hygiene: redact what is written, and write the tracked summary.

One job: everything a crawl puts on disk passes the run's `Redactor` (every .env value,
the test-account email included), and a finished crawl leaves a small committed
`CrawlSummary` so its approval trail is checkable from a clean checkout.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from autotester.core.path_pii import safe_path
from autotester.schema.crawl import Crawl
from autotester.schema.crawl_summary import CrawlSummary
from autotester.schema.enums import NodeStatus

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime

ModelT = TypeVar("ModelT", bound=BaseModel)

# Enumerated stop-reason codes (first match wins); the free text after the code is only a short,
# URL-free, parenthesis-free detail, so the tracked summary never carries page text or a URL.
_STOP_CODES = (
    ("max_screens", "max_screens"), ("max_actions", "max_actions"),
    ("wall_clock_s", "wall_clock_s"), ("max_depth", "max_depth"),
    ("abandoned visits", "abandoned_visits"), ("login case", "login_failed"),
    ("could not open base_url", "seed_unreachable"), ("destructive_last", "destructive_last"),
    ("frontier empty", "frontier_exhausted"), ("synthetic", "typing_refused"),
)
_URLISH = re.compile(r"(?:[a-z][a-z0-9+.-]*://|www\.)\S*|(?<!\w)/[\w./%?&=#:-]*", re.IGNORECASE)
_DETAIL_CAP = 80


def safe_stop_reason(reason: str | None) -> str | None:
    """`code` or `code: short detail`: an enumerated code, then the original text with URLs,
    paths and anything in brackets removed, capped at 80 chars."""
    if not reason:
        return None
    low = reason.lower()
    code = next((c for needle, c in _STOP_CODES if needle in low), "other")
    detail = re.sub(r"[\(\[][^)\]]*[)\]]", "", _URLISH.sub("", reason))
    detail = " ".join(detail.split())[:_DETAIL_CAP].strip()
    return f"{code}: {detail}" if detail and detail.lower() != code else code


def scrubbed(rt: ExploreRuntime, model: ModelT) -> ModelT:
    """A copy of `model` with every secret/account value masked, for DISK only. The
    in-memory object keeps the real selectors the crawler still needs. Ids are kept."""
    clean = rt.session.secrets.redactor().scrub_obj(model.model_dump(mode="json"))
    return type(model).model_validate(clean)


def _split_paths(rt: ExploreRuntime) -> tuple[list[str], list[str]]:
    """(visited, never visited) url templates. Path templates only: no host, query or content."""
    done = {NodeStatus.EXPLORED, NodeStatus.SKIPPED_UNCHANGED}
    reached = {safe_path(n.url_template) for n in rt.nodes.values() if n.status in done}
    rest = {safe_path(n.url_template) for n in rt.nodes.values() if n.status not in done}
    return sorted(reached), sorted(rest - reached)


def write(rt: ExploreRuntime, crawl: Crawl) -> CrawlSummary:
    reached, unreached = _split_paths(rt)
    summary = CrawlSummary(
        reached_paths=reached, unreached_paths=unreached,
        crawl_id=crawl.id, project=crawl.project, status=crawl.status,
        approval_id=crawl.approval_id, approval_production=crawl.approval_production,
        project_production=rt.project.production, bounds=crawl.bounds,
        started_at=crawl.started_at, finished_at=crawl.finished_at,
        stop_reason=safe_stop_reason(crawl.stop_reason),
        screens=crawl.screens, edges=crawl.edges, actions=crawl.actions,
        denied=crawl.denied, issues=crawl.issues, tool_failures=crawl.tool_failures)
    rt.store.save_crawl_summary(scrubbed(rt, summary))
    return summary
