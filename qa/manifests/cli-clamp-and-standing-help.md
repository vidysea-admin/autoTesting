# Manifest - cli-clamp-and-standing-help

**Status:** checked-PASS
**Fix cycle:** 1
**Security trigger:** YES (light) - touches the consent grant derivation (`schema/approval.py::derive_grant_bounds`, D-018/D-112). It only adds input rejection and a message; no ceiling, signing or row shape changes. Single checker is enough.
**Authority:** `qa/verdicts/auto-size-budget.b.md` findings F1 (line 36), F2 (line 37) and the `--standing` scoping ask; D-112 item 2 keeps the 2000-action / 24h / 40000-probe ceilings.
**Branch:** `fix/cli-clamp-and-standing-help` (worktree `D:/autoTesting/.claude/worktrees/cli-clamp`, off master a6e03fa4)
**Not done by the maker:** no merge, no push, nothing in the main checkout, no edit to `qa/contracts/` or `docs/DECISIONS.md`.

## Cycle 1 (answers `qa/verdicts/cli-clamp-and-standing-help.b.md` F1-F3 and checker A's addendum)
- **C7 (B-F1, blocking)** The refusal path never raises on malformed bounds: `schema/approval.py::hint_grant_bounds` (new) echoes negative / NaN / infinite / bool bounds unchanged and otherwise calls `derive_grant_bounds`; `core/consent.py::_grant_command` (line 150) now calls it. `derive_grant_bounds` stays strict, so `approve` is unchanged. Tests: `require_approval` with 6 malformed triples for EVERY `ApprovalKind` raises `ApprovalRequired` ("refusing to start"); `explore demo --wall-clock inf|nan|-5` and `--max-actions -1` exit 2 with the refusal (CliRunner), not a `ValueError`. Not done: rejecting negatives at the `explore` option itself, because the coordinator's test requires exit 2 for `inf`; the gate refuses them with a plain message.
- **C8 (B-F2)** The clamp warning's wall clock is whole seconds rounded up (`_whole_seconds`): 86400.0004 reads `planned 86401s > ceiling 86400s`, 1234567.0 reads `1234567s`, inf reads `inf`; no `:g`.
- **C9 (B-F3)** A bool is rejected by the new validation (`_is_valid_bounds`).
- **C10 (pre-existing red)** `tests/advice_scan.py` gets `KNOWN_NUMERIC_IMPORTS = {"MAX_GRANT_PROBES"}` (an int bound to `MAX_GRANT_ACTIONS * PROBES_PER_ACTION`, which `_module_level_names` cannot prove numeric), merged into `bound_elsewhere` in `unresolved_in_source`. The filter is not loosened by shape: one named constant. `test_the_collector_reports_what_it_could_not_resolve` now passes.

## Criteria (judge against these)
- **C1 (F1, refusal hint)** A LIVE_CASE refusal whose plan is over a grant ceiling says so before "Grant one with:", naming each over bound as `<bound>: planned N > ceiling M` (actions, probes, `wall clock` in s) and advising to split the cases. A plan inside every ceiling, and every other kind, adds nothing.
- **C2 (F1, `approve`)** `autotester approve --kind live_case` with flags omitted appends the same warning to its cyan "derived from N planned case(s)" line when the planned request is over a ceiling. It still signs the clamped grant (exit 0, behaviour of F1 unchanged; only the silence is removed). A plan that fits prints no ceiling text.
- **C3 (F1, one place)** The wording and the over-ceiling test live once: `schema/approval.py::grant_clamp_warning`. The two callers pass the gate's own request (`consent._grant_command` args; `run_gates._planned_request`).
- **C4 (F2, total derivation)** `derive_grant_bounds` raises `ValueError("grant bounds must be non-negative and finite ...")` for any negative, NaN or infinite actions / probes / wall clock (all kinds); an input whose margin would overflow (wall 1.7e308, actions 10**400) saturates at the ceiling instead of raising `OverflowError`. Valid inputs and the non-LIVE_CASE pass-through give the same results as before.
- **C5 (`--standing` help)** `autotester approve --help` shows `crawl only; until revoked (autotester revoke)` for `--standing`; `tests/test_cli_advice_resolves.py` site set and count (`EXPECTED_SITE_COUNT = 32`) unchanged.
- **C6 (design rules)** `cli_crawl.py` and `core/consent.py` stay at <= 300 lines; no function > 50 lines; no new module; ruff clean; `doctor` reports no rule this change touches.

