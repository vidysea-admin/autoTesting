# Manifest - at591-media-resolution

**Unit:** Fix AT-591 (`VisionOptions.media_resolution` is an unvalidated bare
str reaching the SDK unchecked -- the same shape AT-370 fixed for
`thinking_level`).
**Contract:** qa/contracts/ingest.md (provider seam), C8 (VisionOptions
carried settings must actually be applied or refused, never silently
dropped/mis-applied).
**Date:** 2026-09-26
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-591

## What changed

1. `src/autotester/schema/observation.py:94-101`
   (`VisionOptions.media_resolution`) -- changed from `str = "high"` to
   `Literal["low", "medium", "high"] = Field(default="high", ...)`. Values
   verified against the **installed** `google-genai` SDK (never memory):
   `.venv/Lib/site-packages/google/genai/types.py:661` --
   `class MediaResolution(_common.CaseInSensitiveEnum)` with members
   `MEDIA_RESOLUTION_UNSPECIFIED, MEDIA_RESOLUTION_LOW,
   MEDIA_RESOLUTION_MEDIUM, MEDIA_RESOLUTION_HIGH`. The three real
   resolutions are exposed lowercase, matching the field's existing
   `.upper()` convention at `providers/gemini.py:100`; the `UNSPECIFIED`
   sentinel is excluded, mirroring how AT-370 excluded `thinking_level`'s
   `UNSPECIFIED`. An invalid value (e.g. `"ultra"`) now raises
   `pydantic.ValidationError` at `VisionOptions(...)` construction time,
   before it can reach `providers/gemini.py`'s
   `f"MEDIA_RESOLUTION_{opts.media_resolution.upper()}"` string build.
2. `src/autotester/providers/gemini.py` -- **no change needed.** Its
   conversion (`gemini.py:100`) is already generic over any valid
   `media_resolution` string; it does not need to know the literal's members.
   Verified this holds by falsifying the conversion in the scratch copy
   (see below) and confirming the existing
   `test_config_applies_media_resolution_for_the_fully_qualified_form` catches
   it -- i.e. that test already guards this file, so leaving it untouched is
   the correct, minimal diff.
3. `tests/test_gemini_config.py` -- added 2 tests, mirroring AT-370's pattern
   exactly: `test_visionoptions_rejects_an_invalid_media_resolution` and
   `test_visionoptions_accepts_every_sdk_media_resolution` (parametrized over
   all 3 valid resolutions).

No real model calls anywhere -- every test exercises `GeminiProvider._config`
directly with a fake `api_key` (never reaches `genai.Client`) or constructs
`VisionOptions` in isolation.

## Callers and defaults checked

Searched all of `src/`, `tests/`, `qa/`, `docs/` for `media_resolution`. Every
site already uses `"high"`, `"low"`, `"medium"`, or leaves the field unset
(default `"high"`):

- `tests/test_gemini_config.py` -- only ever constructs with `"high"` or
  leaves it default.
- `tests/test_schema_video.py:201` -- asserts the default is `"high"`.
- No shipped caller (`stages/ingest.py`, `cli_video.py`, etc.) sets
  `media_resolution` at all (same finding as AT-125 for this field's sibling
  settings) -- narrowing the type invalidates nothing already on disk or in
  a fixture.

## TDD: red-first, done outside the worktree

