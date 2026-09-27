# Manifest — at265-gemini-schema-allowlist
**Contract:** qa/contracts/ingest.md (provider seam), I11
**Goal task:** none
**Date:** 2026-09-25
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-265 (medium, open -> fixed)
**Executor:** maker build subagent (worktree D:/autoTesting/.worktrees/at265-gemini-schema-allowlist, branch wave/at265-gemini-schema-allowlist)
**Executor rationale:** single-file sanitiser fix + new test file; RAM ~0.7 GB free at start, well below the 3.5 GB full-suite ceiling — targeted verification only, declared below

## What changed
- `src/autotester/providers/gemini_schema.py`:
  - `_SDK_SCHEMA_FIELD_ALIASES` (line 40) and `ALLOWED_KEYS` (line 61) replace `DROPPED_KEYS`. `_SDK_SCHEMA_FIELD_ALIASES` is the 22 keyword-position field names `google.genai.types.Schema` defines (its wire aliases), verified against the installed SDK (`google-genai` 2.22.0, no network — `types.Schema.model_fields[name].alias`), explicitly excluding `additionalProperties` (a real SDK field that still 400s at Google, AT-230) and the bare `ref`/`defs` aliases (moot — `$ref`/`$defs` are inlined before this filter runs and never match those spellings). `ALLOWED_KEYS` further excludes `title`/`default` for the same noise-reduction reason AT-230 always has.
  - `_translate` (line 96, new): renames `oneOf` -> `anyOf` and `const` -> a one-element `enum`, only when the target key isn't already present — the two constructs Gemini's dialect has no name for but a close equivalent it does.
  - `_expand_ref` (line 118) and `_collapse_nullable_anyof` (line 138): the `$ref`-inlining branch and the nullable-collapse tail of the old `_resolve` monolith, split out so `_resolve` (line 165) stays under the project's 50-line function ceiling (`autotester doctor` caught this at 65 lines on the first pass and it's now ~24).
  - `_resolve`'s main loop (inside `_resolve`, ~line 180) now does `if key not in ALLOWED_KEYS: continue` instead of `if key in DROPPED_KEYS: continue` — the deny-to-allow flip that is the actual fix. `_collapse_nullable_anyof` generalises the nullable collapse from the old `len(concrete) == 1 and len(options) == 2` (2-member-only) guard to `len(concrete) < len(options)` (any N-member `anyOf` with at least one null branch), fixing the `int | str | None` probe.
