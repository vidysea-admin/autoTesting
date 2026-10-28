# Manifest - bundle-hash-redaction

**Status:** checked-PASS
**Fix cycle:** 0
**Issues addressed:** inbox 2026-10-28 (run3, run-01M613NEA9M29N8N7SKBR01FGT): bundle manifest hashes get redacted -> intermittent PartialBundleError on `bundles/fb_585c249bc002`
**Branch:** fix/bundle-hash-redaction (from master e74664f8)

## Criteria
1. A short secret value that occurs inside a computed `sha256` hex does not change that hash in `manifest.json`, and `load_bundle` returns the manifest (no `PartialBundleError`).
2. Every free-text manifest field is still scrubbed and gated: a real secret in `run_id` (a manifest free-text field) is masked as `[REDACTED]:APP_PASSWORD` and absent from `manifest.json`; the bundle still loads.
3. A tampered / wrong `sha256` in the manifest is still refused by `load_bundle` (the hash check is not weakened).
4. Only well-formed 64-hex digests are exempt; a malformed `sha256` string goes through the normal scrub.
5. All other bundle parts (case, verdict, result, error, steps, trace) are dumped exactly as before (`_dump` unchanged).

## Files changed
- `src/autotester/stages/failure_bundle.py`: new `_SHA256_RE` + `_dump_manifest` (lines 84-105); manifest write at line 221 now calls `_dump_manifest` instead of `_dump`. File is 255 lines, function ~17 lines. Edited in place; no new module.
- `tests/test_failure_bundle_hash_redaction.py` (new, 3 tests: criteria 1, 2, 3). Separate file because `tests/test_failure_bundle.py` is at 292/300 lines.

## How it works
`_dump_manifest` model-dumps the manifest, blanks each well-formed `sha256` (`[0-9a-f]{64}`), runs the existing `_dump` (scrub object, serialise, scrub + `assert_clean` text) on the rest, then re-inserts the original digests and re-serialises with the same `indent=2, ensure_ascii=False`.

## Tests run (worktree D:/autoTesting/.claude/worktrees/bundle-hash)
Red first (before the fix), `uv run pytest tests/test_failure_bundle_hash_redaction.py -o addopts=`:
```
src\autotester\stages\failure_bundle.py:227: PartialBundleError
FAILED tests/test_failure_bundle_hash_redaction.py::test_short_secret_inside_a_computed_hash_does_not_break_the_bundle
============= 1 failed, 2 passed, 2 warnings in 94.78s (0:01:34) =============
```
(the other two tests are regression guards for criteria 2 and 3 and pass before and after.)

Green after the fix, `uv run pytest tests/test_failure_bundle_hash_redaction.py tests/test_failure_bundle.py tests/test_failure_bundle_escape.py tests/test_failing_step_bundle.py -o addopts=`:
```
======================= 41 passed, 2 warnings in 12.27s =======================
```
`uv run ruff check src/autotester/stages/failure_bundle.py tests/test_failure_bundle_hash_redaction.py`: `All checks passed!`

## Not run (machine low on memory)
Full `uv run pytest` and `uv run autotester doctor`; checker should run them. Only `stages/failure_bundle.py` changed; its importers are `stages/run_artifacts.py` and `stages/report_export.py` (via `bundle_report_detail`).

## Residual / notes for the checker
- `bundle_id`, `run_id`, `case_id` and `files[].name` in the manifest are still scrubbed like any text (criterion 2 relies on that). A short secret equal to a substring of a content-id such as `fb_<hex>` would still alter `bundle_id` in the manifest; not addressed here (the id is also the directory name, and `load_bundle` does not compare them).
