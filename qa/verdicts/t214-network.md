# Verdict - t214-network (T-214, MP21 + MP22)

Cycle checked: 0
Date: 2026-10-18 (checker, bound to D:/autoTesting/.worktrees/t214-network, head 8083fa0e; code SHA d756b351, manifest-only commit after it)

## Check plan
Tier M (3 new src files, public oracle entry points, new schema file). Signals: logic changed -> affected tests + falsification floor. No UI, no auth/tenancy/write/prod trigger, no prompt, no data artifact: no Mode D, no persona walk, single checker. Lane: off (`--lane-check` -> `lane-disabled`), so a normal check.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met, 3/3 invariants hold (MPI1, MPI2, MPI3)
TIER: M (3 new src modules incl. a shared schema file and two oracle entry points; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (one named falsification per criterion, in copies outside the repo)
LIVE-BROWSER: not-applicable (no route, template or static asset changed; src/autotester/schema/request_budget.py, stages/oracle_api_error.py, stages/oracle_request_budget.py only)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all produced in this check)
- Step 3: `uv run --directory <worktree> pytest tests/test_network_oracles.py tests/test_oracle_registry.py` -> 59 passed. `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> 2 violations, both `stale-generated` (docs/MAP.md, docs/SNAPSHOT.md), as manifest judgement call 11 says; neither is a product defect.
- MP21: read oracle_api_error.py:33-52. A step with `success_indicator` set yields one finding per distinct (method, templated URL, status) with 400<=status<=599 (lines 23-24, 35), citing method, status, URL template, indicator and screen template in the title (27-30). Third-party responses never reach it: `capture_samples` goes through `network_capture.first_party_evidence` (oracle_request_budget.py:74), which drops non-first-party hosts and applies `Redactor.scrub` (network_capture.py:36-43). Fixture 500-behind-toast test passes.
- MP22: oracle_request_budget.py:107-137. Per-screen total strictly greater than `max_requests_per_screen` is a finding with the count in the title (112-115); an endpoint repeated >= `min_repeats_for_polling` with its smallest gap under `min_poll_interval_s` is a finding with the measured gap and the budget (127-134); no declared budget -> `[]` (150). The 200 ms vs 1 s fixture passes and the title carries "0.20 s" and "1.00 s".
- MPI1: neither oracle nor the schema file references `autotester.providers` (grep: none); findings carry `safe_template` output only; canary email/phone/id test passes.
- MPI2: fixtures are scripted `(method, url, status, t_s)` lists in status/interval/count matrices; none reproduces a benchmark finding.
- MPI3: `git diff --name-only cff3ffe6..HEAD` lists only the manifest, the 3 src files and the 2 test files; `schema/multi_role_enums.py` is absent.
- Step 4c: `git diff --numstat cff3ffe6..HEAD` -> 705 insertions, 0 deletions; every file is in the manifest "What changed". Nothing removed or renamed. `git diff d756b351..HEAD` is the manifest only.
- Step 4b, floor 1 per criterion, each in its own throwaway copy under the scratchpad (src, tests, scripts, pyproject; PYTHONPATH pointing at the copy, `autotester.__file__` confirmed inside the copy):
  - MP21: `FIRST_ERROR_STATUS = 400` -> `500` in oracle_api_error.py:23. `test_mp21_every_4xx_and_5xx_is_flagged` green in the unmutated copy (9 passed), red after (`assert [] == [1]`, the 4xx params).
  - MP22: `gap < budget.min_poll_interval_s` -> `<=` in oracle_request_budget.py:131. `test_mp22_the_polling_boundary_is_the_declared_interval` green in the copy (4 passed), red after (`[1.0-False]`: `assert True is False`).
  Both reds are on the named assertion, not on import or setup.

## Judgement calls (11 in the manifest)
All accepted. 1-3 (optional `NetworkLogPort` seam, `NetworkLogUnavailable` -> registry `errored` with type name only, budget from the port, none -> no finding) are the narrowest reading that leaves T-207/T-210/T-211 files untouched, and the errored path is tested end to end through `run_oracles`. 7 (finding cites the template, not the raw URL) follows MPI1 and `MultiRoleFinding.url_template`. 8 (`run =` alias) is the documented workaround for the doctor duplicate-concept rule. The CORE-REQUEST lines in the manifest (port seam wiring in T-210, a `request_budget` field on `Project`, a doctor exemption for oracle `run`) are for their owners, not defects here.

EXPLANATION: Both oracles do what MP21 and MP22 state, with the boundary, no-budget, third-party and redaction cases tested and the diff touching only its declared files. I re-ran the 59 affected tests, read all three modules in full, and falsified one rule per criterion in separate copies (green before, red on the named assertion after). No criterion, invariant, correctness or floor defect found.

Metrics: start=2026-10-18T20:16:24Z end=2026-10-18T20:24:00Z wall_min=8 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=456 mutants=0 defects_unit=0 defects_6c=0
slow: reading checker protocol and 3 modules before first command 3 min
Lane exit: none (lane disabled in qa/adapter.json at base and HEAD; normal check from the start)
