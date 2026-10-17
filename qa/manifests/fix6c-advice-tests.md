# Manifest - fix6c-advice-tests (test-only: 6c integration FAIL on int/1017)

Contract: none new; repairs the 6c integration FAIL in qa/verdicts/integration-6c-int1017.md (commit 7b16f66b)
Issues addressed: none (stale expectations in two existing tests; no ledger row edited)
Fix cycle: 0
Dual check: no - test-only; no product, security, auth or tenancy code edited
Executor: claude-sonnet-subagent (maker, fix6c-advice-tests), 2026-10-18

## What changed
- tests/test_cli_advice_resolves.py:210-214 - `EXPECTED_SITE_COUNT` 28 -> 31 plus a history comment. f7605b35 (AT-899, checker-PASSed release CLI) added three real advice sites in `cli_release.py`: `release` at :49, `release-log` at :62 and :105. The (file, command) `EXPECTED_SITES` set already named both commands, so only the count was stale. Kept as `==`, not loosened to `>=`.
- tests/golden/cli_commands.json - two entries added (pure additions, order = `autotester --help` order): `ledger-backref` (AT-712, commit 81970378, merged on checker PASS at712-ledger-store, verdict qa/verdicts/at712-ledger-store.md) and `loop-tick` (AT-644, commit ce4e124a, merged as 8b98981f "ledger-tick-integrity checker PASS cycle 1", verdict qa/verdicts/ledger-tick-integrity.md). `schedule` and `auth` were already in the golden; the brief's "ledger-backref and schedule" is corrected to "ledger-backref and loop-tick" by `golden-only []` / `head-only [ledger-backref, loop-tick]` from a direct comparison.
- Not changed: tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve stays red (see Item 3 below). No file under src/ touched.

## Verification scope
Policy-Version: proportional-verification/2026-10-17.13
Tier: S (test only, two existing test expectations; the golden is read only by tests/test_cli_subapp_hook.py)
Base / checked state: base 7b16f66b; test commit 8a28f8f4
Gate answers: none; no new module, no qa/contracts or qa/issues.jsonl edit, no assertion deleted or weakened (both updates keep exact equality)
Affected tests / full-suite trigger: tests/test_cli_advice_resolves.py, tests/test_cli_subapp_hook.py; none
Tests[C1]: tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed - the count and set assertion for all advice sites
Tests[C2]: tests/test_cli_subapp_hook.py::test_help_lists_exactly_the_commands_it_listed_before - golden vs the live `--help` listing
Pre-check[C1]: 8a28f8f4 uv run pytest tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed -> 1 passed t=58 blobs=tests/test_cli_advice_resolves.py:fd39507
Pre-check[C2]: 8a28f8f4 uv run pytest tests/test_cli_subapp_hook.py -> 4 passed t=30 blobs=tests/test_cli_subapp_hook.py:3cc729f,tests/golden/cli_commands.json:11fe8c6
Metrics: start=2026-10-17T00:00:00Z end=2026-10-18T00:00:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal

## How to verify (commands + expected)
- `uv run pytest tests/test_cli_advice_resolves.py tests/test_cli_subapp_hook.py` -> expected: 43 passed, 1 failed (only test_the_collector_reports_what_it_could_not_resolve, pre-existing)
- `uv run ruff check src tests scripts` -> expected: All checks passed
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest (the two files): `1 failed, 43 passed, 20 warnings`; the one FAILED is `test_the_collector_reports_what_it_could_not_resolve`.
- ruff: `All checks passed!`; doctor: `doctor: clean` (2 advisory decision-citation-known-disputed notes, D-087, non-blocking).
- Direct site list (31): `cli_release.py` lines 49 release, 51 release-log, 55 release, 62 release-log, 105 release-log; every one is a literal `next:`/`see` hint in the file, and the parametrized `test_every_command_the_code_names_is_one_the_cli_exposes` cases for all five pass (they run `autotester release|release-log --help`).
- Base finding: master (69ebfae7) golden also lacks `ledger-backref` and `loop-tick` while `cli_loop.py::attach_loop_commands` registers both, so the golden red is pre-existing on master as well as on head; the count red exists only on head (AT-899 is not on master).

## Item 3 (left, reported)
`tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` flags `src/autotester/ui/routes_crawl_approval.py:184`: `f"max probes ... {MAX_GRANT_PROBES}"`, where `core/consent.py:43` binds `MAX_GRANT_PROBES = MAX_GRANT_ACTIONS * PROBES_PER_ACTION`. `tests/advice_scan.py::_module_level_names` only exempts a non-str literal or a literal container, so an arithmetic binding is an "unresolved hole". Not a one-line fix: exempting any BinOp would hide `CMD = BASE_CMD + SUFFIX` (the AT-212 hole), and the honest fix is evaluating int-only arithmetic across the imported-constant index (new collector logic), or a `str(...)` dodge in a src route (rejected: sidesteps the guard and needs a checker). Left red; needs its own unit. Introduced by AT-675 (354a55e8 / 1dc74b2b).

## Capability coverage (each new claim -> its isolating falsification)

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | the advice-site guard asserts the exact number of sites (31) on head | tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed (`assert len(advice()) == EXPECTED_SITE_COUNT`, :225) | throwaway copy OUTSIDE the worktree (scratchpad/fals, `PYTHONPATH=src:tests:scripts:.`): `cli_release.py:105` text `see \`autotester release-log {project} {rid}\`` -> `see the release log` (the (file, command) set stays equal because release-log remains at :51/:62) | GREEN before in the worktree: `43 passed` incl. this node. RED after: `AssertionError ... assert 30 == 31` at `tests\test_cli_advice_resolves.py:225` (the count assertion, not the set assertion, not an import error). |
| C2 | the CLI golden lists exactly the commands `--help` lists, now including `loop-tick` and `ledger-backref` | tests/test_cli_subapp_hook.py::test_help_lists_exactly_the_commands_it_listed_before | same copy: `cli_loop.py:80` `app.command("loop-tick")(loop_tick_cmd)` -> `pass` | GREEN before in the worktree (same run). RED after: `At index 13 diff: ['explore', ...] != ['loop-tick', ...]` at `tests\test_cli_subapp_hook.py:27` (the named golden entry no longer in the listing). The copy also printed `Right contains one more item: ['auth', ...]`, a side effect of the minimal copy without the editable install, unrelated to the edited line. |

## Live browser evidence
Not UI-touching - no surface changed. Changed paths: tests/test_cli_advice_resolves.py, tests/golden/cli_commands.json.

## Status: merged-no-check (test-lane)
