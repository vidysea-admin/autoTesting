# Verdict — at593-crawls-gap-log

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checked commit:** 94b180f (code), 6878d76 (manifest)
**Checker:** /checker session (claude-opus) + a fresh claude-sonnet subagent (Mode A + Mode D, own headed browser)

```
VERDICT: PASS
SCOREBOARD: 4/4 unit claims met (gap logged, scrubbed, redactor from the one loader, import collapse lossless)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced in own copies (1 passed before each). Row 1 (drop the log block) fails `assert 'coverage gap not queued' in ''`. Row 2 (log spec_error unscrubbed) fails `assert 'hunter2' not in ...`, because pydantic echoes input_value=, which makes the scrub load-bearing.
LIVE-BROWSER: qa/evidence/browser-at593-crawls-gap-log-2026-09-26-checker/ (on master, 6b106e7)
ISSUES-WRITTEN: AT-608 (pre-existing sibling leak, found during this check; not charged to this unit)
EXECUTOR: maker builder (checker: claude-opus session + claude-sonnet subagent)
EXPLANATION: `_queue_coverage_gap` now logs a broken FlowSpec read as `redactor.scrub(spec_error)`, using the project's real SecretStore redactor threaded from start_crawl. Mode D ran a genuine unmocked crawl through the UI, and the server's stderr carried the line as `input_value='[REDACTED]:DEMO_PASSWORD'` with no raw value. The same live page exposed a different, pre-existing leak in `_coverage_card`, which this unit did not touch; it is filed as AT-608.
```

## What I re-ran

- `uv run pytest` (full, no -q): **1851 passed, 6 skipped, 32 xfailed, 0 failed** in 703 s, exit 0. Ruff: All checks passed. Doctor: clean.
- Targeted (subagent): tests/test_ui_crawl_approval.py + tests/test_ui_crawls.py -> 23 passed.

## Diff scope (4c)

Merge-base fc3e07f. Only src/autotester/ui/routes_crawls.py (+ `import logging`, logger, the scrubbed warning, redactor param) and tests/test_ui_crawl_approval.py changed, both listed in "What changed". The only removed lines are the 3-line `ui.helpers` import, collapsed to 1 line with all three names kept (`_load_project_or_404`, `_require_safe_id`, `_reserved_temp_path`). File is 298/300.

## Logging review

- No handler or basicConfig exists anywhere in src. The WARNING reaches stderr via `logging.lastResort` (bare `%(message)s`), shown live under uvicorn.
- The only other argument is `crawl.id`, and there is no `exc_info`.
- This meets the CLAUDE.md rule "logs pass `Redactor.scrub`".
- Note (not charged): with no handler configured, the line carries no level or logger prefix. Worth revisiting if structured logs arrive.

## Mode D (headed Chromium, worktree app on 127.0.0.1:8095, scratch root, local static target on 8096)

- Granted a crawl approval through the real form, then POSTed `/projects/demo/explore`. A real BrowserSession crawl reached `_queue_coverage_gap` with a deliberately broken flowspec.json containing the fake secret -> 303 to the crawl page. 0 console errors or warnings.
- Server stderr: `coverage gap not queued for crawl_...: ... input_value='[REDACTED]:DEMO_PASSWORD'`, with no raw value anywhere.
- Main checkout: no src/tests modifications (the builder's earlier accidental edit to main was reverted cleanly).
