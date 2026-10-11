# t167-release-regression r2 A (repair coordinator A, blind dual check) - 1b6f07e7

Bound to D:/autoTesting. Cycle checked: 2. Policy-Version: proportional-verification/2026-10-10.9. Repair base 102a4b91 (ancestor of 1b6f07e7, verified with git).

## Plan
Repair-scoped: read `102a4b91..1b6f07e7` in full; confirm no `src/` change (so every RR criterion's inputs are untouched and the r1 results stand); rule on the guard-test edit; run the two touched test files in a `git archive` copy; one falsification against the registry and one against the wall-clock clause; ruff + doctor. No full suite.

VERDICT: PASS
SCOREBOARD: failed-at-cycle-1 criterion (full-suite guard `test_no_advice_site_can_vanish_unnoticed`) now green; RR criteria unchanged (inputs untouched), results kept from r1.a checkpoint (evidence identity of 102a4b91)
TIER: L (repair of an L unit with an open FAIL; diff itself is test-only)
FAILURES: none

## Evidence
- Diff: `git diff --stat 102a4b91 1b6f07e7` = qa/manifests/t167-release-regression.md, tests/test_cli_advice_resolves.py (+2 EXPECTED_SITES entries, 19 -> 21), tests/test_release_gate.py (+1 test). `git diff --stat ... -- src docs` is empty: no file under src/ or docs/ changed.
- Ruling on the guard-test edit: it is a guard-registry edit, but not a weakening. No assertion deleted or loosened, no threshold lowered, no skip/xfail. It adds two registered sites and raises the count by exactly the two sites that exist (`cli_release.py` lines 34 and 36), which is what the guard's own docstring asks for ("a new site is a deliberate act and should be added here"). It tightens the freeze. Justified.
- Advice resolves against the real CLI (copy of 1b6f07e7, `autotester release --help` / `release-log --help`, both exit 0): `release-log` takes `{project} {run_id}` (advice: `release-log {project} {run_id}`); `release` takes `{project}` plus `--run-id`, `--approve-by`, `--decline-by` (advice: `release {project} --run-id {id} --approve-by <name>` / `--decline-by <name>`).
- Tests in the copy: `pytest tests/test_cli_advice_resolves.py tests/test_release_gate.py` -> 34 passed (twice, incl. pinned-package re-run in a clean copy).
- Falsification, registry (green before in each copy, red after; own mutants):
  - mut1: remove the `release-log` advice from cli_release.py -> `test_no_advice_site_can_vanish_unnoticed` RED, `gone: [('cli_release.py','release-log')]`.
  - mut2: add an unregistered `autotester providers` string to cli_release.py -> same test RED, `new: [('cli_release.py','providers')]`.
- Falsification, wall-clock clause: mut3 in `stages/orchestrate_gate.py:46-49` replace `max(scope.wall_clock_s, actions * WALL_CLOCK_PER_ACTION_S)` with `scope.wall_clock_s`. `test_rr2_an_under_declared_wall_clock_alone_is_refused` green before, RED after on `Failed: DID NOT RAISE ApprovalRequired` (the assertion it is named for, not an import error).
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> clean (exit 0), run with the copy's own src pinned via PYTHONPATH. Note: a first `uv run autotester doctor` reported `stale-generated: docs/MAP.md`; that run imported a package that listed T-203 modules absent from this tree (environment artifact of `uv run` with a foreign VIRTUAL_ENV), not this diff. Reproducing with the package pinned to the copy's src gives clean, and 102a4b91 is also clean.
- full-suite trigger: none new. The repair is test-only, no src moved; the r1 full suite of 102a4b91 (2865 passed, 19 skipped, 5 failed: this guard, ledgered AT-792/AT-725/AT-858, one load flake) stays valid for every untouched file. The one red this repair owned is now green by the run above.
- CAPABILITY-COVERAGE: 3/3 own mutants reproduced. LIVE-BROWSER: not-applicable (tests/manifest only). ISSUES-WRITTEN: none (dual coordinator).
- PROPOSED-ISSUE: {"severity":"low","feature":"t167-release-regression","title":"EXPECTED_SITES docstring in tests/test_cli_advice_resolves.py still says 'ten entries for eleven sites'; stale wording after the set grew to 20 entries / 21 sites","evidence":"tests/test_cli_advice_resolves.py docstring after EXPECTED_SITES"}

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-1 failure was an unregistered pair of real advice sites; the repair registers them, the CLI parser resolves both, and the guard still fails on removal and on an unregistered addition. The new wall-clock test is isolated to the `max(...)` clause. No src change, so no RR criterion moved.
Metrics: start=2026-10-10T23:48:00Z end=2026-10-10T23:59:00Z wall_min=11 agent_min=11 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=660 mutants=3 defects_unit=0 defects_6c=0
