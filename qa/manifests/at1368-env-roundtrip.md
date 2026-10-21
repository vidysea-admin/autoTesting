# Manifest - at1368-env-roundtrip (AT-1368, Umesh 2026-10-21 "fix kro")

## Status: checked-PASS (dual: qa/verdicts/at1368-env-roundtrip.md + .b.md, cycle 1)
**Fix cycle:** 1
**Repair base:** 692adbcd
**Contract:** qa/contracts/ui-settings.md (settings .env writer), qa/contracts/browser-and-secrets.md (secret reading); criteria C1, C2 are the unit brief's (.work/briefs/build-at1368-env-roundtrip.md)
**Issues addressed:** AT-1368 (PROPOSED-ISSUE P1 of qa/verdicts/t169-harness-login.md)
**Dual check:** required (security: credential value handling between the settings writer and the loader)
dual-trigger: security src/autotester/core/env.py:84
**Executor:** claude-sonnet-subagent
**Base SHA:** 83e8f71e (worktree .worktrees/at1368-env-roundtrip, branch wave/at1368-env-roundtrip)
**Code SHA:** 8d0d2215 (cycle 0 code d39837eb unchanged; cycle 1 edits one test)

## Criteria (quoted from the brief)
- **C1.** Any printable value (`${X}`, `$X`, literal backslash-n, `\`, `'`, `"`, `#`, spaces, unicode) written through the settings `.env` writer is read back by `load_repo_env` byte-identical; existing keys in the real `.env` stay readable (unquoted plain values identical).
- **C2.** A round-trip property test over those characters, temp dir only; existing env/settings tests stay green; values never echoed in failure messages.

## What changed
- `src/autotester/core/env.py:84` new `read_dotenv(source)`: the one reading of a dotenv file, `dotenv_values(..., interpolate=False)`. `load_repo_env` (line 124) now calls it, so `${X}` in a value is data, not a template (root cause 1).
- `src/autotester/ui/env_editor.py::_render_value` (line 28) + new `_reads_back`: a candidate (double quoted, single quoted, bare) is accepted only if BOTH readers (`browser.secrets.parse_env` and `read_dotenv`) return the value byte-identical (root cause 2: dotenv decodes backslash-n in double quotes and a doubled backslash in single quotes; parse_env decodes nothing). Double quotes stay first, so every value the old writer could store is written as before.
- Same one-argument fix in the other three readers of the repo `.env` values so redaction masks the string the login actually types: `providers/litellm_provider.py::_env_secret_values`, `core/redact_cli.py::env_values`, `core/image_privacy.py` (tesseract path). They now import `read_dotenv`; no behaviour change except no interpolation.
- Residual (stated, not hidden): where no quoting satisfies both readers the writer still REFUSES with `InvalidEnvValue` (never stores altered). The refused class is: (a) values that need quoting (` #`, leading/trailing whitespace, a leading or trailing quote) and hold BOTH quote kinds, e.g. `p@ss #1 "q" 'r'`; (b) values that start with a quote character and hold the other kind, e.g. `"'`; (c) values that end in a backslash and need quoting (a space then a backslash); (d) some backslash shapes the old writer stored (it double-quoted them and the loader later decoded them). Closing it needs `parse_env` to decode dotenv escapes, which would change how SecretStore reads existing quoted values; left for a human decision. Pinned by `test_a_value_no_quoting_can_store_exactly_is_refused_never_stored_altered` and, from fix cycle 1, `test_a_value_that_cannot_round_trip_is_refused_not_mangled`.
- Fix cycle 1 (dual check C2 FAIL, no product code change): `tests/test_ui_credential_safety_project.py::test_a_value_that_cannot_round_trip_is_refused_not_mangled` pinned `a"b'c` as refused; the unit makes that value storable and exactly round-trippable (correct C1 behaviour), so the test was red ("DID NOT RAISE InvalidEnvValue"; green on base 83e8f71e). **Protected test change, reason:** the old input stopped being a refused value by design; the input is now `p@ss #1 "q" 'r'` (needs quoting for ` #`, holds both quote kinds, which `_render_value` still refuses). Assertions kept (refused, `.env` bytes unchanged) plus one added (the refusal message does not echo the value); docstring rewritten to say why.
- Not touched: qa/contracts, `.env`, `parse_env`, qa/issues.jsonl.

## Tests
`tests/test_env_loading.py` (edited in place, 3 added tests; values spelled with a `¦` placeholder for backslash so no tool halves them). Fix cycle 1: `tests/test_ui_credential_safety_project.py` (one stale input changed, see What changed).

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L (credential handling)
Round: fix cycle 1, 2 files (1 test + this manifest), 1 failed criterion (C2), est 15 min
Base / checked state: 83e8f71e / 8d0d2215, clean tree; Repair base 692adbcd
Gate answers: none apply.
Affected tests / full-suite trigger: `tests/test_ui_env_editor.py`, `tests/test_ui_settings.py`, `tests/test_server_settings.py` (writer), `tests/test_container_redaction.py`, `tests/test_image_privacy.py` (readers); no schema or shared helper signature changed; no full suite run.
Tests[C1]: tests/test_env_loading.py::test_every_printable_value_the_settings_writer_stores_loads_byte_identical — 40 values (`${HOME}`, `$X`, `${X}${Y}`, backslash-n literal, lone/trailing/doubled backslash, both quote kinds, `#`, ` #`, spaces, tab, unicode, `=`) written with `set_env_value`, loaded with `load_repo_env`, equality asserted; plus tests/test_env_loading.py::test_a_value_the_old_writer_left_bare_still_loads_unchanged (hand-written bare value unchanged), tests/test_ui_env_editor.py, tests/test_ui_settings.py, tests/test_server_settings.py (writer), tests/test_container_redaction.py, tests/test_image_privacy.py (readers), tests/test_approval_prod_gate.py and tests/test_ui_auth_envkeys.py (callers of `load_repo_env`, identifier hits).
Pre-check[c1]: 8d0d2215 uv run pytest tests/test_env_loading.py tests/test_ui_env_editor.py tests/test_ui_settings.py tests/test_server_settings.py tests/test_container_redaction.py tests/test_image_privacy.py tests/test_approval_prod_gate.py tests/test_ui_auth_envkeys.py -> green, all passed (these files are inside the 588 passed, 2 skipped union run of Pre-check[C2], t=225)
Falsification[c1]: in a throwaway copy (D:/autoTesting/.work/tmp/fals1368c1, PYTHONPATH to the copy's src) `interpolate=False` flipped to True in `read_dotenv`: tests/test_env_loading.py red, `test_every_printable_value_the_settings_writer_stores_loads_byte_identical` fails.
Tests[C2]: tests/test_env_loading.py::test_every_printable_value_the_settings_writer_stores_loads_byte_identical, tests/test_env_loading.py::test_a_value_no_quoting_can_store_exactly_is_refused_never_stored_altered, tests/test_ui_credential_safety_project.py::test_a_value_that_cannot_round_trip_is_refused_not_mangled — the property test runs in tmp_path only (never the repo-root `.env`) and prints case indexes, never values; the second and third pin the refuse-never-alter edge (the third is the fix-cycle-1 repair: refused, `.env` bytes unchanged, message value-free); plus every other file in the union run.
Pre-check[c2]: 8d0d2215 uv run pytest tests/test_approval_prod_gate.py tests/test_citation_advisory.py tests/test_citation_seals.py tests/test_cli_sweep.py tests/test_container_redaction.py tests/test_doctor.py tests/test_env_loading.py tests/test_failure_bundle.py tests/test_goal_done_check_shapes.py tests/test_goal_done_checks.py tests/test_issue_ids.py tests/test_ledger_backref.py tests/test_ledger_checks.py tests/test_ledger_tick_integrity.py tests/test_mc_sessionstart_unclosed.py tests/test_oracle_registry.py tests/test_real_acceptance.py tests/test_role_port_authz.py tests/test_ui_auth_envkeys.py tests/test_ui_auth_escalation.py tests/test_ui_auth_groups.py tests/test_ui_auth_hardening.py tests/test_ui_auth_policy_table.py tests/test_ui_auth_surface.py tests/test_ui_crawl_approval.py tests/test_ui_dashboard.py tests/test_ui_env_labels.py tests/test_ui_settings.py tests/test_ui_sidebar.py tests/test_ui_env_editor.py tests/test_server_settings.py tests/test_image_privacy.py tests/test_ui_credential_safety_project.py -> 588 passed, 2 skipped t=225
Falsification[c2]: in the copy, `_render_value` changed to always return the double-quoted form (writer never refuses): tests/test_ui_credential_safety_project.py::test_a_value_that_cannot_round_trip_is_refused_not_mangled red ("DID NOT RAISE InvalidEnvValue"), plus test_a_stored_credential_reads_back_exactly[has"double] red.

## Test selection
Candidates from `python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo <WT> --affected 83e8f71e..HEAD --mode unit --list --candidates` (29 reference-hit test files, 57 siblings, truncated=false). Selected by the maker reading the diff (no separate model selector: the set is the whole reference-hit list). All 29 reference-hit files were RUN in Pre-check[C2] and are green, together with the writer/reader files and the credential-safety file.
Identifier hits (real coupling to the changed code): tests/test_approval_prod_gate.py (`load_repo_env`), tests/test_container_redaction.py (`env_values`), tests/test_env_loading.py, tests/test_ui_auth_envkeys.py (`load_repo_env`); all in the Tests lines.
Fragment-only hits (matched on text of this unit's qa/manifests, qa/verdicts, qa/checkpoints, or on test_env_loading.py fragments, not on product code): tests/test_citation_advisory.py, tests/test_citation_seals.py, tests/test_cli_sweep.py, tests/test_doctor.py, tests/test_failure_bundle.py, tests/test_goal_done_check_shapes.py, tests/test_goal_done_checks.py, tests/test_issue_ids.py, tests/test_ledger_backref.py, tests/test_ledger_checks.py, tests/test_ledger_tick_integrity.py, tests/test_mc_sessionstart_unclosed.py, tests/test_oracle_registry.py, tests/test_real_acceptance.py, tests/test_role_port_authz.py, tests/test_ui_auth_escalation.py, tests/test_ui_auth_groups.py, tests/test_ui_auth_hardening.py, tests/test_ui_auth_policy_table.py, tests/test_ui_auth_surface.py, tests/test_ui_crawl_approval.py, tests/test_ui_dashboard.py, tests/test_ui_env_labels.py, tests/test_ui_settings.py, tests/test_ui_sidebar.py. Each is in the Pre-check[C2] command and passed; none is dropped.
Dropped: none.
Sibling: src/autotester/core/env.py:50,96 — changed (`load_repo_env` now reads through `read_dotenv`, interpolate=False)
Sibling: src/autotester/core/image_privacy.py:49,66 — changed (`_env_tesseract` reads through `read_dotenv`)
Sibling: src/autotester/core/redact_cli.py:33,43 — changed (`env_values` reads through `read_dotenv`)
Sibling: src/autotester/providers/litellm_provider.py:56,188 — changed (`_env_secret_values` reads through `read_dotenv`)
Sibling: src/autotester/ui/env_editor.py:28,75 — changed (`_render_value`)
Sibling: src/autotester/cli.py:19,45 — not affected because it only calls `load_repo_env`, whose signature is unchanged (covered by tests/test_env_loading.py::test_the_CLI_actually_calls_the_loader_before_any_command)
Sibling: src/autotester/core/ids.py:29, src/autotester/stages/leak_evidence.py:10,28,47, src/autotester/ui/app.py:20,60, src/autotester/ui/credential_guard.py:42,60 — not affected because they call `load_repo_env` with the same signature; only the interpolation inside the loader changed
Sibling: src/autotester/core/env.py:51, src/autotester/ui/routes_settings.py:29, scripts/run_real_acceptance.py:11 (`AUTOTESTER_HARNESS_PASSWORD` copies) — not affected because they name a key, not a value shape
Sibling: scripts/check_crawl_approval.py:33,72, scripts/explore_proof.py:34,161, scripts/run_real_acceptance.py:25,81, tests/conftest.py:76,78 — not affected because they are `load_repo_env` call sites with an unchanged signature
Sibling: qa/evidence/** `load_repo_env` call sites (t122, t168, t202, t204, t209, text-availability) — not affected because they are archived probe scripts, not product code or collected tests

Lint: 8d0d2215 `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean (decision-citation advisories pre-exist).
Live browser evidence: SKIP - maker smoke only; no UI change (writer/reader logic only); checker runs Mode D if it judges the settings page affected.
Metrics: start=2026-10-21T09:00:00Z end=2026-10-21T10:00:00Z wall_min=60 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=unavailable mutants=2 defects_unit=0 defects_6c=0 tests=3 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_env_loading.py tests/test_ui_env_editor.py tests/test_ui_settings.py tests/test_server_settings.py tests/test_container_redaction.py tests/test_image_privacy.py` -> all pass.
- `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean.
