# Verdict — t173-parallel-run

**Cycle checked: 1**
**Contract:** qa/contracts/parallel-run.md (PR1-PR7) + qa/contracts/core-invariants.md
**Manifest:** qa/manifests/t173-parallel-run.md
**Checker:** fresh-context /checker Mode A, worktree `D:/autoTesting/.worktrees/t173-parallel-run`
(branch `wave/t173-parallel-run`, HEAD `bdde901`)

## VERDICT: PASS

## What I ran

- `git -C <wt> diff --stat` / full diff against `merge-base HEAD master` (`a953bc5`) — 6 files
  changed, all additive (no deletion/rename of any existing function/class/export/route/test/
  config key). Matches manifest's "What changed" exactly: `schema/project.py` (+5, new
  `Project.max_parallel: int = Field(default=1, ge=1, ...)`), `schema/run.py` (+12, new
  `Run.parallel_n`/`Run.parallel_bound_by` fields), `stages/parallel_run.py` (new, 237 lines),
  `tests/test_parallel_run.py` (new, 295 lines), `docs/MAP.md` (+1, generated). Both schema
  additions are `Field`s on existing `Project`/`Run` Pydantic models, which inherit
  `extra="forbid"` via `schema.base.Artifact` — no new dict/dataclass/TypedDict duplicating a
  schema shape.
- `uv run pytest tests/test_parallel_run.py` → `10 passed in 1.20s`.
- `uv run ruff check src tests scripts` → `All checks passed!`.
- `uv run autotester doctor` → `doctor: clean`.
- Non-browser suite (computed via the contract's `comm -23` recipe over `tests/test_*.py` against
  the 20 files matching `playwright|chromium|sync_playwright|BrowserSession\(|launch_browser|
  browser_session`; 136 non-browser files): `uv run pytest <136 files> -p no:randomly` in the
  worktree → **1497 passed, 5 skipped, 0 failed in 251.85s (0:04:11)**. Nothing this unit could
  have caused to fail; no master comparison needed.
- Capability coverage: reproduced all 7 rows myself in a throwaway copy outside the worktree
  (`C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\909303db-cd49-47bd-ad40-ab83e988e1dc\
  scratchpad\t173-copy`, `shutil.copytree` excluding `.git/.venv/.work/projects/__pycache__/
  node_modules`, then `uv sync` — 1497-equivalent deps installed clean). Baseline in the copy:
  `10 passed in 1.41s` before every sabotage. Each edit applied via a Python anchor-count-then-
  replace (asserted the anchor matched exactly once and the file text actually changed before
  believing any result, per C7), single-hunk, single-file, restored from a saved `.orig` copy of
  `parallel_run.py` and reconfirmed green (`10 passed`) between rows.
- PR5 flakiness protocol (step 6a): 5 unmodified runs of `test_pr5_...` and 5 sabotaged runs.

## CAPABILITY-COVERAGE: 7/7

| PR | edit | assertion fired |
|---|---|---|
| PR1 | `n = min(config_ceiling, measured_budget)` → `n = config_ceiling` | `test_pr1_n_is_min_of_config_ceiling_and_measured_budget`: `AssertionError: assert (8, 'budget', 8, 3) == (3, 'budget', 8, 3)` — `1 failed, 1 passed`. Reverted → `2 passed, 8 deselected`. |
| PR2 | `ProjectPaths(f"{project.slug}-parallel-{case.id[:12]}")` → `ProjectPaths(f"{project.slug}-parallel")` | `test_pr2_default_session_factory_gives_each_case_a_distinct_profile`: `AssertionError: assert 'p1-parallel' != 'p1-parallel'` — `1 failed, 1 passed`. Reverted → `2 passed, 8 deselected`. |
| PR3 | `if project.write_policy is WritePolicy.ALLOW_WRITES:` → `if False:` | `test_pr3_allow_writes_forces_serial_regardless_of_max_parallel`: `AssertionError: assert (4, 'config') == (1, 'write_policy')` — `1 failed, 9 deselected`. Reverted → `1 passed, 9 deselected`. |
| PR4 | `return [f.result() for f in futures]` → `return [f.result() for f in reversed(futures)]` | `test_pr4_parallel_verdicts_equal_serial_verdicts`: order assertion fires (`AssertionError: assert ['case_fcaf65...'] == ['case_3531e5...']`) while the preceding dict-parity assertion stays green — `1 failed, 9 deselected`, confirming the two assertions isolate independent properties. Reverted → `1 passed, 9 deselected`. |
| PR5 | `n = max(1, plan.n)` → `n = 1` | `test_pr5_parallel_is_faster_than_serial_for_n_ge_2`: `assert 0.609... < (0.610... * 0.7)` — `1 failed, 9 deselected`. Reverted → `1 passed, 9 deselected`. Flakiness re-checked (see below). |
| PR6 | `except Exception as exc:` → `except KeyError as exc:` | `test_pr6_one_case_crashing_does_not_abort_siblings`: unhandled `ValueError: boom mid-case` propagates out of `_run_one`/`Future.result()`, whole call errors rather than the one case reporting `ERRORED` — `1 failed, 9 deselected`. Reverted → `1 passed, 9 deselected`. |
| PR7 | `if budget is not None and not budget.try_consume(...)` → `if False:` | `test_pr7_aggregate_budget_is_not_multiplied_by_concurrency`: `AssertionError: at least one case refused by the shared budget` (all 4 cases, cost 12, ran unchecked against `max_actions=10`) — `1 failed, 1 passed`. Reverted → `2 passed, 8 deselected`. |

All 7 fired for the reason the test is named for (value/behaviour assertions on the exact
property, never an import/syntax/collection break), matching the manifest's claims exactly, and
none were on a re-scoped/multi-file/shell-command cell (no CONTRACT_MISMATCH).

