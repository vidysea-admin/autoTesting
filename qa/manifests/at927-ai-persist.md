# Manifest - at927-ai-persist
**Contract:** qa/contracts/ai-target.md AI6, AI9, AI11, AI14 (T-155); open choices at ai-target.md:205-211 closed by Umesh 2026-10-17 (qa/gates/umesh-decisions-2026-10-17.md: store under projects/<slug>/ai/, report = the Excel workbook only)
**Goal task:** T-155 (feature t155-ai-report); issue AT-927
**Policy-Version:** proportional-verification/2026-10-17.13
**Tier:** M (no store locking or concurrency change; redaction logic is only called, `core/redact.py` is untouched)
**Dual check:** no
**Fix cycle:** 0
**Branch:** wave/at927-ai-persist (base 9aaf1fe5), product commit a62fa404
**Issues addressed:** AT-927

## What changed (no new module under src/)
- `core/paths.py`: `ProjectPaths.ai_dir`, `ai_capture_dir(capture_id)` (via `safe_name`, one safe segment), `ai_report` (`ai/ai-report.xlsx`).
- `stages/ai_capture.py`: `capture_id(cap)` (the former `ai_judge._case_id` content id, moved), `persist_scrubbed(path, model, redactor)` (scrub_obj, revalidate, `assert_clean`, then `store.filestore.write_json`, atomic; a surviving secret raises `CaptureWithheld`, nothing written), `store_capture(paths, cap, redactor)` (refuses a capture of another project).
- `stages/ai_judge.py`: `store_verdict(...)`; `judge_capture(..., paths=None)` persists capture and verdict when `paths` is given; the verdict returned is unchanged. Body moved to `_judge` (judge_capture 14 lines). `_case_id` now calls `capture_id`.
- `stages/ai_report.py`: reads `store.paths.ai_dir`; `export_ai_report(store, out=None, ...)` defaults `out` to `paths.ai_report`. Reading logic untouched.
- `tests/test_ai_persist.py` (new, 11 tests).

## Criteria
- AT-927 / ai-target.md open choice 1: captures and verdicts are written to `projects/<slug>/ai/behavioural/<id>/{capture,verdict}.json`.
- AI9/AI11: the workbook reads the persisted capture and verdict (round trip: judge with `paths` then `export_ai_report` shows PASS, not "CAPTURED, NOT JUDGED").
- AI14 / C5: no secret reaches either stored file, including a secret in a judge reason; an encoded survivor withholds the file.
- Open choice 2: workbook only, no new surface (default path under `ai/`).

## Pre-check and tests
Pre-check[AT-927]: a62fa404 uv run pytest tests/test_ai_persist.py -> 11 passed
Pre-check[AI9]: a62fa404 uv run pytest tests/test_ai_persist.py tests/test_ai_report.py -> passed (part of 794 passed below)
Pre-check[AI14]: a62fa404 uv run pytest tests/test_ai_persist.py -> 11 passed (secret tests included; ruff and doctor also clean on this sha)
Tests[AT-927]: tests/test_ai_persist.py::test_judge_capture_with_paths_persists_the_capture_and_the_verdict, tests/test_ai_persist.py::test_capture_judge_store_report_round_trip — persistence of capture and verdict, then the workbook reading them back.
Tests[AI9]: tests/test_ai_persist.py::test_capture_judge_store_report_round_trip, tests/test_ai_report.py — the stored result lands in the tier sheet; the existing report tests are unchanged and still green.
Tests[AI14]: tests/test_ai_persist.py::test_a_planted_secret_never_reaches_capture_json, tests/test_ai_persist.py::test_a_secret_in_a_judge_reason_never_reaches_verdict_json, tests/test_ai_persist.py::test_an_encoded_secret_withholds_the_capture_and_writes_nothing — no secret in either stored file, and a surviving encoded secret withholds the file.
Related run: test_ai_persist, test_ai_report, test_ai_capture, test_ai_catalog, test_core, test_store, test_safe_names_windows, test_check_no_secrets, test_grade, test_grade_evidence, test_doctor, test_run_id_path_safety -> 794 passed.
`shard_suite.py --affected 9aaf1fe5..HEAD` exits 2 `integration-required` (tests/conftest.py imports `core/paths.py`, a changed module); the full suite is the 6c integration tier, not run in this worktree.

## Falsification (copy outside the worktree, D:/autoTesting/.work/fals-at927, removed after)
Baseline 11 passed. Each mutation went red on its own assertion:
- F1 scrub and assert_clean removed in `persist_scrubbed` -> 3 failed (planted secret x2, encoded-secret withhold).
- F2 `judge_capture` no longer persists -> 3 failed (persist, judge-reason secret, round trip).
- F3 default workbook path changed -> round trip failed.
- F4 non-atomic `write_text` instead of `write_json` -> `test_a_failed_write_leaves_no_partial_file` failed.
- F5 `safe_name` dropped in `ai_capture_dir` -> path-segment test failed.

## Status notes
- Honest limit: nothing outside `stages/ai_*` calls `capture_run`/`judge_capture` yet (no CLI or UI caller exists, none was asked for); this unit makes persistence and the report round trip real, not a new command.
- Incident: a failed `cd` in one of my falsification commands made it run in the main checkout, which left copies of the four src files and older copies of five `scripts/*.py` uncommitted there. Reported to the coordinator; not touched from here.

**Status:** ready-for-check
