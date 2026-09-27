# Manifest — at593-crawls-gap-log

**Unit:** `_queue_coverage_gap` (`ui/routes_crawls.py`, the AT-477 branch) captured
`_load_flowspec_safe`'s error and discarded it — a broken `flowspec.json` hit through
`POST /explore` left no server-side trace at all.
**Contract:** `qa/contracts/ui.md` (U5 escaping / no criterion pins this logging path directly —
this is an observability fix, not a behavior change to any U-item) + `browser-and-secrets.md`
(the redaction discipline every log line in this codebase already follows, `core/redact.py`).
**Date:** 2026-09-26
**Fix cycle:** 1 of max 3
**Persona walk:** skip (error-path logging, not a user-facing flow)
**Dual check:** no
**Issues addressed:** AT-593
**Executor:** claude-sonnet-subagent

## What changed

1. `src/autotester/ui/routes_crawls.py`
   - Added `import logging` and a module-level `logger = logging.getLogger(__name__)` — this
     codebase had **no** logging convention anywhere (`grep -rn "^import logging\|getLogger" src`
     returned zero hits before this fix), so none existed to "follow"; this establishes the
     standard `logging.getLogger(__name__)` pattern for the module.
   - `_queue_coverage_gap(store, crawl)` → `_queue_coverage_gap(store, crawl, redactor: Redactor)`.
     When `_load_flowspec_safe` returns a `spec_error`, it is now logged
     (`logger.warning("coverage gap not queued for %s: %s", crawl.id, redactor.scrub(spec_error))`)
     instead of being silently dropped (the old code bound it to `_spec_error` and never touched
     it again). `spec is not None` behavior is byte-identical to before.
   - **Redaction, not just logging.** A broken `flowspec.json` can echo an operator-pasted secret
     back through pydantic's own `input_value=...` in its validation error (proven below, not
     assumed) — CLAUDE.md's hard rule is "logs must pass `Redactor.scrub`," so the message is
     scrubbed before it reaches the logger. `redactor` is threaded in from the caller rather than
     rebuilt here: `start_crawl` (the one call site) already builds `secrets =
     SecretStore.load(project, paths.env_file, strict=False)` for the crawl itself, so
     `_queue_coverage_gap(store, crawl, secrets.redactor())` reuses that exact instance — no second
     `.env` read, matching this codebase's "one loader" precedent (`ui/error_pages.py::_repo_redactor`
     reuses `SecretStore.load(...).redactor()` for the same reason, AT-596 cycle 1).
   - `from autotester.ui.helpers import (...)` (3-name multi-line import) collapsed to one line —
     needed to stay under `autotester doctor`'s 300-line file cap after the above additions (this
     file was at 296/300 before this unit); this is an import-statement reflow, not a docstring or
     comment, so it is outside the "never trim pre-existing docstrings/comments" rule. File is
     298/300 lines after.
   - No pre-existing docstring or comment was shortened or reflowed; the only docstring change is
     one wholly new sentence appended to `_queue_coverage_gap`'s docstring (AT-593 note).
2. `tests/test_ui_crawl_approval.py` — added
   `test_explore_logs_a_redacted_flowspec_read_failure` (see "Capability coverage").

`_coverage_card` (the other `_load_flowspec_safe` caller, used by `GET .../crawls/{id}`) is
untouched — its `spec_error` already reaches the operator via the rendered card (AT-477), which is
exactly what the issue's own evidence says ("the user sees the error only on the redirect target's
own card"); AT-593 is specifically about the **server-side** trace `_queue_coverage_gap` discarded,
which no other code path supplied.

## How to verify (commands + expected)

```
uv run pytest tests/test_ui_crawl_approval.py tests/test_ui_crawls.py
# 23 passed

uv run ruff check src tests scripts
# All checks passed!

uv run autotester doctor
# doctor: clean
```

## Actual outputs (this run, worktree venv)

