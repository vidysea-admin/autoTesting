# Verdict - issues-close-sweep

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** b8b721fc1c0af02196304cf6a75d98f776f19790
**Base SHA:** 7409a486
**Checker:** independent (Sonnet 5.5), scoped; maker usage ~104k tokens / 1060 s, checker exact tokens not exposed (unknown)

## Diff (independently computed)
- `git diff 7409a486 b8b721fc` touches only qa/issues.jsonl and the manifest. issues.jsonl: 1025 rows before and after, 0 duplicate ids, all lines valid JSON, no id added/removed.
- 13 closed rows changed exactly `status` (open -> fixed), `resolution`, `fixed_date`. AT-735 and AT-787 changed only `checker_note` and stay open. No other row differs. No row uses `verified`.
- AT-644 resolution states the residual: qa/hooks/* and .claude/hooks/* callers still need switching to `autotester loop-tick` (needs Approved-by: Umesh).

## Evidence opened (file:line) and tests
- AT-840: grade.py `_pii_masked` (mask_pii after secret gate) and `judge_images` -> grade_images.py `sanitized_images`; PASS capped at INCONCLUSIVE when images sent (grade.py ~226-240). Matches.
- AT-888: video.py `begin_case_video`/`_open_case_page`/`_restart_session` (one restart, bounded relaunch, session-restart evidence). Matches.
- AT-773: grade.py:96-110 `_assertion_guard`, called in grade(). Matches.
- ISS-d063-grant-budget-2: ui/app.py:61-68 middleware order, helpers.py `_OriginGuard` (403 on cross-site unsafe methods); tests/test_ui_origin_guard.py. Matches the issue's Origin/Host option.
- AT-644/645/676: qa/verdicts/ledger-tick-integrity.md cycle 1 PASS, reviewed SHA fcd2a1eb is an ancestor of the candidate; core/atomic_tick.py append_tick, tests/test_issue_ids.py exist. Current ids unique.
- AT-898: qa/verdicts/flowplan-writer.md cycle 1 PASS, SHA 50bd8756 is an ancestor; stages/flow_plan.py exists.
- Not individually opened: AT-887, AT-820, AT-736, AT-830, ISS-t191-run-video-2 (maker citations only; manifest tests in the same suite).
- pytest (no -q, venv python, PYTHONPATH=worktree src): test_grade_assertion_rule, test_grade_pii, test_image_privacy, test_session_survives_failure, test_ui_runs_target_closed, test_ui_origin_guard, test_explore_merge -> 192 passed, exit 0.
- doctor (`autotester.cli:app doctor`, worktree root) -> exit 0, `doctor: clean`; only advisory D-087 warnings.

## Limits
- Status is `fixed` only, per the sweep rule; test coverage for ISS-d063-grant-budget-2 and the AT-644 hook switch remain separate units.
- Maker's 349-test claim not rerun in full; ruff not run (no source changed).
