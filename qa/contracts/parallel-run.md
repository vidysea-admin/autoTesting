# Contract — parallel-run (N isolated browser contexts, D-041)

**Status:** ACTIVE (DRAFT->ACTIVE by /checker on T-173's checker PASS, 2026-09-25; qa/verdicts/t173-parallel-run.md Cycle checked: 1, merged 626fa03). Live-path wiring gap AT-562; PR6 session-factory isolation defect AT-565 (T-173 reopened) is a violation OF this ACTIVE criterion, not a reason to keep the contract DRAFT.
**Feature:** run N cases concurrently in isolated Playwright browser contexts, where N is bounded by
both `project.max_parallel` and a measured RAM/CPU budget, with the chosen N and its binding limit
recorded on the run; cases against a project whose `write_policy` permits writes on a shared test
account run serially instead, never concurrently.
**Covers:** goal task T-173. **Deps:** T-163 (orchestrator; done). **Grounding:** D-041 §6
(`docs/DECISIONS.md`, "Parallel runs address the observed serial bottleneck ... ours runs one case at
a time"); `schema/project.py::Project.write_policy` (`WritePolicy.READ_ONLY` /
`WritePolicy.ALLOW_WRITES`, `schema/enums.py:149-154`) — the existing project-level field this unit's
serial-fallback gate reads; `schema/approval.py::RunApproval` (`max_actions`, `max_probes`,
`wall_clock_s`) — the existing per-run consent bound this unit must not silently widen.

## What it is

Today `stages/execute.py::run_case` drives one case at a time on one `BrowserSession`. This unit adds
a fan-out that runs up to N cases concurrently, each on its own Playwright `BrowserContext` (its own
cookies/storage state), where N = `min(project.max_parallel, <measured RAM/CPU budget>)`. Both the
chosen N and which of the two terms bound it are recorded in the run's state so a human reading the
run afterward knows why it ran at that width. A project whose `write_policy` is `ALLOW_WRITES` (a
shared test account writes can collide on) forces its cases back to serial execution — concurrency is
never applied where two cases could race against the same account.

## Criteria (PR1-PRn) — each judged on re-runnable evidence

- **PR1 — N is bounded and the bound is recorded.** The number of concurrently-running cases never
  exceeds `min(project.max_parallel, <measured RAM/CPU budget>)`; the run's persisted state records
  both the chosen N and which term (the config ceiling or the measured budget) actually bound it.
  (Falsifiable: a fixture with `max_parallel=8` on a host whose measured budget yields 3 → the run
  never has more than 3 cases in flight, and the recorded binding names the budget, not the config,
  as the limiting term.)
- **PR2 — Each case gets an isolated browser context; no shared session leak.** Every concurrently-run
  case executes in its own Playwright `BrowserContext`/storage state, distinct from every sibling case
  running alongside it. (Falsifiable: run two cases concurrently where one logs in and the other does
  not declare a session; assert the second case's context never observes the first case's
  cookies/storage state.)
- **PR3 — Write-permitting projects run their cases serially, never concurrently.** When
  `project.write_policy` is `ALLOW_WRITES` (`schema/enums.py:154`), that project's cases never run two
  at a time against it, regardless of `max_parallel` or the measured budget. (Falsifiable: a fixture
  project with `write_policy=ALLOW_WRITES` and `max_parallel=4` and 3 cases → at most one case in
  flight against that project at any instant, verified by overlapping start/end timestamps.)
- **PR4 — Verdict parity: parallel == serial.** On a fixture case set, the set of verdicts produced
  running in parallel equals the set of verdicts produced running the same cases serially — same cases,
  same PASS/FAIL outcomes, nothing gained or lost by concurrency. (Falsifiable: run the same ≥4-case
  fixture once parallel and once serial; diff the two verdict sets → empty diff.)
- **PR5 — Parallel is actually faster for N≥2.** On the same fixture, parallel wall-clock time is
  strictly less than serial wall-clock time when N≥2 cases run concurrently. (Falsifiable: time both
  runs from PR4's fixture; parallel duration < serial duration.)
- **PR6 — A crash in one case does not abort its siblings.** An exception or crash inside one case's
  context is caught and reported as that case's own outcome (e.g. `Outcome.ERRORED`); every other
  concurrently-running case completes and reports its own outcome independently. (Falsifiable: a fixture
  where one case's context is made to crash mid-run alongside two healthy cases → the crashed case
  reports ERRORED, the other two report their real outcomes, none of them ERRORED by contagion.)
- **PR7 — Consent bounds apply to the total run, never widened per worker.** `RunApproval.max_actions`
  / `max_probes` / `wall_clock_s` (`schema/approval.py:41-43`) bound the AGGREGATE of all concurrent
  workers in the run, not each worker independently — running at N-way parallelism never grants the run
  up to N times the approved action/probe/time budget. (Falsifiable: a fixture `RunApproval` with
  `max_actions=10` and N=4 concurrent cases that would together attempt >10 actions → the run halts at
  10 total actions, not 40.)

## Explicit no-fire list (do not raise these as findings)

- A distributed/multi-machine execution model — this unit is N contexts within one process/host, not a
  cluster or queue-based worker fleet.
- Retrying a crashed case automatically — PR6 requires the crash be reported per case, not recovered;
  auto-retry is a separate concern this contract does not require.
- Dynamic re-balancing of N mid-run (e.g. raising N if RAM frees up) — PR1 requires N be bounded and
  recorded at the start of the run's parallel phase; live re-tuning is out of scope.
- The specific RAM/CPU measurement mechanism's precision (exact MB/percentage thresholds) — the
  criterion is that a real measured budget participates in the `min()`, not a particular measurement
  method.

## How a unit is verified (adapter slot 1)

`uv run pytest tests/test_parallel_run.py` (bare, no CLI `-q`, AT-503; this is T-173's `done_check` in
`.goal/goal.json`) + `uv run ruff check src tests scripts` + `uv run autotester doctor`, all exit 0;
each PR criterion carries a capability-coverage row with a single-hunk falsifying edit reproduced
green→red-for-the-named-reason→revert→green. File/function caps (core-invariants C2) apply; if
`stages/execute.py` has no headroom under its 300-line cap, the fan-out logic lands in a new,
justified module per C3 rather than pushing the file over budget.

## Amendment log (append-only; git history is the version)

- 2026-09-24 · init · contract authored by /checker as DRAFT, from D-041 (Approved-by Umesh —
  AskUserQuestion answers + plan approval, chat 2026-09-24). No prior draft existed; nothing amended.
- 2026-09-25 · DRAFT->ACTIVE · /checker Mode B sweep, on T-173 checker PASS (qa/verdicts/t173-parallel-run.md Cycle checked: 1, merged 626fa03), as this contract's own status line pre-authorized; precedent network-assertions.md at the T-170 PASS. No criterion text changed.