Per the hard rule ("never edit a tracked worktree file to falsify or
red-test"), red-first and all falsifying edits were done in a throwaway
scratch copy, never in this worktree:

1. Copied `src/`, `tests/`, and `scripts/` (needed for
   `tests/conftest.py`'s `regression_proof` import) verbatim from the
   pre-fix worktree into
   `.../scratchpad/at591-redcheck/{src,tests,scripts}`.
2. Ran the worktree's own venv (`D:\autoTesting\.venv\Scripts\python.exe`)
   against the scratch copy by setting
   `PYTHONPATH=".../at591-redcheck/src;.../at591-redcheck/scripts"` --
   confirmed this actually shadows the real editable install (the venv's
   `autotester.pth` points at `D:\autoTesting\src`) by checking
   `autotester.__file__` resolves to the scratch path first.
3. Added the new tests to the scratch copy's `tests/test_gemini_config.py`
   (pre-fix `observation.py` still had the bare `str`). Ran:

```
$ PYTHONPATH=.../at591-redcheck/src;.../at591-redcheck/scripts \
  python -m pytest tests/test_gemini_config.py -k media_resolution
.F...                                                                    [100%]
FAILED tests/test_gemini_config.py::test_visionoptions_rejects_an_invalid_media_resolution
  Failed: DID NOT RAISE ValidationError
1 failed, 4 passed, 15 deselected in 1.37s
```

RED confirmed on the original pre-fix code, exactly the predicted failure.

4. Applied the fix to the scratch `observation.py`. Re-ran -- all green
   (`20 passed`).
5. Applied the now-verified fix to the actual tracked worktree files (this
   manifest's "What changed" section). Ran the new + existing tests in the
   real worktree -- all green (below).

## Capability coverage (each claim -> its isolating check)

| claim | single-hunk falsifying edit | check that goes red |
|---|---|---|
| media_resolution rejects an invalid value at construction | scratch copy, revert field to `media_resolution: str = "high"` | `test_visionoptions_rejects_an_invalid_media_resolution` -- `Failed: DID NOT RAISE ValidationError` (this is also the red-first run above) |
| default stays `"high"` after narrowing the type | scratch copy, change `default="high"` to `default="medium"` on the fixed field | `test_vision_options_defaults_match_the_proven_pipeline_settings` (`tests/test_schema_video.py:201`) -- `AssertionError: assert 'medium' == 'high'` |
| `gemini.py`'s `MEDIA_RESOLUTION_{...}` conversion still works unchanged for the new `Literal` type | scratch copy, changed `gemini.py:100`'s prefix from `MEDIA_RESOLUTION_` to `WRONG_PREFIX_` | `test_config_applies_media_resolution_for_the_fully_qualified_form` -- `AssertionError: assert <MediaResolut..._PREFIX_HIGH'> == 'MEDIA_RESOLUTION_HIGH'` (SDK also emitted `UserWarning: WRONG_PREFIX_HIGH is not a valid MediaResolution`, confirming the SDK enum itself rejects a bad literal string exactly as AT-591 describes) |
| every real SDK resolution still accepted | n/a -- `test_visionoptions_accepts_every_sdk_media_resolution` is parametrized over all 3 verified `MediaResolution` members (`low`, `medium`, `high`); a falsifying edit narrowing the `Literal` to fewer values fails this parametrized test directly | `test_visionoptions_accepts_every_sdk_media_resolution[low\|medium\|high]` |

All three falsifying edits above were applied and reverted only in the
scratch copy; the tracked worktree files were never touched except by the
final, verified fix.

## How to verify (commands + expected)

```
uv run pytest tests/test_gemini_config.py tests/test_providers.py tests/test_schema_video.py
# 53 passed in 0.91s

uv run ruff check src tests scripts
# All checks passed!

uv run autotester doctor
# doctor: clean
```

Pasted runner output (this run, worktree venv):

```
.....................................................                    [100%]
53 passed in 0.91s

All checks passed!

doctor: clean
```

**LIVE-BROWSER:** not-applicable (no browser interaction in this unit --
schema/provider config only).

## Gaps

- Full suite not run -- RAM is very low per the brief; ran the 3 targeted
  files named in the brief instead (`test_gemini_config.py`,
  `test_providers.py`, the schema tests exercising `VisionOptions` --
  `test_schema_video.py`), 53 tests total, all pass.
- No live/real Gemini API call was made anywhere (per the brief); the SDK's
  own `CaseInSensitiveEnum` behavior (silently accepting an unknown value
  with a `UserWarning`, never raising) was observed directly during the
  falsifying-edit check above, confirming the original AT-591 evidence.

## Commit

`64ebf6d` -- fix(gemini): validate media_resolution against the SDK enum
(AT-591)

Status: checked-PASS (cycle 1, 79c7667)
