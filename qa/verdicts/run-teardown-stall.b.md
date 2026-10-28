# Verdict - run-teardown-stall (checker B: contracts + adversarial)

**Cycle checked:** 1
**Verdict:** PASS (no blocking finding; two non-blocking residuals R1-R2 and one integration note N1)
**Checked:** branch fix/run-teardown-stall @ fd23a042 (the cycle-0 verdict at 7f887552 is in git history), worktree only. Source of intent: D-112 (docs/DECISIONS.md:2808 in the main checkout, "go with A"). Probes (gitignored): `.work/probe_clock_c1_b.py`, `.work/probe_clock_c1_b2.py`. No live run, no browser, no .env read.

## Commands run
- `pytest -o addopts= -p no:cacheprovider tests/test_run_teardown_stall.py tests/test_run_teardown_stall_wiring.py tests/test_run_budget_judge_time.py` (main venv, `PYTHONPATH=<worktree>/src`) -> `34 passed, 1 warning in 7.66s` (matches the manifest). Targeted set only (host low on memory; the other checker owns the sharded run).
- `python -m ruff check src tests scripts` -> `All checks passed!`
- `autotester doctor` (via `from autotester.cli import app`) -> `7 violation(s)`, all `decision-citation-dangling`: `qa/manifests/run-teardown-stall.md:53,54,61,82` cite D-112; `qa/verdicts/6c-1028-signup.md:4` and `qa/verdicts/run-teardown-stall.b.md:38` (cycle-0 text) cite D-110. No design-rule (size / duplicate / docstring) violation. See N1.

## Cycle-0 findings
- **F1 (double subtraction on overlap): CLOSED.** One shared `_ExcludedClock` (`run_budget.py:96`) is the only clock subtracted (`_browser_elapsed_locked`, `:135-137`); `_excluding` (`:112-122`) enters it plus the measuring-only kind clock under one lock, and `_ExcludedClock.enter/leave` (`:40-48`) count overlapping scopes as a union via `active`. Probe P1: 60 s inside both `judging()` and `housekeeping()` then 99 s acting -> charged 99.0 (cycle 0 gave a negative/zero charge). Test `test_overlapping_judge_and_housekeeping_subtract_their_union_once` passes.
- **F2 (exclusions not persisted): CLOSED.** `Run.excluded_s` (`schema/run.py:164`), set from `budget.excluded_report()` (`run_launcher.py:229`) via `ParallelPlan.excluded_s` (`parallel_run.py:62`) and saved at `run_launcher.py:265`; keys judging / housekeeping / total, `None` = not recorded. Wiring test `test_a_launched_run_records_phase_totals_and_unaccounted_seconds` passes. Probe P3: 200 s housekeeping, allowance 105 -> report `{judging 0, housekeeping 200, total 105}` (total is what was actually subtracted).
- **F3 (RAM compare outside try): CLOSED.** Compare and `print` are inside the `try` (`run_launcher.py:158-166`), `except Exception: return False`; `prepare_run` ignores the return (`:146`). Test `test_a_garbage_or_unprintable_measurement_never_raises_out_of_the_warning` passes.
- D-112 wording: `schema/approval.py:71-80` now says `wall_clock_s` = time ACTING on the target, judging / housekeeping held off up to bounded allowances; the inaccurate "in total" is gone. D-112 `Changes-authorized` (docs/DECISIONS.md:2820) covers `schema/approval.py` and the RunBudget module. `core/consent.py` (the 2000 / 24 h caps), `qa/contracts` and `docs/DECISIONS.md` are untouched by this diff (`git diff 7f887552 fd23a042 --stat -- src/autotester/core/consent.py qa/contracts docs/DECISIONS.md` is empty).

