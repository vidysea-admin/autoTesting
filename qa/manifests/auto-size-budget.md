# Manifest - auto-size-budget

**Status:** checked-PASS
**Fix cycle:** 0
**Security trigger:** YES - consent gate (D-018 / D-111 / D-112): grant bounds are signed into `RunApproval` rows. **Dual check recommended (A+B).**
**Authority:** D-112 item (2) (`docs/DECISIONS.md` lines 2808-2820 on master, `Approved-by: Umesh`, chat 2026-10-28 "go with A"). The entry is not in this tree yet, so doctor lists the D-112 citations as dangling, as it did for D-110/D-111 on consent-followups.
**Branch:** `fix/auto-size-budget` (worktree `D:/autoTesting/.claude/worktrees/auto-size-budget`, off `fix/consent-followups` 077b7fb9)
**Not done by the maker (by instruction):** no merge, no push, no edit to `qa/contracts/` or `docs/DECISIONS.md`, nothing touched in the main checkout, `stages/run_budget.py` untouched (D-112 item 1 is being built on `fix/run-teardown-stall`).

## Criteria (judge against these)
- **S1** One derivation, no duplicate: `schema/approval.py::derive_grant_bounds(kind, actions, probes, wall_clock_s) -> GrantBounds`. For `LIVE_CASE`: actions and wall clock are multiplied by `GRANT_SAFETY_MARGIN` (1.25) and rounded UP to whole units, clamped to `MAX_GRANT_ACTIONS` (2000) / `MAX_GRANT_WALL_CLOCK_S` (86400); probes are `max(floor, actions x PROBES_PER_ACTION)` capped at `MAX_GRANT_PROBES` (the consent-followups estimator, moved here with the same rule). `0` means "not asked" and stays 0; a non-finite wall clock passes through; every other kind passes through unchanged.
- **S2** `stages/run_gates.py::derive_live_case_grant(cases)` feeds it the gate's OWN request for the planned cases (`sum(action_cost)` = one per step, min 1; `wall_clock_request_s` = per-step allowance x steps plus the judge allowance; `max(probe_request, 1)`), so a derived grant is never below what `require_live_case_approval` asks and always clears the gate it was sized for.
- **S3** The refusal hint ("Grant one with:") prints the derived numbers for a `LIVE_CASE` refusal (`core/consent.py::_grant_command` calls `derive_grant_bounds`). The gate's own checks (`_shortfalls`, `_reject_reason`, the numbers `require_approval` is asked for) are unchanged, so no existing grant becomes invalid. Crawl / adversarial / read hints print exactly what they printed.
- **S4** `autotester approve` (CLI): `--max-actions`, `--max-probes`, `--wall-clock` are optional. For `--kind live_case` each omitted one is derived from the project's non-retired cases and the derived numbers are printed (cyan line) BEFORE the row is signed; a typed flag stands and overrides only itself. With no planned cases, or any other kind, the old 200 / 200 / 600s defaults apply (live_case with no cases says so). Explicit over-ceiling values are still refused by `validate_grant_bounds`; the signed row has the same shape.
- **S5** UI grant form (`/projects/<slug>/env`): when the project has planned cases, the form carries `data-live-actions/-probes/-wall` and a note "derived from N planned case(s)"; choosing kind `live_case` fills the three inputs, choosing `crawl` restores the old defaults, and a field the human already edited is never overwritten. The inputs stay plain editable number inputs and the server still validates and caps whatever is posted. With no planned cases the form is unchanged.
- **S6** Derived values stay inside the hard ceilings (2000 actions / 24h / 40000 probes) and the existing grant bounds; the signed HMAC row shape is unchanged.

## What changed (file:line on the branch head)
- `src/autotester/schema/approval.py:62-90` - `PROBES_PER_ACTION`, `MAX_GRANT_ACTIONS`, `MAX_GRANT_WALL_CLOCK_S`, `MAX_GRANT_DAYS`, `MAX_GRANT_PROBES` MOVED here from `core/consent.py` (beside `STANDING_KINDS`); new `GRANT_SAFETY_MARGIN`, `GrantBounds`, `derive_grant_bounds`. D-112 authorizes this file for "any derived-bound field".
- `src/autotester/core/consent.py:20-29,144-165` - imports the constants and `derive_grant_bounds` from the schema; `_grant_command` derives first, then prints. File is exactly 300 lines.
- `src/autotester/stages/run_gates.py:86-122` - `planned_cases(store)`, `derive_live_case_grant(cases)`, `resolve_grant_bounds(store, kind, actions, probes, wall)`.
- `src/autotester/cli_crawl.py:173-180,266-267` - `approve_cmd` options become `int | None` / `float | None`; new `_resolved_bounds` prints the derived line. Docstrings of six helpers condensed to hold the 300-line cap (no behaviour change); `--standing` help text shortened.
- `src/autotester/ui/routes_credentials.py:182-205,219,234` - `_GRANT_SCRIPT`, `_grant_prefill(cases)`, wired into `env_editor_view`.
- `src/autotester/ui/routes_crawl_approval.py:19-22,53-56,60,96` - `_crawl_approval_form(..., prefill)` inserts the attributes and note/script; `MAX_GRANT_PROBES` import moved to the schema; two docstrings condensed to hold 300 lines.
- `tests/test_auto_size_budget.py` (new, 17 tests, S1-S6). `tests/test_consent_followups.py:15-26` import of `MAX_GRANT_PROBES` follows the move. `tests/test_ui_runs_serial_entry_order.py:266-267` pinned hint `--max-actions 9` / `--wall-clock 477.0` becomes `12` / `597.0` (ceil(9 x 1.25), ceil(477 x 1.25)): the deliberate S3 change. `docs/MAP.md` regenerated by `autotester map`.

