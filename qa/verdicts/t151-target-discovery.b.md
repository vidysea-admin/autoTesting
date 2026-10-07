# Verdict B — t151-target-discovery (cycle 3, narrow repair check, coordinator B)

Cycle checked: 3
Date: 2026-10-07
Bound to: D:/autoTesting (worktree D:/autoTesting/.worktrees/t151-target-discovery, HEAD a0820901, cycle-3 fix 4ffde8fe)
Policy: proportional-verification/2026-10-06.6 · Tier L, dual check (coordinator B, blind to A). Scope: X17 only (narrow cycle authorised by Umesh via the cycle-2 stalled gate, answer A).
Archive: the cycle-2 verdict (Cycle checked: 2) is preserved in git history at bfe2ecda; no same-cycle file existed, so nothing was renamed.

## Check plan (step 0)

Cycle-3 diff is test-only plus manifest (4ffde8fe: tests/test_discover_hardening.py +18, manifest). A master merge (6a3a2503) landed after it, so one full suite is owed. Plan: (1) read the in-loop deadline check in product code myself; (2) run the named test, then both discover files; (3) own falsification of that check in a throwaway copy; (4) diff scope; (5) lint, doctor; (6) exactly one full suite in the worktree. No UI surface, no walks.

## X17 — deadline is checked inside the scan emission loop

Product code, read by me this check: src/autotester/stages/discover.py lines 201-213, `_emit`: the `for kind, line, detail in facts:` loop opens with `if time.monotonic() - started >= scope.limits.wall_clock_s:` (line 208), then `_refuse(result, path, "wall_clock_s", redactor)` and `return False`, before each `result.signals.append(...)`. The check is per Signal, inside the loop. Product files are unchanged by the cycle-3 commit (git show --stat 4ffde8fe: manifest and test only).

Committed defender: tests/test_discover_hardening.py::test_deadline_is_checked_inside_the_scan_emission_loop (line 160). It drives `scan` over a 500-line `import openai` file with a clock advanced 1 s per `Redactor.scrub` and `wall_clock_s=5`, and asserts `complete` is False, a `wall_clock_s` refusal, and fewer than 50 Signals and scrub calls.

Falsification (copy from git archive HEAD in scratch, outside the bound tree; interpreter = the worktree venv with PYTHONPATH pointing at the copy, import path verified to resolve to the copy):
- green before, in the copy: `1 passed`.
- mutant: discover.py line 208 only, `if time.monotonic() - started >= scope.limits.wall_clock_s:` -> `if False:` (diff vs the original, ignoring CR, is exactly that one line). Result: `1 failed`, assertion `assert (500 < 50)` on `len(result.signals) < 50` (the named assertion for this check). All of tests/test_discover.py + tests/test_discover_hardening.py under the same mutant: `1 failed, 90 passed`, so the new test is the sole defender and it fires for the right reason.
- restored (byte-identical to the archive copy, cmp): `1 passed`.
(A first attempt used a sed that also matched the three other deadline checks in the same file; I discarded it and redid the row single-site. The single-site result above is the evidence.)

Affected tests, copy of HEAD: tests/test_discover.py + tests/test_discover_hardening.py: `91 passed` (63 + 28), matching the manifest.

## Diff scope (4c)

`git diff 4ffde8fe^ 4ffde8fe --stat`: tests/test_discover_hardening.py (+18, nothing removed) and the manifest. Base 4ffde8fe^ is an ancestor of HEAD. Since 4ffde8fe^ the only other src/tests changes are the master merge's (src/autotester/stages/ingest.py, tests/test_ingest.py); `git diff 4ffde8fe^ HEAD -- src/autotester/stages/discover.py` is empty. Against master 478cc5fb the branch changes only the T-151 files (pyproject.toml, uv.lock, ai_target schema, discover, read_context, text_lines, credential_files, prompt, mock.py act hunk, the two discover test files). Nothing deleted or renamed.

## Lint, doctor, full suite

- `uv run ruff check src tests scripts`: `All checks passed!`
- `uv run autotester doctor`: `doctor: clean`.
- Full suite, one run, no -q, no -x, worktree: `uv run pytest` -> `2 failed, 2291 passed, 5 skipped, 14 xfailed in 2256.38s (0:37:36)` (run under heavy concurrent load from other sessions' suites). The 2 failures are not caused by this unit:
  - tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered fails on `assert all(value in dashboard for value in facts)` (.goal/dashboard.html stale against goal.json). Identical failure in a plain `git archive 478cc5fb` of master, and `.goal` and plan.md are byte-identical between master and this branch.
  - tests/test_ui_runs_serial_entry_mix_live.py::test_a_serial_run_mixing_an_entry_case_with_ordinary_cases_does_not_500 fails with HTTP 403 "no approval exists" for the live_case run (consent change 1fdba241 on master; the test was not updated). Fails the same way in the master archive; the test file, src/autotester/ui and src/autotester/core are byte-identical between master and this branch. It fails in isolation too (not load related).
  No test in a file touched by this diff failed.

## PROPOSED-ISSUE lines

PROPOSED-ISSUE: {"severity":"medium","feature":"goal-dashboard","title":"tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered fails on master: .goal/dashboard.html out of sync with goal.json","evidence":"fails in a git archive of master 478cc5fb and on the t151 branch (files identical to master); assertion all(value in dashboard for value in facts)","fix_direction":"regenerate the dashboard on master and commit it"}
PROPOSED-ISSUE: {"severity":"medium","feature":"ui-runs","title":"tests/test_ui_runs_serial_entry_mix_live.py fails on master: live_case run now refused 403 without approval (consent change 1fdba241), the test never grants one","evidence":"assert 403 == 303 'no approval exists for it' in the worktree and in a master archive, isolated and in the full suite","fix_direction":"have the test grant a live_case approval for the fixture host, or follow the consent contract for the isolated AUTOTESTER_ROOT"}

## Block

VERDICT: PASS
SCOREBOARD: X17 1/1 evidenced (in-loop per-Signal deadline read at discover.py:208, sole defender goes green->red->green) · other criteria out of scope this cycle (their cycle-2 evidence is unchanged: no product file changed since) · invariants hold
TIER: L (credential, path-escape and approval boundary plus dependency bump, per manifest; the cycle-3 diff itself is test-only, tier unchanged)
FAILURES: none (the two full-suite failures are master-borne and in files this diff does not touch; reported as PROPOSED-ISSUE, not a FAIL)
CAPABILITY-COVERAGE: 1/1 rows reproduced for this cycle's row (X17 / scan _emit deadline: green -> red -> green, single-site, own copy); rows R01-R16 from cycle 2 unchanged, product files byte-identical since
LIVE-BROWSER: not-applicable (changed paths: tests/test_discover_hardening.py and the manifest; no UI surface)
ISSUES-WRITTEN: none (dual check; PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent; self != executor)
EXPLANATION: The only cycle-2 failure was an undefended per-Signal deadline check in the scan emission loop; the committed test now defends it, and disabling exactly that line turns exactly that test red on the named assertion while the 90 other discover tests stay green. Lint, doctor and the discover tests are green; the one full suite has 2 failures that reproduce identically on a clean master archive and sit in files this branch does not change.
Metrics: start=2026-10-07T13:38:27+05:30 end=2026-10-07T14:21:27+05:30 wall_min=43 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=2 cycle=3 resumes=0 tokens=unavailable policy=2026-10-06.6