```
$ uv run pytest tests/test_ui_crawl_approval.py tests/test_ui_crawls.py
.......................                                                  [100%]
23 passed, 1 warning in 1.99s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

(One retry along the way: doctor first reported `file-too-long: routes_crawls.py — 302 lines > 300`
after the initial fix; resolved by collapsing the `ui.helpers` multi-line import per "What changed,"
never by touching a docstring or comment. Re-ran clean, above.)

**Also confirmed:** an earlier attempt in this session edited the WRONG checkout — the primary
`D:/autoTesting` working directory instead of this worktree — before any commit. Caught via
`git -C <worktree> status` showing "nothing to commit" when it should not have. Diff was captured
with `git diff`, the main checkout's two files were reverted with `git checkout --`, and the exact
diff was reapplied to this worktree with `git apply`, confirmed identical
(`git diff --stat` in the worktree matched the intended 2-file, +52/-10 change) before continuing.
The main `D:/autoTesting` checkout was left exactly as it was found (its own pre-existing dirty
state from unrelated concurrent work untouched).

## Capability coverage (each claim → its isolating falsification)

Per the hard rule, every falsifying edit below was made in a throwaway copy of `src`/`tests`
OUTSIDE this worktree (`.../scratchpad/at593-redcheck`), run against the worktree's own
already-synced venv via `PYTHONPATH` pointed at the scratch copy (confirmed shadowing:
`python -c "import autotester; print(autotester.__file__)"` resolved to the scratch path before
each falsification, never `git stash`, never an edit to a tracked file). The tracked worktree file
was diffed byte-identical to the scratch copy before and after every falsification round.

| claim | falsifying edit (single hunk, scratch copy only) | check | observed |
|---|---|---|---|
| a `flowspec.json` read failure is now logged (used to vanish) | `_queue_coverage_gap`: revert to the pre-fix body — drop the `if spec_error is not None: logger.warning(...)` block entirely, back to `spec, _spec_error = _load_flowspec_safe(store)` | `test_explore_logs_a_redacted_flowspec_read_failure` | PASS before. FAIL after: `AssertionError: assert 'coverage gap not queued' in ''` — `caplog.text` came back empty, exactly reproducing the original AT-593 gap |
| the logged line is scrubbed, not the raw pydantic message | keep the `logger.warning(...)` call but drop `redactor.scrub(...)`, logging `spec_error` raw | same test | PASS before. FAIL after: `AssertionError: assert 'hunter2' not in '...'` — captured log line reads `...ValueError: ...flowspec.json: 1 validation error for FlowSpec\nscreens\n  Input should be a valid array [type=list_type, input_value='hunter2', input_type=str]...` — the raw secret value `hunter2` is present verbatim in the un-redacted message, confirming pydantic's `input_value=...` echo is a real leak vector for this exact failure mode, not a theoretical one |
| the route's own behaviour (redirect, crawl persisted) is unchanged from AT-477 | not independently falsified this unit — already pinned by the pre-existing `test_explore_survives_an_invalid_flowspec_after_the_crawl_finished`, re-run green in every round above (23/23, including this one) | `test_explore_survives_an_invalid_flowspec_after_the_crawl_finished` | PASS throughout (unaffected by either falsification, since it asserts on `response.status_code`/`store.load_crawl`, not the log) |

Both falsifying edits were reverted; the scratch copy was re-run green (`7 passed` in
`tests/test_ui_crawl_approval.py`) and diffed byte-identical to the tracked worktree file
(`diff -q` produced no output) before this manifest was written. Scratch directory deleted after.

## Live browser evidence

**SKIP.** Reasons:
- This is a pure server-side logging change — zero HTML/rendering touched. `_coverage_card`, every
  `theme.card`/`theme.page` call, and the redirect target's markup are byte-identical to before;
  there is nothing new for a browser to *see*.
- The trigger condition (`_queue_coverage_gap` runs only after a real crawl finishes) requires a
  genuine `BrowserSession`/Playwright run against a real target site — heavier setup than this
  low-severity observability fix warrants, and every existing test (including the new one) already
  exercises the identical code path end-to-end via `TestClient`, mocking only the Playwright
  boundary itself (`BrowserSession`, `explore.run_crawl`) exactly as the pre-existing AT-477 test
  already did.
- RAM checked before deciding: 3.5–3.65GB free of 23.71GB total (`Get-CimInstance
  Win32_OperatingSystem`) — above the 2GB floor, but thin enough (concurrent maker/checker activity
  per the session's own git log) that spending it on a browser launch with no visible surface to
  verify was judged the wrong tradeoff.
- Flagged as a gap for the checker's Mode D below rather than silently skipped.

## Gaps

- Full test suite not run (RAM discipline per the brief) — ran the two directly-relevant files
  (`test_ui_crawl_approval.py`, `test_ui_crawls.py`, 23 tests, all pass) instead of the full suite.
- No live/interactive browser run (see "Live browser evidence" above) — if the checker's Mode D run
  has headroom, driving a real crawl through `POST /explore` against a scratch project with a
  corrupted `flowspec.json` and confirming a warning line lands in the server's stdout/log would
  close this gap; no UI regression is expected or claimed either way.
- No new `qa/contracts/` criterion added or changed (out of scope per the brief; this is an
  observability fix, not a new behavior for any U-item to pin).

## Status: checked-PASS (cycle 1, qa/verdicts/at593-crawls-gap-log.md 119fd0a)
