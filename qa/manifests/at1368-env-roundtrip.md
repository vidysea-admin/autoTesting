# Manifest - at1368-env-roundtrip (AT-1368, Umesh 2026-10-21 "fix kro")

Status: ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/ui-settings.md (settings .env writer), qa/contracts/browser-and-secrets.md (secret reading); criteria C1, C2 are the unit brief's (.work/briefs/build-at1368-env-roundtrip.md)
**Issues addressed:** AT-1368 (PROPOSED-ISSUE P1 of qa/verdicts/t169-harness-login.md)
**Dual check:** required (security: credential value handling between the settings writer and the loader)
dual-trigger: security src/autotester/core/env.py:84
**Executor:** claude-sonnet-subagent
**Base SHA:** 83e8f71e (worktree .worktrees/at1368-env-roundtrip, branch wave/at1368-env-roundtrip)
**Code SHA:** d39837eb

## Criteria (quoted from the brief)
- **C1.** Any printable value (`${X}`, `$X`, literal backslash-n, `\`, `'`, `"`, `#`, spaces, unicode) written through the settings `.env` writer is read back by `load_repo_env` byte-identical; existing keys in the real `.env` stay readable (unquoted plain values identical).
- **C2.** A round-trip property test over those characters, temp dir only; existing env/settings tests stay green; values never echoed in failure messages.

## What changed
- `src/autotester/core/env.py:84` new `read_dotenv(source)`: the one reading of a dotenv file, `dotenv_values(..., interpolate=False)`. `load_repo_env` (line 124) now calls it, so `${X}` in a value is data, not a template (root cause 1).
- `src/autotester/ui/env_editor.py::_render_value` (line 28) + new `_reads_back`: a candidate (double quoted, single quoted, bare) is accepted only if BOTH readers (`browser.secrets.parse_env` and `read_dotenv`) return the value byte-identical (root cause 2: dotenv decodes backslash-n in double quotes and a doubled backslash in single quotes; parse_env decodes nothing). Double quotes stay first, so every value the old writer could store is written as before.
- Same one-argument fix in the other three readers of the repo `.env` values so redaction masks the string the login actually types: `providers/litellm_provider.py::_env_secret_values`, `core/redact_cli.py::env_values`, `core/image_privacy.py` (tesseract path). They now import `read_dotenv`; no behaviour change except no interpolation.
- Residual (stated, not hidden): where no quoting satisfies both readers the writer still REFUSES with `InvalidEnvValue` (never stores altered). Class: starts with a quote char and holds the other quote kind (e.g. `"'`), or ends in a backslash while needing quotes (leading/trailing whitespace, ` #`). Pinned by `test_a_value_no_quoting_can_store_exactly_is_refused_never_stored_altered`. Closing it needs `parse_env` to decode dotenv escapes, which would change how SecretStore reads existing quoted values; left for a human decision.
- Not touched: qa/contracts, `.env`, `parse_env`, qa/issues.jsonl.

## Tests
`tests/test_env_loading.py` (edited in place, 3 added tests; values spelled with a `¦` placeholder for backslash so no tool halves them).

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L (credential handling)
Round: 6 files (5 src + 1 test), 2 criteria, fix cycle 0, est 30 min
Base / checked state: 83e8f71e / d39837eb, clean tree
Gate answers: none apply.
Affected tests / full-suite trigger: `tests/test_ui_env_editor.py`, `tests/test_ui_settings.py`, `tests/test_server_settings.py` (writer), `tests/test_container_redaction.py`, `tests/test_image_privacy.py` (readers); no schema or shared helper signature changed; no full suite run.
Tests[c1]: tests/test_env_loading.py::test_every_printable_value_the_settings_writer_stores_loads_byte_identical — 40 values (`${HOME}`, `$X`, `${X}${Y}`, backslash-n literal, lone/trailing/doubled backslash, both quote kinds, `#`, ` #`, spaces, tab, unicode, `=`) written with `set_env_value`, loaded with `load_repo_env` (HOME and X exported to a sentinel so interpolation would show), equality asserted; plus `test_a_value_the_old_writer_left_bare_still_loads_unchanged` (hand-written bare value unchanged).
Pre-check[c1]: d39837eb uv run pytest tests/test_env_loading.py tests/test_ui_env_editor.py tests/test_ui_settings.py tests/test_server_settings.py tests/test_container_redaction.py tests/test_image_privacy.py -> 171 passed, 2 skipped t=72
Falsification[c1]: in a copy (.work/tmp/fals1368, PYTHONPATH to the copy's src) `interpolate=False` flipped to True in `read_dotenv`: red, cases [6, 22] (`a${HOME}b`, `${X}${Y}`) did not round-trip.
Tests[c2]: tests/test_env_loading.py::test_every_printable_value_the_settings_writer_stores_loads_byte_identical, tests/test_env_loading.py::test_a_value_no_quoting_can_store_exactly_is_refused_never_stored_altered — the property test runs in tmp_path only (never the repo-root `.env`), its failure message prints case indexes, never values, and the second pins the refuse-never-alter edge; existing env/settings tests green in the Pre-check above.
Pre-check[c2]: d39837eb uv run pytest tests/test_env_loading.py -> 9 passed (6 existing + 3 new) t=22
Falsification[c2]: in the copy, `_render_value` reverted to double-quote-only (the old writer): red, 16 cases [3, 9, 10, 11, 17, 18, 23, 24, 25, 27, 35, 36, 37, 38, 39, 40] fail (backslash and mixed-quote values altered or refused).
Lint: d39837eb `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean (decision-citation advisories pre-exist).
Live browser evidence: SKIP - maker smoke only; no UI change (writer/reader logic only); checker runs Mode D if it judges the settings page affected.
Metrics: start=2026-10-21T09:00:00Z end=2026-10-21T10:00:00Z wall_min=60 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=unavailable mutants=2 defects_unit=0 defects_6c=0 tests=3 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_env_loading.py tests/test_ui_env_editor.py tests/test_ui_settings.py tests/test_server_settings.py tests/test_container_redaction.py tests/test_image_privacy.py` -> all pass.
- `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean.
