"""T-145's done_check (D-018): a live crawl counts as done only if it actually
ran AND a matching human approval covered it.

Replaces `{"cmd": "true"}` — a check that could never fail, on the highest-risk
task in the plan. Exits 0 only when the project has at least one crawl on disk
whose bounds an intact, unexpired `RunApproval` authorised.

    uv run python scripts/check_crawl_approval.py <project-slug>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.core.consent import ApprovalRequired, require_approval
from autotester.core.env import load_repo_env
from autotester.schema.enums import ApprovalKind, CrawlStatus
from autotester.store.project_store import ProjectStore


def main() -> int:
    load_repo_env()  # AT-110: require_approval now verifies a signature keyed from .env
    if len(sys.argv) != 2:
        print("usage: check_crawl_approval.py <project-slug>")
        return 2
    slug = sys.argv[1]
    store = ProjectStore(slug)
    project = store.load_project()
    if project is None:
        print(f"FAIL  no project '{slug}'")
        return 1

    crawl_ids = store.list_crawl_ids()
    crawls = [c for c in (store.load_crawl(i) for i in crawl_ids) if c is not None]
    finished = [c for c in crawls if c.status is not CrawlStatus.RUNNING and c.finished_at]
    if not finished:
        print(f"FAIL  no finished crawl on disk for '{slug}' ({len(crawl_ids)} crawl dirs)")
        return 1

    latest = finished[0]
    try:
        approval = require_approval(
            store.list_approvals(), project=slug, kind=ApprovalKind.CRAWL,
            target=project.base_url, actions=latest.bounds.max_actions,
            wall_clock_s=latest.bounds.wall_clock_s,
        )
    except ApprovalRequired as exc:
        print(f"FAIL  crawl {latest.id} ran but no approval covers it:\n{exc}")
        return 1

    print(
        f"PASS  crawl {latest.id} ({latest.status.value}, stop_reason={latest.stop_reason}, "
        f"{latest.screens} screens, {latest.denied} refused) covered by approval "
        f"{approval.id} granted by {approval.granted_by}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
