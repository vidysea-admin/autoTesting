# t167-release-regression - coordinator B, repair check (cycle 2)
Cycle checked: 2
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting · branch wave/t167-release-regression · commit 1b6f07e7 (product 7e09124a) · Repair base 102a4b91 (ancestor of HEAD, verified)

## Check plan
Repair diff 102a4b91..1b6f07e7 is claimed test-only. Plan: read the diff in full (4c); confirm src/ untouched and no assertion weakened; attack the advice guard (registry, scanner blind spots, option resolution); run the two test files; one falsification per repaired item in its own copy; ruff + doctor. No full suite (the other coordinator owns it). Work in `git archive 1b6f07e7` copies with `uv sync --frozen`.

## Findings
- Diff stat: tests/test_cli_advice_resolves.py (+3/-1), tests/test_release_gate.py (+15), qa/manifests/t167-release-regression.md. `git diff 102a4b91 1b6f07e7 --stat -- src` is empty: no product code changed. Test edits only ADD (2 registry tuples, count 19 -> 21, one new test); no assertion deleted, loosened, skipped or xfailed. Not a protected test change.
- Scanner sees exactly two sites in cli_release.py: line 34 `release-log` and line 36-37 `release` (an implicit-concatenation f-string, rendered as one JoinedStr). Module docstring mentions are correctly excluded as documentation. grep of all other release-path modules (stages/release.py, release_compare.py, orchestrate.py, orchestrate_gate.py): no `autotester <cmd>` advice string exists; ApprovalRequired messages there carry no command. The grant command for the refusal comes from core/consent.py:123 (already registered as `approve`); every option it can print (--kind --target --scope --granted-by --expires --max-actions --max-probes --wall-clock --production) exists on `approve_cmd` (cli_crawl.py:237-247).
- Real-parser check (click `make_context`, not just `--help`) of the exact printed forms: `release proj --run-id rel-1 --approve-by bob`, `... --decline-by bob`, `release-log proj rel-1` all parse to the expected params; `release` opts = --run-id --approve-by --decline-by --git-sha, `release-log` args = project, run_id. All advice in cli_release.py resolves.
- Registry attack: the 21 count is exact (19 + 2 sites). Removing either new entry, or a wrong command name, turns the guard red (below). 

## Evidence
- `pytest tests/test_cli_advice_resolves.py tests/test_release_gate.py` -> 34 passed (30 + 4).
- Falsifications (each in its own `git archive` copy, green on the unmutated copy first):
  - F1 registry: delete `("cli_release.py","release-log")` -> `test_no_advice_site_can_vanish_unnoticed` red by assertion (`new: [('cli_release.py','release-log')]`).
  - F2 wall clock: orchestrate_gate.py:46-49 `max(scope.wall_clock_s, actions*WALL_CLOCK_PER_ACTION_S)` -> `scope.wall_clock_s` -> `test_rr2_an_under_declared_wall_clock_alone_is_refused` red `DID NOT RAISE ApprovalRequired` (1 failed, 3 passed).
  - Extra attack A: cli_release.py:36 `release` -> `releaze` -> `test_no_advice_site_can_vanish_unnoticed` and `test_every_command_the_code_names_is_one_the_cli_exposes[cli_release.py:36:releaze]` both red (2 failed, 28 passed).
  - Extra attack B: `--approve-by` -> `--approve` in the advice string -> guard stays GREEN (30 passed). The guard resolves command names and arity only, never option names. The shipped strings are correct (verified above), so this is a latent weakness, not a defect in this unit.
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
- Evidence reused from r1 (files the repair does not touch): RR1, RR3-RR6, RR2 product fix and attack matrix A0-A9 (src unchanged since 102a4b91).

VERDICT: PASS
SCOREBOARD: criteria RR1-RR6 unchanged-and-met (RR2 repaired items re-evidenced), invariants hold
TIER: L (security/approval gate; dual-trigger src/autotester/core/consent.py:182). This repair diff itself is test-only
FAILURES: none
CAPABILITY-COVERAGE: 2/2 repaired rows reproduced (registry, wall-clock); 2 extra attacks run
LIVE-BROWSER: not-applicable (tests and manifest only)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE only)
PROPOSED-ISSUE: {"severity":"low","feature":"cli-advice-guard","title":"tests/test_cli_advice_resolves.py resolves command names only; a wrong option in advice text (e.g. --approve for --approve-by) passes","evidence":"copy m4 of 1b6f07e7, cli_release.py:36 edited to `--approve <name>`: 30 passed","fix":"extend advice_scan to extract --flags and assert each is an option of the resolved command"}
EXECUTOR: claude-sonnet-subagent (checker)
EXPLANATION: The repair is test-only as claimed: nothing under src/ changed, no assertion weakened. The registry now matches the scanner's two cli_release.py sites exactly, every advice string in that module parses in the real click parser, and both repaired items fail by assertion when mutated. No full suite was run by design (coordinator A owns it).
Metrics: start=2026-10-11T05:05+0530 end=2026-10-11T05:27+0530 wall_min=22 agent_min=22 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1320 mutants=2 defects_unit=0 defects_6c=0
