# Manifest - t206-env-input-mask (T-206, TA15 fix cycle for qa/verdicts/t206-modeD.md F1, F2)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/team-loop-acceptance.md TA15 (secret inputs masked; every form control labelled)
**Goal task:** T-206
**Dual check:** required (security: a secret typed into the Add credential form was shown in clear)
dual-trigger: security src/autotester/ui/routes_credentials.py:112
**Persona walk:** skip (the checker re-walks TA15 in its own browser; this unit fixes two of its findings)
**Issues addressed:** none (findings F1 high, F2 medium of qa/verdicts/t206-modeD.md, commit fa18f30f on the live-t206 worktree)
**Executor:** claude-sonnet-subagent
**Base SHA:** 15d9ca7b (worktree .worktrees/t206-env-input-mask, branch wave/t206-env-input-mask)
**Code SHA:** e6640a2f

## Criteria (quoted verbatim from the contract)
- **TA15 - Persona walks in the checker's own browser on the local deployment (Mode D).** ... Zero unexplained console errors per page; every form
  control labelled and keyboard-operable; secret inputs masked. `serves:` intent#O8-O15, spec user types (`dev`, `tester`, `subadmin`, `admin`), `auth.md` AU26.

## What changed
- F1 (high): `src/autotester/ui/routes_credentials.py:112` `_custom_credential_card`: the Add credential Value input is now `type='password' autocomplete='new-password'` (the row editor at :70 and /onboard were already masked). The page has no show/hide eye for this form, so none was added.
- F2 (medium): every control on `/projects/<slug>/env` and `/settings/providers` now has a programmatic label. Secret-row value inputs get `aria-label='Value for <KEY>'` (`routes_credentials.py::_env_table`, `routes_settings.py::provider_settings_view`); the platform-URL form, Add credential form and the crawl-approval form (`routes_crawl_approval.py`: kind, production checkbox incl. the forced-on disabled one, scope, expires, UTC offset, max actions, max probes, wall clock, note) use `<label for>` / `id`.
- Test: `tests/test_ui_env_labels.py` (4 cases; reuses `unlabelled_controls` from `tests/test_ui_onboard_a11y.py`, no second helper).
- Not touched: qa/contracts, qa/issues.jsonl, any other route. No new module; routes_crawl_approval.py is 260 lines, routes_credentials.py 243.

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L (a secret-input mask on the credentials surface)
Round: 4 files (3 src + 1 test), 1 criterion (TA15 clauses: masked, labelled), fix cycle 0, est 10 min
Base / checked state: 15d9ca7b / e6640a2f, clean tree
Gate answers: none apply.
Affected tests / full-suite trigger: `tests/test_ui_env_editor.py`, `tests/test_ui_crawl_approval.py`, `tests/test_ui_crawl_approval_list.py`, `tests/test_ui_settings.py`, `tests/test_ui_production_approval.py`, `tests/test_ui_secrets_declaration.py`, `tests/test_ui_onboard_a11y.py` render the edited pages; no schema, no shared helper changed; no full suite run.
Tests[TA15]: tests/test_ui_env_labels.py - the Add credential Value input is `type='password'` with `autocomplete='new-password'`; every input/select/textarea on /env (non-production and production-forced projects) and on /settings/providers has a `<label for>` or aria-label; provider rows name their key. Regression: tests/test_ui_env_editor.py (row masking and show/hide unchanged), tests/test_ui_crawl_approval*.py, tests/test_ui_settings.py.
Pre-check[TA15]: e6640a2f uv run pytest tests/test_ui_env_labels.py tests/test_ui_env_editor.py tests/test_ui_crawl_approval.py tests/test_ui_crawl_approval_list.py tests/test_ui_settings.py tests/test_ui_production_approval.py tests/test_ui_onboard_a11y.py tests/test_ui_secrets_declaration.py -> 57 passed, 1 skipped t=9 blobs=tests/test_ui_env_labels.py:d682e86,tests/test_ui_env_editor.py:bcf3623,tests/test_ui_crawl_approval.py:5ebd27a,tests/test_ui_settings.py:d1e9d3d,tests/test_ui_onboard_a11y.py:3099a06
Falsification[TA15]: green-before/red-after in a copy (scratchpad/t206-env-input-mask, PYTHONPATH to the copy's src): on the base tree the 4 new tests fail (4 failed, run before the fix); control on the fixed copy 4 passed; Add value type=password removed: red `test_the_add_credential_value_box_is_masked_not_clear_text` (1 failed); aria-label on row inputs removed in both modules: red 3 (`..._credentials_page_has_a_label[False]`, `[True]`, `..._provider_settings_has_a_label`); `for=` removed from the crawl-approval Scope label: red 2 (`..._credentials_page_has_a_label[False]`, `[True]`).
Lint: e6640a2f `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean (decision-citation advisories pre-exist).
Metrics: start=2026-10-19T18:00:00Z end=2026-10-19T18:50:00Z wall_min=50 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=unavailable mutants=3 defects_unit=0 defects_6c=0 tests=4 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_ui_env_labels.py tests/test_ui_env_editor.py tests/test_ui_crawl_approval.py tests/test_ui_settings.py tests/test_ui_onboard_a11y.py` -> all pass.
- `uv run ruff check src tests scripts` -> All checks passed!
