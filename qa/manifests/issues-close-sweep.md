# Manifest - issues-close-sweep

Status: checked-PASS
Fix cycle: 0

Changed path: `qa/issues.jsonl` only (15 rows edited in place, no id added or removed). Statuses set to `fixed`, never `verified`.

Scoped tests (no -q): `tests/test_grade_assertion_rule.py test_grade_pii.py test_image_privacy.py test_explore_merge.py test_ui_origin_guard.py test_run_failure_artifacts.py test_redact_pii.py test_browser_close_tolerant.py test_session_survives_failure.py test_ui_video_route.py test_mutation_sandbox.py` -> 349 passed.

| id | evidence | new status |
|---|---|---|
| AT-888 | browser/video.py:111-125,148-199 spare page + one restart; test_session_survives_failure.py, test_ui_runs_target_closed.py | fixed |
| AT-773 | grade.py:96-110 `_assertion_guard`, called at :234; test_grade_assertion_rule.py | fixed |
| AT-840 | text: grade.py:168-172 `_pii_masked`; images: grade_images.py:19 `sanitized_images` (local OCR mask, fail closed); test_grade_pii.py, test_image_privacy.py | fixed |
| AT-887 | explore_merge.py:207-230 `merge_screens_and_flows`; test_explore_merge.py | fixed |
| ISS-t191-run-video-2 | routes_report.py:94-100 `_video_section`; test_ui_video_route.py | fixed |
| AT-820 | scripts/mutation_check.py:154-162 `taskkill /F /T /PID` own child; test_mutation_sandbox.py | fixed |
| AT-736 | session.py:100-132 `_close_quietly` on failed start; run_execution.py:116-119; test_browser_close_tolerant.py | fixed |
| AT-830 | core/redact.py:192 `mask_encoded_emails`; test_redact_pii.py | fixed |
| ISS-d063-grant-budget-2 | ui/app.py:61-68 origin guard; test_ui_origin_guard.py (test coverage is a separate unit) | fixed |
| AT-898 | qa/verdicts/flowplan-writer.md cycle 1 PASS | fixed |
| AT-645 | qa/verdicts/ledger-tick-integrity.md cycle 1 PASS | fixed |
| AT-676 | qa/verdicts/ledger-tick-integrity.md cycle 1 PASS | fixed |
| AT-644 | same verdict; residual: hook callers still to switch to `autotester loop-tick`, needs Approved-by: Umesh (noted on row) | fixed |
| AT-735 | prune_old_videos moved to run_launcher.py:291 but still unguarded and before the O5 ask step; no test | open (note added) |
| AT-787 | wired at run_artifacts.py:58, but no failing_step passed; failure_bundle.py:98-105 still heuristic | open (note added) |

Rows were rewritten by a one-off script (not a CLI helper; none writes status changes). Unchanged lines are byte-identical.
