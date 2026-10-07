# Verdict: at113-crawl-completion (Mode A, cycle 4)

Date: 2026-10-07 · Bound to D:/autoTesting · code under check: worktree `.worktrees/at113-crawl-completion`, branch `codex/at113-crawl-completion`, commit 9f651068b40f6fed1b49887d19ea67902c60fe2c (parent 085537cd = base)
Cycle checked: 4
Policy-Version: proportional-verification/2026-10-06.6 (as pinned); .7 in-flight rules applied (no per-unit full suite, impact-based reuse, one checker)
Verdict path: qa/verdicts/at113-crawl-completion.md · Checkpoint: qa/checkpoints/at113-crawl-completion.md
The cycle-3 verdict was kept as qa/verdicts/at113-crawl-completion.r3-1.md. `.b.md` is the cycle-3 side-B verdict and was not read or touched (cycle 4 is a single check).

## Check plan (step 0)

Diff 085537cd..9f651068 = 2 files: `src/autotester/stages/explore_typing.py` (type_form), `tests/test_explore_typing_guards.py`. Both are exactly the cycle-4 "What changed" list; no deletion or rename of any function, class, route, config key or test (4c: only the original `max_actions`-only guard in the field loop was folded into the shared `explore.stop_reason(rt)`, plus three added rechecks; the old docstring was shortened, not a behaviour removal).

| Signal | Check | Result |
|---|---|---|
| Logic changed (bound timing, form writes) | focused set + falsification floor | done |
| Browser-visible behaviour (FILL, navigation) | headed live fixture, BFS and hybrid | done (Mode D) |
| X4 re-run end to end (failed in cycle 3) | headed fixture + 16-case guard test | done |
| X16, X18, CR4, CR5, C12 inputs unchanged | reuse by impact; also re-ran in the focused set | done |
| Security/auth/tenancy/prod write | none | not triggered, so no full suite |

TIER: L. Cited trigger: `src/autotester/stages/explore_typing.py:108-126` is product code inside the critical X4 scope (timing/bound latch, form writes). One checker (not dual: no security/auth/tenancy or production-write trigger). `full-suite trigger: none`.

## Evidence (all re-run by me)

1. **Focused set**, run in the worktree: `uv run pytest tests/test_explore_typing_guards.py tests/test_explore_blocked.py tests/test_explore_node_recovery.py tests/test_crawl_status_surfaces.py tests/test_explore_completeness.py tests/test_explore_traversal.py tests/test_persona_changes.py` -> **126 passed** (355 s; 2 warnings, both a `.pytest_cache` access-denied warning on the worktree).
2. **`tests/test_crawl_inventory_live.py` in isolation**: **2 passed** (257 s). No timing failure observed.
3. `uv run ruff check src tests scripts` -> All checks passed.
4. `uv run autotester doctor` -> one violation, `ledger-row-missing: T-171` (a closed task with no ledger row). It concerns `docs/FEATURES.jsonl` and `.goal`, not a changed file, and the manifest records it as pre-existing at cycle 2. Not charged to this unit; low ledger row (below).
5. **Headed X4 fixture** (my own script, `qa/evidence/browser-at113-crawl-completion-2026-10-07-checker/x4_headed.py`, a real visible Chromium, local HTTP server logging every request, `Cache-Control: no-store`): root -> `/fill-child` -> FILL `#trigger` (its `input` handler navigates to `/fill-out`, depth 2) with `max_depth=1`, policy TEST_ACCOUNT + synthetic_typing, `max_actions=50`.
   - BFS: status `stopped_bound`, stop_reason `max_depth`, actions 2; request log ends `... /log?field=trigger, /fill-out`; **requests after `/fill-out`: none**; `#second` never filled.
   - HYBRID: identical result.
   - Report: `.../browser-at113-crawl-completion-2026-10-07-checker/report.json`. No console errors are applicable (the fixture pages run no scripts beyond the handlers).
6. **Live falsification of the fixture itself (green-before/red-after, in throwaway copies outside the bound root, copy checked via `autotester.__file__`):**
   - copy with the cycle-3 `explore_typing.py` (085537cd): BFS and hybrid both show requests after `/fill-out` = `['/fill-child', '/log?field=second']`, `second_filled=true` -> RED (reproduces the cycle-3 defect).
   - copy with the post-FILL and post-heartbeat guards deleted: BFS and hybrid both show `['/fill-child']` after `/fill-out` (a `return_to` navigation) -> RED.
   - the cycle-4 source: nothing after `/fill-out` -> GREEN.