## Adversarial results (try to break the clock)
| # | Attack | Result | Evidence |
|---|---|---|---|
| P1 | judge + housekeeping overlap | union once | charged 99.0 after 60 s in both + 99 s acting |
| P2 | exception raised inside `judging()` / `housekeeping()` | state restored, exclusion still counted | `active` counters (0,0,0); total 10.0 after two 5 s scopes that raised (`_excluding` try/finally, `:117-122`) |
| P3 | allowance exhaustion | excess charged, also while still inside the scope | 200 s hk, allowance 105 -> charged 95.0; inside the scope at 105 s charged 0.0, at 115 s charged 10.0 |
| P3c | hk inside allowance, then acting | fail-closed boundary exact | hk 100 s, acting 99 s -> consume True; 101 s -> False (`stop_reason` wall_clock_s) |
| P4 | max real run time vs approval | `wall_clock_s + (45+60) * cases`, nothing more | n=1 refused at 205.0 s (=100+105); n=10 at 1150.0 s (=100+1050) |
| P5 | 3000 randomized interleavings (nested, cross-kind, out-of-order exits) vs invariants | 0 violations | total <= combined allowance, total >= largest single kind (capped), charged never negative |
| P6 | 8 real threads, 200 random scopes each with 10% raises, concurrent `try_consume` / `excluded_report` | no deadlock, no error, counters back to (0,0,0) | all threads exited within the join timeout |
| P7 | NaN / inf / negative allowance | all rejected with ValueError | `run_budget.py:87-89` |
| P8 | worker A in housekeeping while worker B acts on the target | B's acting time is NOT charged (0.0 for 60 s) | bounded by the combined allowance, see R1 |
| P9 | hung teardown that `cancel_inflight` cannot reach (fake context with no `_loop`, `close()` sleeping 3 s, timeout 1 s) | `close_session` returned after 3.0 s | see R2 |

Ceilings: the 2000-action and 24 h limits are grant-time caps (`core/consent.py:40-41`, `validate_grant_bounds`) and are untouched. The exclusion cannot raise them: P4 shows run time is at most the granted `wall_clock_s` plus the per-case allowances, which are derived from the case list (`for_cases`, `run_budget.py:105-110`) and finite-validated; `max_actions` / `max_probes` accounting (`_consume`, `:185-192`) is independent of the clock and unchanged. A `RunBudget(approval)` built without `for_cases` (`parallel_run.py:201` default) has zero allowances, so all housekeeping is charged: fail-closed. Contract PR7 (aggregate, never per worker, parallel-run.md:55) holds: one shared budget, one shared exclusion clock.

## Residuals (non-blocking)
- **R1 (bounded, by design).** The exclusion clock is global across workers: while any worker is in housekeeping or judging, another worker's target-acting seconds are not charged (P8). The leak is capped by the combined allowance (105 s per case, P4), so "bounds time ACTING on the target" is exact for a serial run and bounded-approximate (+105 s per case worst case) for a parallel one. This is the property `judging()` already had and cycle 0 disclosed; D-112 item 1 asks for one shared clock, not a per-worker one. No action unless Umesh wants per-worker accounting.
- **R2 (pre-existing class, newly visible).** `bounded_call` (`browser/teardown.py:48-72`) relies on `cancel_inflight` reaching the Playwright loop (`:33-45`). A step that does not block on that loop is not interrupted (P9), and the run clock is consulted only at `try_consume` / `remaining_ms`, never during a scope. So a truly wedged teardown is not cut by the budget; it is traced (`session_close.*`) and, past the allowance, charged once it returns. Cycle 0 live-probed the real Playwright path (hung request cancelled in 2.0 s) and the pre-change `close()` was equally unbounded, so this is not a regression.

## Integration note
- **N1.** `autotester doctor` shows the 7 dangling-citation rows because D-110 and D-112 exist only in the uncommitted `docs/DECISIONS.md` of the main checkout (`git -C D:/autoTesting diff --stat -- docs/DECISIONS.md` -> 42 insertions), not on this branch. Not a code defect; the doctor clears these once D-110 / D-112 are committed to master before or with the merge. Do not copy DECISIONS into this branch (append-only, one write path).
- Cycle-0 D1 (a consent.md CN10 / parallel-run.md PR7 note that `wall_clock_s` is the target-acting clock) is now authorized by D-112 (`Changes-authorized`: "the consent contract's wall-clock criterion (checker only)"). The contract is the checker's to amend, at the landing step; not required for this PASS.

## Result
PASS, cycle 1, on the contracts-and-adversarial axis. F1, F2, F3 closed with probe and test evidence; the clock could not be made to exceed `wall_clock_s` plus the allowances, and no 24 h / 2000 ceiling is touched.
