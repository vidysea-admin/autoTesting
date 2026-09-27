# Verdict — at608-609-scrub-leftovers

**Date:** 2026-09-26
**Cycle checked:** 1
**Checker:** /checker (standing checker session, orchestrator + fresh subagents for the parallel legs)
**Contract:** qa/contracts/core-invariants.md C5, C2; qa/contracts/ui.md; qa/contracts/report-export.md RE5
**Branch / code commit:** wave/at608-609-scrub-leftovers · 023ffd5 (manifest 7f68ebc), base c8d078d

```
VERDICT: PASS
SCOREBOARD: 3/3 criteria met (C5 crawl-page read-error scrub, RE5 Excel Case title scrub, RE5 HTML h2 + figcaption scrub), 3/3 invariants hold (C2 line cap, C3 one-concept-one-place, C5 single redaction mechanism)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 manifest rows reproduced + 2 extra checker rows (h2-only, figcaption-only) both killed
LIVE-BROWSER: qa/evidence/browser-at608-609-scrub-leftovers-2026-09-26-checker/ (headed Chromium, port 8097)
ISSUES-WRITTEN: none (AT-608, AT-609 flip to fixed only after the merge is verified on master)
EXECUTOR: claude-opus-subagent (checker: claude-opus orchestrator + sonnet subagents)
EXPLANATION: Both leak sites now go through the existing Redactor path (no second mechanism). The full suite, ruff and doctor are green on the branch tip, and every falsifying edit reddens exactly the named assertion. The _bounds_form -> crawl_view.bounds_form move is disclosed, forced by C2 (routes_crawls hit 305 lines), byte-identical in body, and leaves no stale caller.
```

## What the checker re-ran itself

- Full suite on the worktree tip, serial (RAM): `uv run pytest` -> `1860 passed, 5 skipped, 32 xfailed, 15 warnings in 759.31s (0:12:39)` EXIT 0; `uv run ruff check src tests scripts` -> `All checks passed!`; `uv run autotester doctor` -> `doctor: clean`.
- Targeted files: `tests/test_ui_crawl_approval.py tests/test_report_export_secrets.py` -> 15 passed.

## Capability rows (own throwaway copies at `<scratch>/at608-row<k>`, worktree venv, `-o addopts= -p no:cacheprovider`)

| Row | Edit (single hunk) | GREEN in the copy before | RED after (named assertion) |
|---|---|---|---|
| 1 | routes_crawls.py:105 `escape(redactor.scrub(spec_error))` -> `escape(spec_error)` | `1 passed` | `AssertionError: assert 'hunter2' not in '<!doctype h.../main></div>'` |
| 2 | report_export.py:142 `redactor.scrub(case.title)` -> `case.title` | `1 passed` | `assert 'hunter2-super-secret' not in 'Login works...super-secret'` |
| 3 (manifest row 3) | report_export.py:195 + :201 both scrubs reverted | `1 passed` | h2 AND figcaption both show `hunter2-super-secret` |
| 4 (checker extra) | report_export.py:195 only (h2) | `1 passed` | `gin works hunter2-super-secret <span class='badge'...` (figcaption still `[REDACTED]`) |
| 5 (checker extra) | report_export.py:201 only (figcaption) | `1 passed` | `<figcaption>before hunter2-super-secret</figcaption>` |

Rows 4 and 5 prove the one HTML test isolates each of the two fields independently. The manifest row 3 reverts both, and on its own that would not prove this.

## Diff scope (4c)

`git diff --stat c8d078d..023ffd5`: 5 files, +140/-34. These are routes_crawls.py, crawl_view.py, report_export.py and the two test files, exactly the "What changed" list. One removal: `routes_crawls._bounds_form` moved to `crawl_view.bounds_form` (crawl_view.py:196).
- Its body is byte-identical once docstrings are stripped.
- `grep -rn bounds_form src tests scripts` finds only the one definition and the two updated callers (routes_crawls.py:145, :170).
- The move is required by C2: the AT-608 fix took routes_crawls.py to 305 lines. After the move, line counts are routes_crawls 286, crawl_view 233, report_export 281.

Not charged.

## Mode D (own headed browser)

Scratch project "demo" declares DEMO_PASSWORD, and its .env holds a FAKE value (`hunter2`). flowspec.json is deliberately broken and echoes that value.
- GET the crawl page. `hunter2` is absent from both page.content() and inner_text. `[REDACTED]` is present in the "Against the FlowSpec" card. 0 console errors.
- The moved bounds form renders, fills and submits the real POST. It reaches the D-018 consent gate and gets 403 "Crawl approval required", which is expected for an unapproved project. The single console line is the browser logging that 403.

No server or browser process was left running.

## Disclosed, not charged

`scoreboard`, `error`, `reason` and `fix_hint` in exports are still unscrubbed. These are pre-existing and outside this unit's two issue ids. They belong to a separate follow-up if wanted, not to this unit.
