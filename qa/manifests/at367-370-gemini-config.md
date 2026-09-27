# Manifest - at367-370-gemini-config

**Unit:** Fix AT-367 (temperature silently discarded on every gemini-3.x
model, including DEFAULT_MODEL) and AT-370 (VisionOptions.thinking_level is
an unvalidated bare str reaching the SDK unchecked).
**Contract:** qa/contracts/ingest.md (provider seam), C8 (VisionOptions
carried settings must actually be applied or refused, never silently
dropped).
**Date:** 2026-09-25
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-367, AT-370

## What changed

1. `src/autotester/providers/gemini.py:98-109` (`GeminiProvider._config`) --
   the `elif opts.temperature is not None:` that gated temperature behind
   "model is NOT gemini-3.x" (making it unreachable for `DEFAULT_MODEL =
   "gemini-3.6-flash"` and every other 3.x model) is now an unconditional
   `if opts.temperature is not None:` applied after the gemini-3 branch.
   Verified against the installed `google-genai` SDK
   (`types.GenerateContentConfig.model_fields`) that `temperature` is an
   independent field with no declared conflict with `thinking_config` --
   AT-367's "honour it, or fail loudly" is resolved as **honour it**.
   Docstring (`gemini.py:76-83`) updated to state temperature is applied for
   every model, not just pre-3.x ones.
2. `src/autotester/schema/observation.py:95-97`
   (`VisionOptions.thinking_level`) -- changed from `str = "high"` to
   `Literal["minimal", "low", "medium", "high"] = Field(default="high", ...)`.
   Values verified against the installed SDK's
   `google.genai.types.ThinkingLevel.__members__`:
   `THINKING_LEVEL_UNSPECIFIED, MINIMAL, LOW, MEDIUM, HIGH` -- the four
   real levels are exposed (lowercase, matching the field's existing
   `.upper()` convention at `gemini.py:103` and `media_resolution`'s sibling
   convention); the `UNSPECIFIED` sentinel is excluded since it is not a
   value a caller should ever explicitly choose. An invalid value now raises
   `pydantic.ValidationError` at `VisionOptions(...)` construction time,
   before it can reach `types.ThinkingConfig`.
3. `tests/test_gemini_config.py` -- added 6 tests:
   `test_config_honours_temperature_on_the_default_gemini_3_model`,
   `test_config_honours_temperature_alongside_thinking_config`,
   `test_config_omits_temperature_when_caller_does_not_set_it` (no-regression),
   `test_visionoptions_rejects_an_invalid_thinking_level`,
   `test_visionoptions_accepts_every_sdk_thinking_level` (parametrized over
   all 4 valid levels).

No real model calls anywhere -- every test exercises `GeminiProvider._config`
directly with a fake `api_key` (never reaches `genai.Client`) or constructs
`VisionOptions` in isolation.

## TDD: red-first, done outside the worktree

