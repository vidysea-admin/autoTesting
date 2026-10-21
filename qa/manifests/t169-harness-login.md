# Manifest - t169-harness-login (T-169: acceptance-script login comes from the settings page, not a terminal prompt)

**Status:** checked-PASS (qa/verdicts/t169-harness-login.md + .b.md, dual, cycle 0)
**Fix cycle:** 0
**Contract:** qa/contracts/generic-acceptance.md, qa/contracts/ui-settings.md (US1 closed key set widened by this unit's brief C1; no contract edited, checker folds the amendment), qa/contracts/core-invariants.md (credential rules)
**Goal task:** T-169 (Umesh 2026-10-21: "login and all k liye ui se hi hona chaiye, terminal se thodi")
**Dual check:** required
dual-trigger: auth src/autotester/ui/routes_settings.py:89
**Persona walk:** skip (maker smoke only; checker runs Mode D, the settings page changed)
**Executor:** claude-sonnet-subagent
**Base SHA:** 8956c9bc (worktree .worktrees/t169-harness-login, branch wave/t169-harness-login)

## What changed
- `src/autotester/core/env.py:48-50` - `HARNESS_KEYS = (AUTOTESTER_HARNESS_EMAIL, AUTOTESTER_HARNESS_PASSWORD)`. `AUTOTESTER_*` already counts as a server key (`is_server_key`), so `load_repo_env` exports both and a project cannot claim them.
- `src/autotester/ui/routes_settings.py:28-29,56-59` - the page's closed key set is `(*PROVIDER_KEYS, *HARNESS_KEYS)`; the write path (`provider_settings_submit`, line 89) is unchanged and still the one `set_env_value` writer. The password row is write-only: masked input, no stored value in the field and no show/hide button, even for a `credentials.view` holder (stricter than the other secret keys, which a viewer sees masked). The email row behaves like any non-secret row.
- `scripts/run_real_acceptance.py:55-64,100-109` - new `_harness_login()` reads the two keys from `os.environ` (loaded by `load_repo_env`); with either missing it prints `MISSING <KEY>[, <KEY>]: ... <origin>/settings/providers` to stderr and `main` returns 4, before the app import or any sign-in. `input()`, `getpass` and the `--email` flag are removed. It runs after `--dry-run` returns, so a dry run needs no login. Values are never printed; the tuple is dropped (`login = None`) once signed in.
- `.env.example` - both key names, empty values.
- Tests: `tests/test_ui_settings.py` (+2), `tests/test_real_acceptance.py` (+4 cases).
- Contract note for the checker: ui-settings US1 says "exactly" six keys; the brief widens it. Contract not edited by the maker.

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L (credential handling: a password is written to the repo-root `.env` and read by a sign-in script)
Round: 3 src/script files, 2 test files, 3 criteria, est 20 min - one key tuple, one settings row rule, one script gate
Owners: OG-HARNESS-LOGIN
Base / checked state: 8956c9bc / a271a187, clean tree
Gate answers: none apply (no gate touches the harness login; no new src module)
Affected tests / full-suite trigger: no conftest or shared schema changed; `PROVIDER_KEYS` and `is_server_key` unchanged; callers of the settings page and `.env.example` tests ran. Builder ran no full suite.
Tests[C1]: tests/test_ui_settings.py::test_settings_page_lists_the_harness_login_keys_password_masked_and_never_prefilled, ::test_settings_submit_saves_the_harness_password_to_dotenv_and_never_echoes_it; regression tests/test_ui_settings.py, tests/test_ui_env_labels.py — both keys appear, the password is masked and absent from every page body, the POST round-trips into `.env`
Tests[C2]: tests/test_real_acceptance.py::test_script_exits_naming_the_missing_harness_key_and_the_settings_page (3 cases: email, password, both missing), ::test_script_signs_in_with_the_two_keys_without_prompting_or_printing_them; regression tests/test_real_acceptance.py, tests/test_acceptance_isolation.py — a missing KEY exits 4 naming it and /settings/providers, both set signs in with no prompt (input and getpass raise if touched) and the password is in no output
Tests[C3]: tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads, ::test_env_example_holds_no_secret_looking_value — both names documented with empty values
Pre-check[C1]: a271a187 uv run pytest tests/test_ui_settings.py tests/test_ui_env_labels.py -> 12 passed t=12 blobs=tests/test_ui_settings.py:dd8578b
Pre-check[C2]: a271a187 uv run pytest tests/test_real_acceptance.py tests/test_acceptance_isolation.py -> 23 passed t=82 blobs=tests/test_real_acceptance.py:0444186,tests/test_acceptance_isolation.py:e884768
Pre-check[C3]: a271a187 uv run pytest tests/test_hosting_deploy.py -> 15 passed t=26 blobs=tests/test_hosting_deploy.py:722e59e
Falsification[C1]: copy of routes_settings.py mutated to `_WRITE_ONLY = frozenset()` -> 2 failed (page test and submit test: stored password rendered into the field), restored byte-identical (sha256 of the three touched files compared) -> 8 passed
Falsification[C2]: copy of run_real_acceptance.py mutated so `_harness_login` checks only the email key (`HARNESS_KEYS[:1]`) -> 2 failed (password-missing and both-missing cases), restored byte-identical -> 15 passed
Falsification[C3]: `.env.example` with the AUTOTESTER_HARNESS_PASSWORD line deleted -> test_env_example_documents_every_key_the_code_reads failed, restored byte-identical -> 15 passed
Lint: a271a187 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean
Live browser evidence: SKIP - maker smoke only; checker runs Mode D when UI changed
Metrics: start=2026-10-21T00:00:00Z end=2026-10-21T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 lane=normal check_s=25 mutants=3 defects_unit=0 defects_6c=0 tests=6 tests_min=1

## Residual risk and boundaries
- The script's printed settings URL uses `AUTOTESTER_PUBLIC_ORIGIN` or `http://127.0.0.1:8000` (the documented local port); a server on another port gets a path that still reads correctly.
- A viewer of `/settings/providers` still sees the harness EMAIL prefilled when holding `credentials.view`; only the password is write-only.
- A password containing a newline is refused by the existing `set_env_value` guard (unchanged).
- Real sign-in against a live AutoTester account was not run (needs the account and a live crawl approval).
