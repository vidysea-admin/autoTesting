# Verdict: fix6c-approval-tests

Verdict: PASS
Status: PASS
Cycle checked: 1
Reviewed SHA: c052e373 (fix commit e4c8e662; test-only)
Repair base: 7b16f66b (verified ancestor of HEAD; `git merge-base HEAD int/1017` = 7b16f66b)
Tier: L (protected-test scope of the crawl-approval gate), single checker
Policy: proportional-verification/2026-10-17.13

## Check plan
Logic = test fixtures only. Affected tests + falsification floor (1 per repaired test group). No UI, no persona walk, no live check. Lane check not applicable (repair cycle).

## C1 - the 4 reds pass again while still guarding their named property: MET
- Diff read in full (`git diff 7b16f66b..e4c8e662`): tests/test_approval_prod_gate.py +15 (import subprocess, helper `_track_summaries` at :169, calls at :188, :200, :216), tests/test_approval_prod_gate_paths.py +3/-1 (import + call at :148). Pure additions in the test bodies: no assertion removed or edited, no skip/xfail (grep: none), no threshold change.
- scripts/ and src/ untouched in 7b16f66b..HEAD (`git diff --stat -- scripts src` empty). The AT-999 tracked-only rule (`scripts/check_crawl_approval.py:45-67`, `git ls-files`) is intact.
- Helper is genuine: it runs a real `git init` + `git add -A -- projects` + `git commit` in the tmp project root (the same root the script's `git -C store.paths.root ls-files` reads); it does not bypass the tracked check. Mutant d below proves it.
- Verify commands (run by me in the worktree): `uv run pytest` on the 4 files -> 63 passed (150 s, machine busy with parallel mutants); `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean.

## Falsification (copies OUTSIDE the worktree, PYTHONPATH confirmed to the copy's src; `-k done_check`, 2 files)
Green-before (unmutated copy g): 5 passed. Then one mutant per test, each red on the named test:
| Test | Mutant (copy) | Result |
|---|---|---|
| test_done_check_fails_when_a_production_project_was_gated_by_a_non_production_row | script production-approval gate `if project.production or latest.project_production:` -> `if False:` | RED on that test only (1 failed, 4 passed) |
| test_done_check_fails_without_a_recorded_approval_id | `if not latest.approval_id:` -> `if False:` | RED on that test only |
| test_done_check_fails_closed_for_production_without_the_key | key-missing fail-closed `... and not verify:` -> `if False:` | RED on that test only |
| test_done_check_passes_from_summary_alone_for_a_production_row (+ all 4) | `_track_summaries` body made a no-op (tests' tracking removed) | 4 failed, all with `FAIL no tracked crawl summary for 'demo'`, i.e. the tracked-only rule still bites and the helper is what satisfies it (not an import error) |

## Findings
None blocking. PROPOSED-ISSUE (low, not a FAIL): the helper commits with `git add -A -- projects` and passes `-c user.name/email` per call; it needs `git` on PATH, same as the script under test. No action needed.
(Out of scope, already in the integration verdict: the 5th red test_cli_advice_resolves::test_no_advice_site_can_vanish_unnoticed is a different unit's, not this repair.)

Invariants: [I*] none-touched (test fixtures only)

Metrics: start=2026-10-18T00:02 end=2026-10-18T00:17 wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=900 mutants=4 defects_unit=0 defects_6c=0