## What changed (file:line on the branch head)
- `src/autotester/schema/approval.py:84-122` - new `_margined` (saturating margin), `derive_grant_bounds` validates then uses it (F2), new `grant_clamp_warning` (F1).
- `src/autotester/core/consent.py:25-29,262-264` - imports `grant_clamp_warning`; the refusal message inserts it before "Grant one with:" (net 0 lines, file is exactly 300).
- `src/autotester/stages/run_gates.py:96-109,120-134` - `_planned_request(cases)` (one place for the gate's request), `derive_live_case_grant` uses it, `resolve_grant_bounds` appends the warning to its note.
- `src/autotester/cli_crawl.py` (`approve_cmd`) - `--standing` help text; the success `secho` `fg=` joined onto the previous line to stay at 300 lines.
- `tests/test_grant_clamp_notes.py` (new, 17 tests, C1-C5). `tests/test_auto_size_budget.py:115-118` - the old "non-finite wall clock passes through untouched" test is inverted in place (that behaviour is the F2 defect).

## Judgement calls (checker, please confirm)
1. Rejection (not clamping) for negative / NaN / inf; saturation only for finite-but-huge values, whose correct answer is the ceiling. Validation applies to every kind, not only LIVE_CASE; no existing caller passes such values (13 approval/consent files green).
2. `approve` still signs a clamped grant and exits 0 (the checker's F1 note suggested saying so, not refusing). Refusing would change D-112 behaviour and needs a human call.
3. Warning triggers only when the PLAN (raw request) exceeds a ceiling, not when only the 1.25x margin is clamped, since in that case the grant still covers the run.

## Tests run, cycle 1 (worktree, 2 files per call, `-o addopts=`)
- `tests/test_cli_advice_resolves.py tests/test_grant_clamp_notes.py` -> 96 passed (the previously red collector test is green; red first for the new tests: collection ImportError on `hint_grant_bounds`)
- `tests/test_auto_size_budget.py tests/test_consent.py` -> 54 passed
- `tests/test_approve_cli.py tests/test_approve_cli_bounds.py` -> 21 passed
- `tests/test_grant_bounds_caps.py tests/test_consent_followups.py` -> 85 passed
- `tests/test_explore_consent.py tests/test_ui_crawl_approval.py` -> 11 passed
- `tests/test_run_launcher_approval.py tests/test_ui_runs_live_case_approval.py` -> 25 passed; `tests/test_standing_approval.py tests/test_standing_approval_grant.py` -> 32 passed; `tests/test_credential_run_approval.py tests/test_approval_signing.py` -> 43 passed
- `uv run autotester doctor` -> only the 2 pre-existing SNAPSHOT.md staleness violations
- `uv run ruff check src tests scripts` -> All checks passed. Lines: cli_crawl.py 300, consent.py 300, approval.py 286, advice_scan.py 291.

## Tests run, cycle 0 (worktree, `uv run pytest <2 files> -o addopts=`, one at a time)
- `tests/test_grant_clamp_notes.py tests/test_auto_size_budget.py` -> 34 passed (red first: collection ImportError on `grant_clamp_warning` before the code).
- `tests/test_cli_advice_resolves.py tests/test_consent.py` -> 77 passed, **1 failed**: `test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` (`ui/routes_crawl_approval.py:203` unresolved). **Pre-existing**: identical failure on a clean detached worktree at a6e03fa4 (no change of mine). Not touched here.
- `tests/test_standing_approval_grant.py tests/test_ui_runs_serial_entry_order.py` -> 36 passed
- `tests/test_approve_cli.py tests/test_approve_cli_bounds.py` -> 21 passed
- `tests/test_grant_bounds_caps.py tests/test_consent_followups.py` -> 85 passed
- `tests/test_run_approval_grant_budget.py tests/test_ui_runs_live_case_approval.py` -> 20 passed
- `tests/test_run_launcher_approval.py tests/test_ui_crawl_approval.py` -> 24 passed
- `tests/test_explore_consent.py tests/test_approval_signing.py` -> 21 passed
- `tests/test_credential_run_approval.py tests/test_standing_approval.py` -> 42 passed
- `uv run ruff check src tests scripts` -> All checks passed
- `uv run autotester doctor` -> 2 violations, both `stale-generated`/`stale-committed` for `docs/SNAPSHOT.md` (pre-existing, master moved since the last snapshot; not regenerated here). Line counts: cli_crawl.py 300, consent.py 300, approval.py 263, run_gates.py 134.
- Not run (low-memory machine): the whole suite.
