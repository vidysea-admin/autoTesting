# Checkpoint — t205-g10-headroom, coordinator A, cycle 0
Head 0b8325b6 · base 09828f2d · policy proportional-verification/2026-10-10.9 · written 2026-10-11T03:33Z
Verdict: qa/verdicts/t205-g10-headroom.a.md = FAIL (TF6 provenance). Full suite not run (lock held by another check; coordinator said skip).

Evidence identity (all on worktree D:/autoTesting/.worktrees/t205-g10-headroom at 0b8325b6, status clean; env = worktree .venv, Windows 11, `-p no:xdist -o addopts=`):
| check | scope | result |
|---|---|---|
| 8 TF test files | tests/test_run_launcher.py, _run_launcher_approval, _routers_list, _policy_merge, _cli_subapp_hook, _project_schema_team, _team_store, _team_enums_home | 4+8+4+8+4+6+50+3 passed |
| ui-run + CLI set | test_ui_runs*.py (6), test_cli_surface, test_cli_advice_resolves, test_cli_issues, test_schedule_model | 176 passed, 1 skipped |
| ruff | `ruff check src tests scripts` | All checks passed |
| doctor | `autotester doctor` | clean |
| route/CLI/schema audit | master 09828f2d vs 0b8325b6, same venv | identical (OpenAPI description string differs) |
| browser smoke | new :8811 vs master :8812, temp data root | identical pages and refusal |
| falsifications | 30 edits in copies (evidence §4) | 18 killed, 12 survived |
Attribution: coordinator A (this agent) plus six Sonnet sub-checkers, session 236a59b4. No reuse of B's evidence.

Remaining for re-dispatch: the full suite on 0b8325b6 (`python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting --ref 0b8325b6 --shards 4 -- -o addopts=`). Any repair cycle changes the SHA, so the suite then runs on the repaired head instead.
