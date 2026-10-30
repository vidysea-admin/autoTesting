# Manifest - d110-allow-all (D-110 opt-in `*` allow-all for the Host and Origin guards)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/auth.md (AU18, AU19, AU20; to be amended by the checker per D-110)
**Goal task:** none (T-204 linked by D-110)
**Authority:** D-110 (Approved-by: Umesh, maker session chat 2026-10-26, chose "Make `*` a wildcard" after the CSRF/host-spoofing tradeoff was stated)
**Date:** 2026-10-30
**Dual check:** required
dual-trigger: auth src/autotester/ui/helpers.py:201
**Round cap:** (a) SECURITY CLASS -- auth: the unit changes the D-066 Host/Origin guards (`_host_allowed`, `_origin_allowed`) and the AU20 hosted-startup check, i.e. CSRF and Host-spoofing protection on every authenticated route; D-014 never caps it.
**Persona walk:** skip (no screen or navigation change; startup/guard configuration only)
**Issues addressed:** none (clears the `decision-citation-dangling` D-110 notes other manifests recorded once this lands)
**Executor:** claude-opus-main
**Executor rationale:** two small source edits already written in the main checkout; landed here verbatim as a patch
**Base SHA:** 19a9dd79 (master)
**Code SHA:** 51dbbf80 (worktree .claude/worktrees/d110-allow-all, branch wave/d110-allow-all)

## Criteria (from D-110 `What` / `Result`)
- C1 - `*` in `AUTOTESTER_ALLOWED_ORIGINS` makes `_origin_allowed` True for any Origin (cross-site state-changing POST passes) and `_host_allowed` True for any Host.
- C2 - `*` in `AUTOTESTER_ALLOWED_HOSTS` makes `_host_allowed` True for any Host only; a cross-site POST is still refused.
- C3 - With `*` in either list, hosted startup (`_check_hosted`) treats the allow-list as satisfied and does not require `AUTOTESTER_PUBLIC_ORIGIN`, on any bind including wildcard.
- C4 - With no `*`, every guard and startup refusal is unchanged (AU18-AU20); a comma-only list still does not satisfy "set"; `*` is the only token with this meaning and literal names still match exactly (`_listed` still drops `*`).

## What changed
- `src/autotester/ui/helpers.py:195-199` - `_listed` docstring; new `_allow_all(name)` (:201) tokenises the env value the same way `_listed` does and returns `"*" in tokens`.
- `src/autotester/ui/helpers.py:206-212` - `_origin_allowed` short-circuits on `_allow_all("AUTOTESTER_ALLOWED_ORIGINS")`.
- `src/autotester/ui/helpers.py:224-230` - `_host_allowed` short-circuits on `*` in either list.
- `src/autotester/auth/config.py:61-78` - `_check_hosted`: `*` satisfies the allow-list; with `*` it returns before `_check_public_origin` / the own-origin pin.
- Tests (edited in place): `tests/test_ui_origin_guard.py` (two old "no wildcard" assertions inverted; two new tests for C1, C2), `tests/test_ui_auth_own_origin.py` (startup parametrize rows for `*`; two PUBLIC rows for wildcard bind with no PUBLIC_ORIGIN; wildcard-bind test now asserts start), `tests/test_ui_auth_host_and_consent.py` (AU18 login POST with ORIGINS=* now 303).
- File sizes: helpers.py 299, config.py 153 (cap 300).
- Not touched: `qa/contracts/`, `docs/DECISIONS.md` (D-110 already on master), ARCHITECTURE.md, enforcement paths.

## Verification (main checkout, same content as Code SHA)
- `uv run pytest tests/test_ui_origin_guard.py tests/test_ui_auth_own_origin.py tests/test_ui_auth_host_and_consent.py` -> `218 passed, 1 warning in 17.03s`
- `uv run pytest` (full) -> `7 failed, 9807 passed, 10 skipped, 85 warnings in 4290.89s`. None of the 7 is in a D-110 file; maker believes them environmental/pre-existing (unverified against a baseline - checker to confirm):
  - tests/test_container_ci_workflow.py::test_exit_trap_removes_container_without_unbound_error
  - tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild
  - tests/test_infra_trio.py::test_verify_gates_keeps_exit_code[0], [3]
  - tests/test_role_port_mail.py::test_w2_a_mail_that_arrived_is_observed_through_the_read_only_reader
  - tests/test_ui_auth_envkeys.py::test_au21_no_onboarded_key_becomes_an_environment_variable[anthropic-ANTHROPIC_BASE_URL]
  - tests/test_ui_auth_envkeys.py::test_au21_env_add_and_undeclare_leave_nothing_exported[anthropic-ANTHROPIC_BASE_URL]
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `4 violation(s)`, all `root-clutter` in the main checkout (`at113-fixture-wn6g4n_e`, `HANDOFF.md`, `nul`, `pytest-of-unknown`), none from this unit.

## Accepted risk (D-110, stated to Umesh before the choice)
`*` re-opens Host-header spoofing (AU19) and, with writes enabled, CSRF on state-changing routes (AU18). Opt-in only; default unchanged.