## NON-BROWSER SUITE: 1497 passed, 5 skipped, 0 failed in 251.85s — no master comparison needed (no failures introduced)

## PR5 FLAKINESS: 5/5 green unmodified, 5/5 red sabotaged

Ran `uv run pytest tests/test_parallel_run.py -k pr5` five times against the unmodified copy
(all `1 passed, 9 deselected`), then applied the manifest's PR5 falsifying edit (`n = max(1,
plan.n)` → `n = 1`) and ran it five more times (all `1 failed, 9 deselected`, e.g. `assert
0.609... < (0.609... * 0.7)`, `assert 0.641... < (0.593... * 0.7)`, `assert 0.594... <
(0.609... * 0.7)`). The 0.7 margin holds reliably in both directions on this host under load
(other wave sessions were running concurrently, per the manifest's own RAM-pressure table) — not
a check that passes or fails by luck. No FAIL, no debt row for PR5.

## WIRING JUDGEMENT

Quoted from each criterion's own Falsifiable clause: PR1 "a fixture with `max_parallel=8` on a
host whose measured budget yields 3 → the run never has more than 3 cases in flight"; PR2 "run
two cases concurrently where one logs in and the other does not declare a session"; PR3 "a
fixture project with `write_policy=ALLOW_WRITES`... → at most one case in flight"; PR4 "run the
same ≥4-case fixture once parallel and once serial; diff the two verdict sets"; PR5 "time both
runs from PR4's fixture"; PR6 "a fixture where one case's context is made to crash mid-run
alongside two healthy cases"; PR7 "a fixture `RunApproval`... → the run halts at 10 total
actions, not 40." Every PR's own falsification is stated against a fixture/test harness, not
against the live UI run trigger (`ui/routes_runs.py`) or `stages/orchestrate.py`. The contract's
"How a unit is verified" section names only `uv run pytest tests/test_parallel_run.py` +
`ruff` + `doctor` + the capability-coverage table as what a unit is verified against — it does
not name wiring into the live run path. No PR criterion's text requires the live run path to
actually invoke parallel execution for PASS.

**Ruling: unwired state is an observation, not a FAIL.** `run_cases`/`plan_parallel_run` are a
complete, independently-tested capability that `ui/routes_runs.py`/`stages/orchestrate.py` do not
yet call — consistent with the manifest's stated reason (avoiding file-level collision with
sibling worktrees T-172/T-175, which are building against those same two files) and with
core-invariants' No-fire list ("Missing features that are scheduled in a later phase of the plan
and not claimed by this unit"). A follow-up unit should wire `run_cases` into the live path;
until then, T-173 as scoped (the fan-out module + its tests) is complete against its own
contract.

## LIVE-BROWSER: not-applicable

Changed paths: `src/autotester/schema/project.py`, `src/autotester/schema/run.py`,
`src/autotester/stages/parallel_run.py` (new), `tests/test_parallel_run.py` (new),
`docs/MAP.md` (generated). None match the UI-surface glob (`ui/**`, `routes/**`, templates,
`*.tsx|jsx|vue|svelte|html|css`) and none flow into what a page renders — `ui/routes_runs.py`
is untouched (confirmed by the diff, matches manifest's "Not touched" list). No Mode D run
performed; none required.

## EXPLANATION

All 7 PR criteria have re-runnable, independently-reproduced falsifying evidence (not read from
the manifest — I applied and ran every sabotage myself in a fresh throwaway copy), the full
non-browser suite (1497 tests) is green with no regressions, and PR5's timing assertion is
reliable in both directions across 10 independent runs. The unit is deliberately unwired into
the live run path, and no PR criterion's own falsification text requires that wiring for PASS —
recorded as an observation per the maker's question (b), not charged against the unit.

## VERDICT-COMMIT: (see commit recorded immediately after this file, in the same commit as this verdict)

## PROPOSED FINDINGS

none

---

## SUPERVISING CHECKER — PASS accepted · 2026-09-25

Meets the checker bar: every non-browser test file green (1497 passed, 5 skipped, 0 failed), 7/7
capability rows reproduced by the checker in a throwaway copy, PR5 timing reliable in both
directions (5/5 green unmodified, 5/5 red sabotaged), no UI path changed. The wiring ruling is
confirmed against the contract text: every PR criterion's falsifiable clause is fixture-level and
"How a unit is verified" names only the test file + ruff + doctor + the capability table, so the
unit does not have to be wired into the live run path to PASS.

**Goal-level gap, filed separately (AT-562):** the contract's "What it is" says N and its bounding
term are "recorded in the run's state so a human reading the run afterward knows why it ran at
that width". No live path (`stages/execute.py`, `stages/orchestrate.py`, `ui/routes_runs.py`)
calls `run_cases`, so no real run can use or record parallel execution yet. The unit PASSes; the
user-visible feature is not delivered until a follow-up wires it in. T-173 is closed in
`.goal/goal.json` only after this merges, with AT-562 carrying the wiring.

---

## REOPENED by Mode B sweep · 2026-09-25

The PASS above is not fully backed for PR6. stages/parallel_run.py::_run_one calls session_factory(case) outside its try, so a context-launch failure for one case raises out of run_cases and discards every sibling's result -- PR6 requires that crash be reported as that case's own ERRORED outcome. The cycle-1 PR6 capability row only mutated the run_fn except-clause, so the factory path was never falsified (a checker miss, owned). Filed AT-565 (high); T-173 goal task reopened; the fix is folded into at562-564-live-wiring (Issues addressed: AT-562, AT-564, AT-565). The next T-173 check must include a PR6 test in which the FACTORY raises.