## Judgement calls (checker, please confirm)
1. Constants moved to `schema/approval.py` because `core/consent.py` was at the 300-line cap and the derivation needs them. `core.consent` no longer re-exports `MAX_GRANT_PROBES` (unused there); the only importers (the UI route and `test_consent_followups.py`) were updated.
2. The margin applies to LIVE_CASE only. Crawl / explore bounds are user-chosen caps for an open-ended crawl, not a plan to size, so they print and default as before (`test_crawl_real_cli` pins 200 / 600).
3. The wall clock is `wall_clock_request_s x 1.25`, so it still contains the 45 s/case judge allowance the gate requests TODAY. Dropping that so only target-acting time counts is D-112 item 1 in `run_budget.py` (fix/run-teardown-stall, not touched here). Deriving from the gate's own request means the derived grant covers the gate on either side of that merge and shrinks when the request does. A bare `steps x 8s` would have produced grants the current gate refuses.
4. A derived action count over 2000 is clamped to 2000 (the cap `approve` accepts); a run that really plans more than 2000 actions can never be granted anyway, and the gate's shortfall line names it.
5. The CLI sizes from ALL non-retired cases, the maximum any run of the project can ask, so the grant covers every subset or priority filter. `planned_cases` repeats `run_launcher`'s `RETIRED` filter (AT-774).
6. UI: the default selected kind is still `crawl`, so a crawl grant never silently gets live-case-sized bounds. The prefill happens on choosing `live_case` (client-side); the server renders the derived values as data attributes plus a visible note, and does not trust the POST (same `_bounds` / `_capped` path).

## Verify (one pytest at a time, `-o addopts=`, in the worktree)
Tests first. Before any src change `tests/test_auto_size_budget.py` could not even be collected (`ImportError`: no `derive_grant_bounds`, `GrantBounds`, `derive_live_case_grant`), so all 17 tests were red.
After:
```
uv run pytest tests/test_auto_size_budget.py tests/test_ui_runs_serial_entry_order.py -o addopts= -q
38 passed
uv run pytest tests/test_auto_size_budget.py tests/test_consent_followups.py tests/test_consent.py tests/test_approve_cli.py tests/test_approve_cli_bounds.py tests/test_approve_target_match.py tests/test_probe_floor_matches_runtime.py tests/test_run_approval_grant_budget.py tests/test_grant_bounds_caps.py tests/test_standing_approval_grant.py -o addopts= -q
212 passed
uv run pytest tests/test_ui_runs_serial_entry_order.py tests/test_ui_crawl_approval.py tests/test_ui_crawl_approval_list.py tests/test_ui_production_approval.py tests/test_ui_runs_live_case_approval.py tests/test_run_launcher_approval.py tests/test_real_acceptance.py tests/test_crawl_real_cli.py -o addopts= -q
89 passed, 1 failed (pre-existing, see below)
uv run pytest tests/test_standing_approval.py tests/test_approval_revoke.py tests/test_approval_signing.py tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py tests/test_approval_residual_callers.py tests/test_run_launcher_priorities_approval.py tests/test_explore_consent.py tests/test_credential_run_approval.py tests/test_parallel_run_approval.py tests/test_team_run_approval.py tests/test_check_crawl_approval.py tests/test_report_export_secrets.py -o addopts= -q
180 passed
uv run pytest tests/test_ui_credential_safety.py tests/test_ui_credential_safety_project.py tests/test_ui_credential_exemption.py tests/test_ui_credential_exemption_scope.py tests/test_ui_credential_bidi.py -o addopts= -q
50 passed
uv run ruff check src tests scripts   ->  All checks passed!
uv run autotester doctor              ->  no function-too-long / file-too-long; MAP.md regenerated and committed; the rest are decision-citation findings (D-112 and others not yet entries in this tree)
```
The one failure, `tests/test_crawl_real_cli.py::test_the_refusals_command_grants_the_run_once_a_human_fills_it_in` ("No such option: --standing,"), is **pre-existing**: it fails identically on `fix/consent-followups` (077b7fb9) in `D:/autoTesting/.claude/worktrees/consent-followups` (`1 failed, 6 passed`). The D-111 hint text "(or --standing, ...)" is split into tokens by the test's `shlex`. Not touched here.
The full suite was NOT run (machine low on memory, by instruction); the checker should run its own sharded sweep.
