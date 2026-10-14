"""CrawlSummary: the small, redacted, TRACKED record of one finished crawl.

The full crawl directory is gitignored (it carries a real product's screen structure), so a
done_check that read it failed in a clean checkout. This is the part safe to commit: ids,
the gating approval, bounds and counters. No URLs, identifiers, secrets or page content.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from autotester.schema.base import Artifact
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import CrawlStatus


class CrawlSummary(Artifact):
    model_config = ConfigDict(extra="forbid")

    crawl_id: str
    project: str
    status: CrawlStatus
    approval_id: str | None = Field(default=None, description="the approval that gated the run")
    approval_production: bool | None = None
    project_production: bool = Field(default=False, description="the project's declared flag then")
    bounds: CrawlBounds
    started_at: str | None = None
    finished_at: str | None = None
    stop_reason: str | None = Field(default=None, description="code, then short URL-free detail")
    screens: int = 0
    edges: int = 0
    actions: int = 0
    denied: int = 0
    issues: int = 0
    tool_failures: int = 0
    reached_paths: list[str] = Field(
        default_factory=list,
        description="AT-887 clause 2: url_template (path only) of each screen the crawl visited")
    unreached_paths: list[str] = Field(
        default_factory=list,
        description="AT-887 clause 2: url_template of each screen found but never visited -- "
                    "still queued, or aborted -- when the crawl stopped (the frontier)")
