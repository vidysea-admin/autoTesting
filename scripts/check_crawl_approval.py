"""T-145's done_check (D-018): a live crawl counts as done only if it actually
ran AND a matching human approval covered it.

Replaces `{"cmd": "true"}` — a check that could never fail, on the highest-risk
task in the plan. Exits 0 only when the newest tracked crawl summary
(`projects/<slug>/crawl_summaries/`, written when a crawl finishes; the full crawl dir is
gitignored, so a clean checkout has only this) names a recorded approval id that is in
approvals.jsonl, intact, matches project/kind/target, covered the recorded bounds when
the crawl started, and -- for a project declared `production` (D-088) -- is a
human-granted `production: true` row. The signature is verified when
AUTOTESTER_APPROVAL_KEY is available; without it (a clean checkout) the check says so.

    uv run python scripts/check_crawl_approval.py <project-slug>
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.core.consent import ApprovalRequired, is_account_derived, require_approval
from autotester.core.env import load_repo_env
from autotester.core.ids import APPROVAL_KEY_ENV
from autotester.schema.enums import ApprovalKind, CrawlStatus
from autotester.store.project_store import ProjectStore


def _fail(msg: str) -> int:
    print(f"FAIL  {msg}")
    return 1


def main() -> int:
    load_repo_env()  # AT-110: signatures are verified when the key is in .env
    if len(sys.argv) != 2:
        print("usage: check_crawl_approval.py <project-slug>")
        return 2
    slug = sys.argv[1]
    store = ProjectStore(slug)
    project = store.load_project()
    if project is None:
        return _fail(f"no project '{slug}'")
    done = [s for s in store.list_crawl_summaries()
            if s.status is not CrawlStatus.RUNNING and s.finished_at]
    if not done:
        return _fail(f"no tracked crawl summary for '{slug}' (projects/{slug}/crawl_summaries/)")
    latest = done[0]
    if not latest.approval_id:
        return _fail(f"crawl {latest.crawl_id} records no gating approval id")
    row = next((a for a in store.list_approvals() if a.id == latest.approval_id), None)
    if row is None:
        return _fail(f"crawl {latest.crawl_id}: recorded approval {latest.approval_id} "
                     "is not in approvals.jsonl")
    if project.production or latest.project_production:
        if not (row.production and latest.approval_production):
            return _fail(f"crawl {latest.crawl_id}: production project but approval "
                         f"{row.id} is not production:true")
        if is_account_derived(row):
            return _fail(f"crawl {latest.crawl_id}: production project but approval "
                         f"{row.id} is account-derived ({row.granted_by})")
    verify = bool(os.environ.get(APPROVAL_KEY_ENV))
    try:
        if verify:
            require_approval(
                [row], project=slug, kind=ApprovalKind.CRAWL, target=project.base_url,
                actions=latest.bounds.max_actions, wall_clock_s=latest.bounds.wall_clock_s,
                production=project.production or latest.project_production,
                now=datetime.fromisoformat(latest.started_at) if latest.started_at else None)
        elif not (row.is_intact and row.signature and row.target == project.base_url
                  and row.project == slug and row.run_kind is ApprovalKind.CRAWL):
            return _fail(f"approval {row.id} is edited, unsigned or for another target/kind")
    except ApprovalRequired as exc:
        return _fail(f"crawl {latest.crawl_id} ran but approval {row.id} does not cover it:\n{exc}")
    sig = "signature verified" if verify else "signature NOT verified (no approval key here)"
    print(
        f"PASS  crawl {latest.crawl_id} ({latest.status.value}, stop_reason={latest.stop_reason}, "
        f"{latest.screens} screens, {latest.denied} refused) gated by approval {row.id} "
        f"production={row.production} granted by {row.granted_by}; {sig}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