- `tests/test_gemini_schema_allowlist.py` (new file, split out once `test_gemini_schema.py` crossed the project's 300-line file ceiling on the first `autotester doctor` pass — same pattern as the existing `test_gemini_config.py` split): 6 new tests covering the 4 probe shapes AT-265 names (`Literal` -> `const`, `tuple` -> `prefixItems`, discriminated union -> `oneOf`/`discriminator`, `int | str | None` -> 3-member `anyOf`) plus a keyword sweep across every hazard shape + `VideoObservation`, plus a test asserting `ALLOWED_KEYS`/`_SDK_SCHEMA_FIELD_ALIASES` still match the installed SDK's actual field set (drift guard for a future `google-genai` upgrade).
- `tests/test_gemini_schema.py`: net zero diff (a block was added then extracted into the new file; final content is byte-identical to before this unit).

## How to verify
- `uv run pytest tests/test_gemini_schema.py tests/test_gemini_schema_allowlist.py tests/test_gemini_config.py` -> all pass
- `uv run ruff check src tests scripts` -> clean
- `uv run autotester doctor` -> clean

## Actual outputs (maker's run, worktree HEAD before this unit's commit: bb4be39)
```
tests\test_gemini_schema.py .............                                [ 48%]
tests\test_gemini_schema_allowlist.py ......                             [ 70%]
tests\test_gemini_config.py ........                                     [100%]
============================= 27 passed in 0.81s ==============================
```
`uv run ruff check src tests scripts` -> `All checks passed!`
`uv run autotester doctor` -> `doctor: clean` (first pass caught `file-too-long: tests/test_gemini_schema.py — 403 lines > 300` and `function-too-long: gemini_schema.py:118 — _resolve is 65 lines > 50`; both fixed by the split/extraction above, then re-run clean)

**Gap, declared:** full suite NOT RUN — free RAM was ~0.7 GB at start (`Get-CimInstance Win32_OperatingSystem`, FreePhysicalMemory ≈ 710 MB), far below the 3.5 GB ceiling for a full-suite run. Ran only the three files this change can affect: the sanitiser's own tests, its new split-out file, and the sibling `test_gemini_config.py` (same module, different seam, confirmed by grep to have no other dependency on `gemini_schema`). `providers/gemini.py` itself was not touched (excluded per instruction — at367-370 owns it in parallel) and its own tests (`test_the_PROVIDER_actually_sends_the_sanitised_schema`, in `test_gemini_schema.py`) are included in the targeted run above and pass unchanged.

## Capability coverage
Falsification run entirely outside the worktree (throwaway copies of the FIXED `gemini_schema.py` in the session scratch dir, own module-level import, no `uv sync` needed since the file only imports `pydantic`/`typing`) — the tracked worktree files were never mutated to produce a red result, per the hard rule. Script: `capability_falsify.py`, scratch dir (session-local, not committed).

| capability | check | falsifying edit | observed |
|---|---|---|---|
| a single-value `Literal` renders as `enum`, not `const` | `test_a_single_value_literal_becomes_enum_not_const` (and the scratch equivalent `claim_const_dropped`) | widen `ALLOWED_KEYS` to wrongly admit `"const"` | baseline (unmodified fixed copy): GREEN. Sabotaged copy: `const` key survives in the rendered schema -> claim check returns `False` (RED) |
| a `tuple[int, str]` drops `prefixItems` rather than leaking it | `test_a_tuple_drops_prefixItems_rather_than_leaking_it` / `claim_prefixItems_dropped` | widen `ALLOWED_KEYS` to wrongly admit `"prefixItems"` | baseline: GREEN. Sabotaged: `prefixItems` key survives -> RED |
| a discriminated union's `oneOf` is translated to `anyOf` (not dropped to nothing) | `test_a_discriminated_union_becomes_anyOf_not_a_dropped_oneOf` / `claim_oneOf_becomes_anyOf` | delete the 2-line `oneOf` branch from `_translate` | baseline: GREEN. Sabotaged: `pet.get("anyOf")` is `None` (the field renders with no type info at all) -> RED |
| an N-member `anyOf` (not just 2-member) with a null branch collapses to `nullable` | `test_a_three_way_union_with_none_collapses_the_null_branch` / `claim_three_way_null_collapses` | restore `_collapse_nullable_anyof`'s body to the old `len(concrete) == 1 and len(options) == 2` guard | baseline: GREEN. Sabotaged: the 3-member `anyOf` for `int \| str \| None` is left untouched, `type: null` branch survives, `nullable` is never set -> RED |
| `additionalProperties` never re-enters the allow-list despite being a real (but 400-ing) SDK field | `test_no_keyword_outside_the_sdk_field_set_ever_survives`, `test_ALLOWED_KEYS_matches_the_installed_SDKs_actual_field_set` / `claim_allowed_keys_no_additionalProperties` | add `"additionalProperties"` into `_SDK_SCHEMA_FIELD_ALIASES`'s literal set | baseline: GREEN (`"additionalProperties" not in ALLOWED_KEYS`). Sabotaged: `"additionalProperties"` present in `ALLOWED_KEYS` -> RED |

All five: baseline (unmodified fixed copy) green, single-hunk sabotage red, confirmed by `capability_falsify.py`'s own assertions (script exits 0 only if every sabotage flipped its claim).

Separately, the pre-fix RED state was confirmed against a throwaway copy of the CURRENT (buggy, deny-list) `gemini_schema.py` before any fix was written (`red_probe.py`, same scratch dir): all four AT-265 probe shapes reproduced exactly as the issue describes (`const`/`prefixItems`/`oneOf` leak through untouched, `discriminator` correctly dropped but `oneOf` incorrectly kept, the 3-member `anyOf`'s null branch survives with `nullable` never set).

## Live browser evidence
LIVE-BROWSER: not-applicable — pure data-transformation unit (`model_json_schema()` dict in, dict out); no browser, no network, no real model call anywhere in this unit's tests or falsification.

## Gaps
- Full test suite not run (RAM ~0.7 GB free, below the 3.5 GB ceiling) — targeted run only, declared above.
- `providers/gemini.py` deliberately untouched (owned in parallel by at367-370); its wiring test (`test_the_PROVIDER_actually_sends_the_sanitised_schema`) still passes unchanged against the new sanitiser output shape.
- No live Gemini API call was made (per instruction) — the fix is verified against the installed SDK's local type introspection (`google.genai.types.Schema.model_fields`) and constructed schema probes, not a real `response_schema` round-trip. `qa/contracts/ingest.md` I13/I15 (pinning the wire + response validation) are unaffected by this unit and were not re-verified here beyond the existing passing test.

## Status: checked-PASS (cycle 1, e14e0af)