7. **Unit falsification (floor: >=1 per criterion, X4 is the failed one), batch runner, one isolated copy per row**, node `tests/test_explore_typing_guards.py -k followup` (16 cases, green in the unedited copy first):
   - F1 delete post-FILL guard (`explore_typing.py:119-121`) -> 4 failed, all `after_fill-*`, assertion `calls == ['fill']` fired (`['fill','heartbeat']`).
   - F2 delete post-heartbeat guard (`:124-126`) -> 4 failed, all `after_heartbeat-*`, `['fill','heartbeat','restore'] != ['fill','heartbeat']`.
   - F3 delete pre-FILL guard (`:108-110`) -> 4 failed, all `after_eligibility-*`, `actions_used` 1 where 0 was expected.
   - Each edit reddens exactly its own phase and the named assertion is the one that fired (not an import or load error). The bound tree was never edited.
8. **4c diff scope:** `git diff 085537cd 9f651068 --stat` = the two files above, +67/-20. The base is an ancestor of HEAD and equals `9f651068^`. The commit carries only those paths (C10).

## Criteria

- **X4 [explore.md]**: MET. Bounds are rechecked before every node and action, and now also after the eligibility/policy checks, after the FILL and after the heartbeat in `type_form`; once any bound has latched, no FILL, heartbeat, `return_to` or replay runs, and the fired bound is retained in `rt.stop_reason`. Evidence: items 5-7 (live BFS and hybrid, 16-case guard test, three isolated falsifications, cycle-3 source reproduces red).
- **X16, X18**: MET, by impact: their input files (explore_status, crawl_report, cli_crawl, crawl_view, routes_crawls, explore.py) are byte-unchanged since 085537cd; the status-surface, blocked and completeness tests in the focused set pass.
- **CR4, CR5**: MET, same reuse; `test_explore_node_recovery`, `test_explore_completeness`, `test_persona_changes`, `test_explore_traversal` pass.
- **C7**: holds (falsification per criterion in copies, green-before/red-after, tree untouched). **C10**: holds (2-path commit, branch before check, no master merge yet). **C12**: holds (a bound latches and the typing path stops; the bound is never silenced).

## Non-blocking findings (ledger rows, not failures)

- low: `autotester doctor` reports `ledger-row-missing: T-171`, pre-existing and outside this diff.
- low: the manifest's cycle-4 section has no "Capability coverage" table (only the falsification line in "Builder evidence"). Under the pinned .6 format this is not a FAIL; the floor was met by my own falsifications above.
- low (process): the manifest asks for one serial full `uv run pytest` and a re-attribution of the 24 baseline failures. Under .7 and the dispatch (`full-suite trigger: none`) it was not run here; the maker's pre-push integration check (step 6c) owns it. The 24 baseline failures stay unwaived there.

## Push

The unit's code is on `codex/at113-crawl-completion` and has not been merged to master (C10 merge is the maker's step after this PASS). Local master is behind origin/master by 43 commits, so the verdict commit cannot fast-forward. The push result is stated in the final report.

VERDICT: PASS
SCOREBOARD: 5/5 criteria met (X4, X16, X18, CR4, CR5), 3/3 invariants hold (C7, C10, C12)
TIER: L (product code inside the critical X4 scope: `explore_typing.py:108-126`, form writes and bound timing)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 unit rows reproduced (F1, F2, F3) plus 2 live-fixture falsifications (cycle-3 source, guards removed)
LIVE-BROWSER: qa/evidence/browser-at113-crawl-completion-2026-10-07-checker/
ISSUES-WRITTEN: none (three low rows named above; the maker may file them, a single checker PASS writes no ledger flip for goal closure)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: After a bound latches, `type_form` no longer performs a FILL, heartbeat or `return_to`; the headed BFS and hybrid fixture shows zero requests after `/fill-out` and no FILL on `#second`, where the cycle-3 source reproduces both. The 126-test focused set and the isolated inventory-live test are green, and each of the three new guards is isolated by its own falsification.
Metrics: start=2026-10-07T09:17Z end=2026-10-07T09:36Z wall_min=19 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=4 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
