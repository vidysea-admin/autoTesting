"""One job: warn, before a run, about cases aimed at screens the latest crawl never reached.

AT-887 clause 2. A crawl's summary records which screen templates it visited and which it
found but left in the frontier (stopped by a bound, or aborted). A case whose first target is a
URL on such a screen was written against a surface the account may not be able to reach, and
running it blind reads as an INCONCLUSIVE product bug. This is a WARNING: it never removes,
skips or reorders a case. Only URL targets are judged; a locator or `{{SECRET}}` first step
cannot be matched to a screen, so it is left unwarned rather than guessed at.
"""

from __future__ import annotations

from autotester.core.urls import url_template
from autotester.schema.case import Case
from autotester.schema.crawl_summary import CrawlSummary
from autotester.schema.enums import Action
from autotester.store.project_store import ProjectStore


def _first_route(case: Case) -> str | None:
    if not case.steps or case.steps[0].action is not Action.NAVIGATE:
        return None
    target = case.steps[0].target
    if "{{" in target or not target.startswith(("http://", "https://", "/")):
        return None
    return url_template(target, keep_host=False, fold_index=True)


def reachability_warnings(cases: list[Case], summary: CrawlSummary | None) -> list[str]:
    """One line per case whose first target the crawl did not reach; [] when no crawl summary."""
    if summary is None or not (summary.reached_paths or summary.unreached_paths):
        return []  # a summary from before AT-887 holds no screen lists: say nothing, claim nothing
    reached, frontier = set(summary.reached_paths), set(summary.unreached_paths)
    out: list[str] = []
    for case in cases:
        route = _first_route(case)
        if route is None or route in reached:
            continue
        why = ("found by crawl %s but never visited (frontier)" if route in frontier
               else "not seen by crawl %s at all") % summary.crawl_id
        out.append(f"case {case.id}: first target {route} {why}; it will still run")
    return out


def latest_warnings(store: ProjectStore, cases: list[Case]) -> list[str]:
    summaries = store.list_crawl_summaries()  # newest first
    return reachability_warnings(cases, summaries[0] if summaries else None)
