# Verdict - at656-status-by-id

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** bdfd4c5f642dd1bd260640f1921995f9dcc6f461 (base fcedc9f4 = git merge-base HEAD master; checked on HEAD 6f1b6801329db81735cd0c17c7b8f13b6547e774, manifest-only commit on top)
**Policy-Version:** proportional-verification/2026-10-15.12
**Tier:** S (confirmed: one reader function plus its tests; no L trigger). LANE: none (lane disabled, normal check).

## Check plan
Criterion C1 = AT-656 issue text, expected part (2): `_status_by_id` must not collapse a repeated id into one clean status; verified by construction (C12b). Part (1) (duplicate-id reporting) is already shipped at base in ledger/issue_ids.py:119-123 (`issue-id-duplicate`), part (3) is prose allocation; neither is in this diff.

## Independent checks (run by me)
- `uv run pytest tests/test_ledger_checks.py tests/test_issue_ids.py` -> 41 passed.
- `uv run ruff check src tests scripts` -> All checks passed.
- `uv run autotester doctor` -> doctor: clean. checks.py 298 lines, test file 299 (<=300).
- Falsification (floor, 1 per criterion), throwaway copy outside the worktree (git archive HEAD, checks.py restored to fcedc9f4 last-wins `out[id] = status`): green before = 41 passed; red after = 4 failed on the named assertions: `assert ('ledger-row-stale' in []) is True` (open/verified and open/fixed) and `assert 'verified' not in {'fixed','open','verified'}` (reader). Worktree untouched.

## Review (step 4c, diff read in full)
- checks.py:141-157: collects all statuses per id; len 1 -> plain status, else `conflict:<sorted distinct>`. A fully identical twin pair (verified,verified) also reads as conflict, never a plain status, matching the "cannot mistake for a single status" wording.
- `_is_open` (:158-160) true for plain `open` or a conflict containing `open`; sole consumer check_qa_issue_rows :198. The only other use of the dict, `named - set(status_of)` (:189), is membership only and unaffected.
- No other reader of `_status_by_id` in src, tests or scripts (grep).
- Diff is confined to the ledger reader and its tests; no security/auth/prod-write surface.

## Findings
None blocking. defects_unit=0.

Metrics: start=2026-10-17T10:00:00Z end=2026-10-17T10:08:00Z wall_min=8 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=300 mutants=0 defects_unit=0 defects_6c=0
