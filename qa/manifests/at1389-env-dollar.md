# Manifest - at1389-env-dollar (AT-1389, Umesh-delegated default 2026-10-21)

## Status: ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/ui-settings.md (settings page), browser-and-secrets.md (secret reading); criteria C1-C3 are the unit brief's (.work/briefs/build-at1389-env-dollar.md); decision record qa/gates/at1389-env-dollar-check.md
**Issues addressed:** AT-1389
**Dual check:** required (security: credential file handling)
dual-trigger: security src/autotester/core/env.py:98
**Executor:** claude-sonnet-subagent
**Base SHA:** c437d3a5 (worktree .worktrees/at1389-env-dollar, branch wave/at1389-env-dollar)
**Code SHA:** ffbe43e9

## Criteria (quoted from the brief)
- **C1.** `uv run autotester doctor` reports how many repo-root .env values contain "${" and lists their KEY NAMES only (never values), as a warning; zero -> no line. Read through core/env.py's existing loader; no new .env parser.
- **C2.** The settings page (/settings/providers) shows the same warning (count + key names) to an admin.
- **C3.** Tests use a temp .env (never the real one); a test asserts no value text appears in the output.

## What changed
- `src/autotester/core/env.py:98` new `dollar_value_keys(root)` (sorted key names whose value contains `${`, read via the existing `read_dotenv`, no new parser) and `dollar_warning(keys)` (the one sentence both surfaces show; empty for no keys).
- `src/autotester/ledger/env_warning.py` (new, one job, same pattern as `committed_fresh.py`): `check_env_dollar(root)` -> one `Violation("env-dollar-literal", ".env", ...)` or none.
- `src/autotester/ledger/advisory.py`: `env-dollar-literal` added to `NON_BLOCKING` (warning, doctor stays green). `src/autotester/doctor.py::run` calls it.
- `src/autotester/ui/routes_settings.py::provider_settings_view`: alert paragraph `#env-dollar-warning` above the table when keys exist (the page is already behind `settings.manage`).
- `docs/MAP.md` regenerated (`autotester map`) for the new module.
- Not touched: qa/contracts, `.env`, expansion behaviour (literal values stay, AT-1368).
- Known baseline: `docs/SNAPSHOT.md` is stale vs HEAD (D-107 not in the snapshot) before and after this unit; not regenerated here (unrelated).

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L (credential file handling)
Round: cycle 0, 7 files, 3 criteria, est 40 min
Base / checked state: c437d3a5 / ffbe43e9
Gate answers: qa/gates/at1389-env-dollar-check.md answered (product reports it; no expansion).
Affected tests / full-suite trigger: tests that import core.env, doctor, advisory or the settings route; no schema or shared signature changed; no full suite run.
Tests[C1]: tests/test_env_dollar_warning.py::test_keys_with_dollar_brace_are_listed_by_name_and_values_stay_literal, ::test_a_lone_dollar_sign_or_a_missing_file_gives_no_keys, ::test_doctor_warns_with_count_and_key_names_but_stays_green_and_prints_no_value, ::test_doctor_prints_no_env_line_when_no_value_contains_dollar_brace, ::test_doctor_command_output_carries_the_warning_and_no_value (real `autotester doctor` command via CliRunner) — they cover the key listing, the zero-keys-no-line rule, the non-blocking warning and the real command output
Pre-check[C1]: ffbe43e9 uv run pytest tests/test_env_dollar_warning.py tests/test_env_loading.py tests/test_ui_settings.py tests/test_doctor.py tests/test_citation_advisory.py tests/test_citation_known_disputed.py tests/test_ui_env_labels.py tests/test_ui_auth_envkeys.py tests/test_ui_env_editor.py -> 113 passed, 1 skipped
Falsification[C1]: in place on a committed tree, restored from a backup copy: `check_env_dollar` removed from `doctor.run` -> test_doctor_command_output_carries_the_warning_and_no_value red (1 failed); restored, tree clean.
Tests[C2]: tests/test_env_dollar_warning.py::test_settings_page_shows_count_and_key_names_and_no_value, ::test_settings_page_has_no_warning_when_the_env_is_clean — they cover the page warning with count and key names and its absence on a clean env
Pre-check[C2]: ffbe43e9 uv run pytest tests/test_env_dollar_warning.py tests/test_env_loading.py tests/test_ui_settings.py tests/test_doctor.py tests/test_citation_advisory.py tests/test_citation_known_disputed.py tests/test_ui_env_labels.py tests/test_ui_auth_envkeys.py tests/test_ui_env_editor.py -> 113 passed, 1 skipped
Falsification[C2]: warning paragraph forced off in `provider_settings_view` -> test_settings_page_shows_count_and_key_names_and_no_value red; restored.
Tests[C3]: all tests in tests/test_env_dollar_warning.py use a tmp_path `.env` with AUTOTESTER_ROOT pointed at it; the doctor, settings-page and summary tests assert the secret values (and fragments `HOME`, `NOPE`, `pa55`) are absent from the output — they cover the no-value-leak criterion on every surface.
Pre-check[C3]: ffbe43e9 uv run pytest tests/test_env_dollar_warning.py tests/test_env_loading.py tests/test_ui_settings.py tests/test_doctor.py tests/test_citation_advisory.py tests/test_citation_known_disputed.py tests/test_ui_env_labels.py tests/test_ui_auth_envkeys.py tests/test_ui_env_editor.py -> 113 passed, 1 skipped
Falsification[C3]: `dollar_value_keys` changed to return `KEY=value` -> 4 of 5 value-leak tests red (4 failed, 1 passed); restored.

## Test selection
Reference hits for `load_repo_env`/`read_dotenv`/`NON_BLOCKING`/`provider_settings_view` were run: test_env_loading, test_ui_settings, test_doctor, test_citation_advisory, test_citation_known_disputed, test_ui_env_labels, test_ui_auth_envkeys, test_ui_env_editor. Dropped: none.
Sibling: src/autotester/ui/routes_server_settings.py (`/settings/server`) - not affected, different page and no `.env` read.
Sibling: src/autotester/core/env.py:`load_repo_env` - not affected, loader behaviour unchanged (the new functions only read).

Lint: ffbe43e9 `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> no blocking rule of this unit; the only remaining violations are stale-generated/stale-committed for docs/SNAPSHOT.md (baseline) and docs/MAP.md stale-committed, which clears once this commit's MAP.md is the committed blob.
Live browser evidence: SKIP - maker smoke only; checker runs Mode D when UI changed.
Metrics: start=2026-10-21T13:30:00Z end=2026-10-21T14:30:00Z wall_min=60 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=unavailable mutants=3 defects_unit=0 defects_6c=0 tests=7 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_env_dollar_warning.py tests/test_env_loading.py tests/test_ui_settings.py tests/test_doctor.py` -> all pass.
- `uv run ruff check src tests scripts` -> All checks passed!
