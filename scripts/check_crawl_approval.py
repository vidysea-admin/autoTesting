"""T-145's done_check (D-018): a live crawl counts as done only if it actually
ran AND a matching human approval covered it.

Replaces `{"cmd": "true"}` — a check that could never fail, on the highest-risk
task in the plan. Exits 0 only when the judged crawl summary names a recorded approval id that is in
approvals.jsonl, intact, matches project/kind/target, covered the recorded bounds when
the crawl started, and -- for a project declared `production` (D-088) -- is a
human-granted `production: true` row. The signature is verified when
AUTOTESTER_APPROVAL_KEY is available; without it (a clean checkout) a non-production project
passes with "signature NOT verified", but a production project FAILS (a content hash is
forgeable by anyone who can edit approvals.jsonl).

    uv run python scripts/check_crawl_approval.py <project-slug> [<crawl-id>]

Only COMMITTED summaries (`git ls-files projects/<slug>/crawl_summaries/`, written when a crawl
finishes; the full crawl dir is gitignored, so a clean checkout has only these) are judged
(AT-999): an untracked leftover on disk is never picked up. With `<crawl-id>` that tracked
summary is judged; without it, the newest tracked one. A `<crawl-id>` that is not tracked
FAILS. If git cannot list the files the check fails closed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.core.consent import ApprovalRequired, is_account_derived, require_approval
from autotester.core.env import load_repo_env
from autotester.core.ids import APPROVAL_KEY_ENV
from autotester.schema.crawl_summary import CrawlSummary
from autotester.schema.enums import ApprovalKind, CrawlStatus
from autotester.store.project_store import ProjectStore


def _fail(msg: str) -> int:
    print(f"FAIL  {msg}")
    return 1


def _tracked_ids(store: ProjectStore) -> set[str]:
    """Crawl ids whose summary file git tracks (AT-999). Empty when git cannot say (fail closed)."""
    folder = store.paths.crawl_summaries_dir
    try:
        out = subprocess.run(
            ["git", "-C", str(store.paths.root), "ls-files", "-z", "--", str(folder)],
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {Path(p).stem for p in out.split("\0") if p.endswith(".json")}


def _pick_summary(store: ProjectStore, slug: str, want: str | None) -> CrawlSummary | str:
    """The tracked, finished summary to judge: `want` if given, else the newest. Or an error."""
    tracked = _tracked_ids(store)
    if want is not None and want not in tracked:
        return (f"crawl {want} is not tracked by git (no committed "
                f"projects/{slug}/crawl_summaries/{want}.json); commit its summary first")
    done = [s for s in store.list_crawl_summaries() if s.crawl_id in tracked
            and s.status is not CrawlStatus.RUNNING and s.finished_at
            and (want is None or s.crawl_id == want)]
    if not done:
        return f"no tracked crawl summary for '{slug}' (projects/{slug}/crawl_summaries/)"
    return done[0]


def main() -> int:
    load_repo_env()  # AT-110: signatures are verified when the key is in .env
    if len(sys.argv) not in (2, 3):
        print("usage: check_crawl_approval.py <project-slug> [<crawl-id>]")
        return 2
    slug, want = sys.argv[1], (sys.argv[2:] or [None])[0]
    store = ProjectStore(slug)
    project = store.load_project()
    if project is None:
        return _fail(f"no project '{slug}'")
    latest = _pick_summary(store, slug, want)
    if isinstance(latest, str):
        return _fail(latest)
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
    if (project.production or latest.project_production) and not verify:
        return _fail(f"crawl {latest.crawl_id}: production project and {APPROVAL_KEY_ENV} is not "
                     f"set here, so approval {row.id}'s signature cannot be verified; a content "
                     "hash is forgeable. Run this where the approval key is available")
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
