"""Crawl persistence hygiene: redact what is written, and write the tracked summary.

One job: everything a crawl puts on disk passes the run's `Redactor` (every .env value,
the test-account email included), and a finished crawl leaves a small committed
`CrawlSummary` so its approval trail is checkable from a clean checkout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

from autotester.schema.crawl import Crawl
from autotester.schema.crawl_summary import CrawlSummary

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime

ModelT = TypeVar("ModelT", bound=BaseModel)


def scrubbed(rt: ExploreRuntime, model: ModelT) -> ModelT:
    """A copy of `model` with every secret/account value masked, for DISK only. The
    in-memory object keeps the real selectors the crawler still needs. Ids are kept."""
    clean = rt.session.secrets.redactor().scrub_obj(model.model_dump(mode="json"))
    return type(model).model_validate(clean)


def write(rt: ExploreRuntime, crawl: Crawl) -> CrawlSummary:
    summary = CrawlSummary(
        crawl_id=crawl.id, project=crawl.project, status=crawl.status,
        approval_id=crawl.approval_id, approval_production=crawl.approval_production,
        project_production=rt.project.production, bounds=crawl.bounds,
        started_at=crawl.started_at, finished_at=crawl.finished_at,
        stop_reason=(crawl.stop_reason or "")[:200] or None,
        screens=crawl.screens, edges=crawl.edges, actions=crawl.actions,
        denied=crawl.denied, issues=crawl.issues, tool_failures=crawl.tool_failures)
    rt.store.save_crawl_summary(scrubbed(rt, summary))
    return summary
