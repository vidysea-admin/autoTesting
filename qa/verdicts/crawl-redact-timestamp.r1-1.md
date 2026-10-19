# Verdict - crawl-redact-timestamp (Mode A repair check, single checker under dual-waiver)

**Verdict:** FAIL
**Cycle checked:** 1
**Head checked:** 943b0655 (repair base 6e94d128 verified with git), worktree .worktrees/crawl-redact-timestamp
Policy-Version: proportional-verification/2026-10-19.17
Tier: S (test-only repair of a checker-reviewed unit; repair checker mandatory at cycle >= 1). Dual-waiver accepted: the diff changes no product line (0 lines in explore_summary.py), so no security behaviour changed; not raised to dual.

Metrics: start=2026-10-19T18:50Z end=2026-10-19T18:57Z wall_min=7 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=420 mutants=0 defects_unit=1 defects_6c=0

## Why FAIL (one defect, evidenced)
`uv run autotester doctor` (qa/adapter.json:24, a project verify command) is RED on this head: `file-too-long: tests\test_explore_replay.py - 301 lines > 300; split by responsibility` (summary "1 violation(s)"; the other output lines are non-blocking advisory decision-citation findings). The repair added 4 lines to a 297-line file (`git show 6e94d128:tests/test_explore_replay.py | wc -l` = 297; head = 301), crossing the CLAUDE.md design rule "File <= 300 lines". Cycle 0 recorded `doctor: clean`, so the repair introduced it. Cited line read: tests/test_explore_replay.py:85-87 is the added method, 301 lines total.
Smallest fix (maker's call, test-only): drop the 2-line comment at :86-87 (or fold the method onto fewer lines) so the file is <= 300, then re-run doctor. No behaviour change is needed.

## Everything else in scope is green
- Diff read in full, `git diff 6e94d128..943b0655 --stat`: 2 files, `tests/test_explore_replay.py` (+4) and `qa/manifests/crawl-redact-timestamp.md`. Test-only: CONFIRMED; no src, conftest, fixture or contract touched.
- Interface match: real `core/redact.py` `Redactor` has `scrub(self, text: str) -> str` (:125) and `scrub_obj(self, obj)` (:134); the double now has both (test_explore_replay.py:85,89). The product call is `redactor.scrub(value)` at stages/explore_summary.py:69 (key not in `_MINTED`); `scrubbed` calls only `rt.session.secrets.redactor()` (:79).
- Other doubles reachable from `explore_summary.scrubbed` (callers explore.py:156, explore_incremental.py:135, explore_node.py:72/85/120/184, explore_summary.py:102): grep of tests/ for `def redactor` / redactor lambdas / `_Redactor` / `_Secrets` found only test_explore_replay.py. Others are not reachable: tests/test_crawl_coverage_bounds.py:112 and test_platform_links.py:92 / test_probe_floor_matches_runtime.py:53 expose only `scrub_optional` and never call `scrubbed`; test_ui_runs_target_closed.py:72 has a `scrub` lambda; test_failure_bundle.py:223 and test_trace_numeric_secret.py:79 subclass the real `Redactor`. No second broken double.
- Re-run by me: `uv run pytest tests/test_explore_replay.py tests/test_crawl_redact_timestamp.py` -> 16 passed in 36 s (includes the 4 failed nodes: `...off_domain_is_refused_and_recorded[click]`, `[fill]`, `test_the_off_domain_replay_refusal_is_recorded_as_an_edge_a_surface_can_show`, `test_a_refill_that_leaves_the_domain_is_caught_before_the_submit_is_clicked`).
- Falsification (floor, 1 for C1-repair), in a `git archive 943b0655` copy (scratchpad check-crawl-redact-c1/copy), PYTHONPATH on the copy src: control, the 4 nodes -> 4 passed; `scrub` removed from the double -> 4 failed, each `AttributeError: '_Redactor' object has no attribute 'scrub'` at explore_summary.py:67; restored by discarding the copy (bound tree untouched, `git status` clean).
- `ruff check tests/test_explore_replay.py` -> All checks passed.
- C2/C3 not repeated (inputs untouched).

## PROPOSED-ISSUE (none beyond the FAIL)
None. (The doctor red is the FAIL itself, not a ledger row.)

## Next
Maker cycle 2 (final cap, .9-18: Opus escalation per policy): the one-line size fix above, then ready-for-check; a doctor run on the final SHA should be recorded in the manifest Pre-check.
