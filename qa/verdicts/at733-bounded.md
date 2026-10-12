# Verdict: at733-bounded (AT-733, ui-run RU5)
Cycle checked: 0 · Checked sha: 32c18947 (code b07cc727, base 057b6dbb) · Policy-Version: proportional-verification/2026-10-10.9 · Dual check: no
Lane: quick lane off (adapter lane.enabled absent), normal check. Resume: 0 of 2 · Retry: 0

## Plan
Tier M (two callers of a shared module + test file; no security/auth/tenancy/prod-write). Checks: RU5 acceptance (affected tests re-run, pre-check t=4 s < 30 s so not reused), 1 falsification in a copy, step 4c diff read, real Windows locked-file probe, presence-check-raises probe, doctor/ruff. No UI surface changed (diff is ui/run_execution.py server-side + one test file): browser check judged not necessary.

VERDICT: PASS
SCOREBOARD: 1/1 criteria met (RU5), invariants: C12(b) holds (fail closed), C7 sabotage asserts it was applied
TIER: M (run_execution.py:90-104 shared by _run_cases_serially and _run_entry_cases; no L trigger in changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced (Falsify[RU5])
LIVE-BROWSER: not-applicable (changed paths: src/autotester/ui/run_execution.py, tests/test_ui_runs_serial_resilience.py)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all run by the checker)
- Affected tests, worktree venv, `-p no:xdist`: resilience + entry_order + entry_screenshot_namespace -> 30 passed (8+21+1), 21 s. Worktree clean afterwards.
- Falsification (copy `scratchpad/check-at733/row1`, git archive b07cc727, PYTHONPATH pointed at the copy, module path printed): resilience file green 8 passed; replaced the one `_wipe_entry_profile(...)` call with `shutil.rmtree(entry_paths.profile_dir, ignore_errors=True)` (anchor matched once, diff shows the single changed line) -> 4 failed 4 passed. leaves-directory-1/-2 red on `assert COMPLETED is ERRORED` (the entry case ran on the leftover profile); raises-permission-error-1/-2 red on the profile-path-in-error assertion. Control stayed green.
- Windows locked-file probe (real `_wipe_entry_profile`, file held open without share-delete): OSError "entry profile not removed: <path> (PermissionError: [WinError 32] ...)", directory still present; after closing the handle the wipe succeeds and a second call on the absent directory returns without error.
- Presence check raising: `Path.exists` patched to raise PermissionError -> OSError naming the path (fail closed; not covered by a committed test, see low note).
- Diff read in full (4c): 2 product/test files + manifest, nothing deleted, no existing assertion edited; only imports (`shutil`, `pytest`) added to the existing test file. `session = None` / `if session is not None` keeps close() semantics. No unlisted file.
- `ruff check src tests scripts`: All checks passed. Files: run_execution.py 214, test file 300 lines.
- `autotester doctor` on a clean archive of master 354bd31f: `stale-generated: docs/SNAPSHOT.md ... 1 violation(s)`. Confirms the builder: pre-existing on master, not from this diff.

## Rulings on the builder's flags
1. Five nodes vs cap four: not a defect. RU5 Verify requires both stub modes at both widths plus the control; the contract governs the brief.
2. Fake grader delegating non-COMPLETED to the real `grade`: lives only in the new helper `_run_entry_and_sibling`; the three pre-existing tests are untouched, so no assertion was weakened and this is not a protected test change (tier stays M). It also makes the ERRORED path real (`grade` shortcut), which is the stronger form.
3. `raises-PermissionError` stub replaces `rmtree` outright: matches RU5's "separately stubbed to raise PermissionError". The genuine fail-open shape is leaves-directory, and that one is red under the falsification on its own named assertion.
4. Untagged duplicate `Pre-check:` line: wording/format, low, no cycle.
5. `stale-generated: docs/SNAPSHOT.md`: CONFIRMED pre-existing on a clean master archive.
6. Locked-file probe: run, see above (done at function level with a real open handle; end-to-end through a browser was not needed).

## Notes (non-blocking)
- low: no committed test for "presence check itself raises" (RU5 names it); code handles it (probe above). PROPOSED low ledger row only; not a unit.
- D-014 seam note: the checker skill has no seam-PASS counting step. By manual count, prior PASS verdicts on the entry-case seam (`_run_entry_case`): at044-entry-case-profile-isolation, at574-serial-resilience (2; at576-577 was FAIL; at567-file-splits PASS also touched run_execution.py, making it 3 if counted). Not security class (Dual check: no, no trigger). If the delivery gate counts this seam, this PASS may be the 3rd; the maker decides. The fix here is a distinct defect (AT-733) and RU5 is a new criterion.

EXPLANATION: RU5 is met on both callers: a failed or fail-open wipe now ends the entry case ERRORED with the profile path, never PASS, no BrowserSession, sibling and Run saved; the falsification reddens exactly the stub tests, and the real Windows locked-file probe ends in OSError. No merge or push done by the checker.
Metrics: start=2026-10-11T01:08:41+05:30 end=2026-10-11T01:16:00+05:30 wall_min=7 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=440 mutants=0 defects_unit=0 defects_6c=0