Per the hard rule ("never edit a tracked worktree file to falsify or
red-test"), red-first was proven in scratch, never in this worktree:

1. Copied the pre-fix `gemini.py` / `observation.py` verbatim from `git show
   HEAD:...` into a scratch dir
   (`.../scratchpad/at367-370-redcheck/{gemini,observation}_original.py`).
2. A standalone harness (`redcheck.py`) registered bare namespace-package
   stubs for `autotester`/`autotester.schema`/`autotester.providers` (so
   unrelated submodules -- `schema.base`, `schema.enums`,
   `providers.base`, `providers.gemini_files`, `providers.gemini_schema` --
   still import normally from the real tree) and loaded ONLY the two scratch
   copies under test. Ran against the untouched worktree venv:

```
$ uv run python .../scratchpad/at367-370-redcheck/redcheck.py
[RED as expected] AT-367 temperature honoured on gemini-3 model: temperature was silently dropped: config.temperature=None
[RED as expected] AT-370 VisionOptions rejects invalid thinking_level: VisionOptions(thinking_level='banana') should have raised a ValidationError but constructed fine: 'banana'

All checks confirmed RED on the original pre-fix code, as expected.
```

3. Applied the fix to the actual tracked worktree files (this manifest's
   "What changed" section). Ran the new + existing tests -- all green (below).

## How to verify (commands + expected)

```
uv run pytest tests/test_gemini_config.py tests/test_gemini_schema.py tests/test_schema_video.py tests/test_ingest_persist.py tests/test_ingest_real_cli.py tests/test_providers.py -v
# collected 92 items ... 92 passed in 6.79s

uv run ruff check src tests scripts
# All checks passed!

uv run autotester doctor
# doctor: clean
```

Pasted runner output (this run):

```
tests\test_gemini_config.py ................                             [ 17%]
tests\test_gemini_schema.py .............                                [ 31%]
tests\test_schema_video.py .........................                     [ 58%]
tests\test_ingest_persist.py ..............                              [ 73%]
tests\test_ingest_real_cli.py ................                           [ 91%]
tests\test_providers.py ........                                         [100%]
============================= 92 passed in 6.79s ==============================

All checks passed!
doctor: clean
```

## Capability coverage (each claim -> its isolating check)

| claim | single-hunk falsifying edit | check that goes red |
|---|---|---|
| AT-367: temperature is honoured for a gemini-3 model (incl. DEFAULT_MODEL) | in a scratch copy of the FIXED `gemini.py`, re-add `elif opts.temperature is not None:` in place of the unconditional `if` (`gemini.py:105-109`) | `test_config_honours_temperature_on_the_default_gemini_3_model` / `test_config_honours_temperature_alongside_thinking_config` -- reproduced standalone via `capability_check.py` row 1: `config.temperature=None` instead of `0.4` |
| AT-367: temperature still omitted when unset (no regression) | n/a -- covered by the existing "does not set thinking_config for an older model"-style assertions plus `test_config_omits_temperature_when_caller_does_not_set_it`; falsifying edit would be forcing `kwargs["temperature"] = opts.temperature` unconditionally, which the pre-existing `test_config_falls_back_to_temperature_for_an_older_model` combined with the new omission test together bound | `test_config_omits_temperature_when_caller_does_not_set_it` |
| AT-370: `thinking_level` rejects an invalid value at construction | in a scratch copy of the FIXED `observation.py`, revert the field to `thinking_level: str = "high"` (`observation.py:95-97`) | `test_visionoptions_rejects_an_invalid_thinking_level` -- reproduced standalone via `capability_check.py` row 2: construction succeeds instead of raising `ValidationError` |
| AT-370: every real SDK level is still accepted | n/a -- `test_visionoptions_accepts_every_sdk_thinking_level` is parametrized over all 4 verified `ThinkingLevel` members (`minimal`, `low`, `medium`, `high`); a falsifying edit narrowing the `Literal` to fewer values would fail this parametrized test directly | `test_visionoptions_accepts_every_sdk_thinking_level[minimal\|low\|medium\|high]` |

Falsification evidence (scratch-only, `capability_check.py`):

```
[RED as expected] AT-367 falsifying edit (re-added elif) makes temperature test go red: temperature was silently dropped by the falsified `elif`: config.temperature=None
[RED as expected] AT-370 falsifying edit (bare str) makes ValidationError test go red: VisionOptions(thinking_level='banana') should have raised but constructed fine on the falsified bare-str field: 'banana'

Both capability rows confirmed: falsifying edit -> check goes red.
```

**LIVE-BROWSER:** not-applicable (no browser interaction in this unit --
provider config only).

## Gaps

- Full suite not run (free RAM measured ~2.3 GB, below the 3.5 GB threshold)
  -- ran the 6 test files that actually reference `VisionOptions` or
  `GeminiProvider` (92 tests, all pass) instead. A stale, unrelated test file
  elsewhere in the suite is a theoretical residual gap the checker may want
  to close with a full run when RAM allows.
- `media_resolution` (`observation.py:94`) is the same "bare str reaching an
  SDK enum" shape as `thinking_level` was, but AT-370 only names
  `thinking_level` and this unit's brief scoped the fix to AT-367/AT-370
  only -- left as-is, not filed as a new issue (checker's call whether it
  warrants one).

## Commit

`7b42a60` -- fix(gemini): honour temperature on 3.x models, validate
thinking_level (AT-367, AT-370)

Status: checked-PASS (cycle 1, 3be547b)
