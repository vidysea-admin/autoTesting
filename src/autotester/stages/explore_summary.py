"""Crawl persistence hygiene: redact what is written, and write the tracked summary.

One job: everything a crawl puts on disk passes the run's `Redactor` (every .env value,
the test-account email included), and a finished crawl leaves a small committed
`CrawlSummary` so its approval trail is checkable from a clean checkout.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from autotester.core.path_pii import safe_path
from autotester.core.redact import Redactor
from autotester.schema.crawl import Crawl
from autotester.schema.crawl_summary import CrawlSummary
from autotester.schema.enums import NodeStatus

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime

ModelT = TypeVar("ModelT", bound=BaseModel)

# Enumerated stop-reason codes (first match wins); the free text after the code is only a short,
# URL-free, parenthesis-free detail, so the tracked summary never carries page text or a URL.
_STOP_CODES = (
    ("crawl error", "crawl_error"),
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


# Values the system mints and later parses or joins on: ids and the crawl's ISO timestamps. They
# are never free text, so a short numeric secret (SMTP port 587) inside one is a coincidence;
# masking it breaks the re-parse (T-136 r5: a crawl died on `ScreenEdge.created_at`) or splits
# the graph's edge<->node joins. Every other string, free text and selectors included, is scrubbed.
_MINTED = frozenset({"id", "crawl_id", "node_id", "from_node", "to_node", "discovered_by",
                     "approval_id", "started_at", "finished_at", "heartbeat_at"})


def _scrub_text(redactor: Redactor, value: Any, key: str | None = None) -> Any:
    """Mask secrets in the STRING values of a python-mode dump only. datetimes, numbers and
    enum members are typed, not text (as in `core/trace.py::TraceWriter._scrub_value`)."""
    if isinstance(value, Enum):
        return value
    if isinstance(value, str):
        return value if key in _MINTED else redactor.scrub(value)
    if isinstance(value, dict):
        return {k: _scrub_text(redactor, v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub_text(redactor, v, key) for v in value]
    return value


def scrubbed(rt: ExploreRuntime, model: ModelT) -> ModelT:
    """A copy of `model` with every secret/account value masked, for DISK only. The
    in-memory object keeps the real selectors the crawler still needs. Ids and timestamps
    are kept (`_MINTED`; typed datetimes are never text)."""
    redactor = rt.session.secrets.redactor()
    return type(model).model_validate(_scrub_text(redactor, model.model_dump(mode="python")))


def save_crawl(rt: ExploreRuntime, crawl: Crawl) -> None:
    """AT-1349: persist the crawl envelope with the fields that carry page text masked.
    `coverage` (holes: selector, link name, url_template), `noise_counts` hosts and `stop_reason`
    go through `scrubbed`; config and counters are not text. In memory `crawl` is unchanged."""
    redactor = rt.session.secrets.redactor()
    update: dict[str, Any] = {
        "noise_counts": [scrubbed(rt, n) for n in crawl.noise_counts],
        "stop_reason": None if crawl.stop_reason is None else redactor.scrub(crawl.stop_reason)}
    if crawl.coverage is not None:
        update["coverage"] = scrubbed(rt, crawl.coverage)
    rt.store.save_crawl(crawl.model_copy(update=update))


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
