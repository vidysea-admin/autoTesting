# Verdict - crawl-approval-by-id

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** 98ecbb3825227b96688d186d91d05424db903738 (base 69ebfae7d039e8bf426206882b417d882822075e via git merge-base HEAD master; code commit b85086f4)

## Plan
AT-999 (script judges only git-tracked crawl summaries; optional crawl id). Diff since base: scripts/check_crawl_approval.py, tests/test_check_crawl_approval.py, the manifest. Tier L as dispatched (approval-gate script); no change to RunApproval/HMAC verification or to what a signed approval authorizes (require_approval call and row checks untouched, diff lines 100-125 of the script are context), so no dual check. Lane: not applicable (cycle 0 L, lane disabled by default); lane=normal.

## Independent checks
- uv run pytest tests/test_check_crawl_approval.py -> 4 passed in 69.95s, rc 0.
- uv run ruff check src tests scripts -> All checks passed, rc 0.
- uv run autotester doctor -> doctor: clean, rc 0.
- Falsification, floor 1 for C1, in copies outside the worktree (scripts + test only, run with the worktree venv python):
  - row1 (base-version script restored): green 4 passed, then red 4 failed on assert (1 == 0), (2 == 0), (2 == 1), (0 == 1) in the four named tests.
  - row2 (replace tracked = _tracked_ids(store) with all on-disk ids): green 4 passed, then red 3 failed, 1 passed, on assert (1 == 0) in test_untracked_newer_leftover_summary_is_not_judged..., assert (0 == 1) in test_a_crawl_id_naming_an_untracked_summary_is_refused... and test_only_untracked_summaries_fail_closed. The assertions that fire are the ones the tests are named for.

## Review (step 4c, diff read in full)
- _tracked_ids (script :45-54) uses git ls-files -z -- <crawl_summaries_dir>; OSError or CalledProcessError yields an empty set, so a git failure fails closed. _pick_summary (:57-68) rejects an untracked crawl id with an error, otherwise filters finished summaries to tracked ids and, with an id, to that id; ordering stays newest-first from list_crawl_summaries. main (:71-120) accepts 1 or 2 args, exit 2 otherwise (CN8 usage exit preserved). Both directions (exit 0 and exit 1) are exercised by the tests on constructed state (CN8).
- Nothing removed besides the docstring wording and the old inline filter; no files outside the declared scope; tests add only new nodes.
- Contract CN8 (qa/contracts/consent.md:130-137) still holds. Criterion C1 (issue text: take a crawl id, judge only committed summaries): met.

## Non-blocking observations (not filed as ledger rows, to avoid id collisions with the main checkout's pending issues.jsonl edits; maker to file if wanted)
- low: git ls-files reads the index, so a summary that is staged but not committed counts as tracked. The issue text says committed; no test covers it. Wording-level, no FAIL.
- low: a tracked summary modified in the working tree is judged on its working-tree content. Same class.

Metrics: start=2026-10-17T22:00:00+05:30 end=2026-10-17T22:09:00+05:30 wall_min=9 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=540 mutants=0 defects_unit=0 defects_6c=0
