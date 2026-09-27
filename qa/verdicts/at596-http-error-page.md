# Verdict — at596-http-error-page

**Date:** 2026-09-26
**Cycle checked:** 1
**Checked commit:** 6b52c12 (code), manifest 6c7f741
**Checker:** /checker session (claude-opus), Mode D by a fresh claude-sonnet subagent driving its own browser

```
VERDICT: FAIL
SCOREBOARD: 5/6 unit claims met (U5 escaping holds; C5 one-loader holds), 1 regression introduced
FAILURES:
- [claim: "status codes unchanged" / HTTP semantics] sev: medium · a browser-negotiated 405 now ships with NO `Allow` header; JSON callers still get `allow: POST`, and before this unit browsers got it too (FastAPI's default handler forwards `exc.headers`) · `_error_page` (error_pages.py:84-95) builds `HTMLResponse(..., status_code=status_code)` without `headers=exc.headers` -- thread `exc.headers` through (every header-carrying HTTPException: 405 Allow, 401 WWW-Authenticate, custom ones) and add a test that an HTML-accept 405 keeps `Allow` · issue: AT-605
CAPABILITY-COVERAGE: 6/6 distinct rows reproduced (row 7 = same edit as row 4); one-loader claim verified by citation
LIVE-BROWSER: qa/evidence/browser-at596-http-error-page-2026-09-26-checker/ (on master)
ISSUES-WRITTEN: AT-605
EXECUTOR: maker builder (checker: claude-opus session + claude-sonnet Mode D subagent)
EXPLANATION: Everything the unit claims works, live in a real browser, including the two pre-check fixes (Starlette's unmatched-route 404 and approve-on-unknown-slug). The one failure is a regression the unit itself introduced: the HTML branch rebuilds the response and drops the exception's headers, so a browser's 405 violates RFC 9110 §15.5.6 ("MUST generate an Allow header field"). It's a one-argument fix plus one test.
```

## What I re-ran

- `uv run pytest` (full suite, no -q) in the worktree: 1 failed, 1774 passed, 6 skipped, 32 xfailed in 1165 s. The one failure is `tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild` (a nested pytest hit a collection error). It is pre-existing and already tracked (ISS-t164-1, AT-518), and this unit touches no file on its path.
- `uv run ruff check src tests scripts` + `uv run autotester doctor`: ruff: All checks passed. doctor: 1 violation, `ledger-row-lost` for AT-605, only because the branch's ledger predates the row filed on master (f9d9e7b); it clears on merge.

## Capability coverage — reproduced by the checker in its own copies

Each row ran in its own copy (`<scratch>/at596-row<k>`: src, tests, scripts and pyproject, with the worktree venv and
`PYTHONPATH=<copy>/src;<copy>/scripts`). **Every copy was 12/12 green before its edit.**

| row | single-hunk edit in error_pages.py | red after (named tests) |
|---|---|---|
| 1 browser gets themed page | L74 `_wants_html` -> `return False` | 7 failed: all 5 HTML-accept tests + unmatched-route HTML + approve-unknown-slug |
| 2 JSON caller unchanged | L74 -> `return True` | 5 failed: all 4 JSON/no-Accept tests + unmatched-route JSON |
| 3 detail escaped | L89 drop `escape(...)` | 1 failed: `test_html_error_page_escapes_the_detail` |
| 4 secret redacted (also the 6b52c12 row) | L89 -> `escape(detail)` | 1 failed: `test_html_error_page_redacts_a_known_secret_from_the_repo_env` (raw `sk-supersecretvalue123` on page) |
| 5 status code kept | L95 `status_code=200` | 7 failed (every HTML-path test) |
| 6 Starlette base class | L34 -> `from fastapi import HTTPException` | 1 failed: `test_unmatched_route_with_html_accept_renders_a_themed_page` |

**One-loader claim (C5):** verified by citation, as the manifest says a test cannot tell the difference.
`error_pages.py:67` calls `SecretStore.load(...)` (browser/secrets.py:117) and then `.redactor()`
(browser/secrets.py:223). `parse_env` appears only in the docstring (line 52). A missing `.env` is safe: secrets.py:125
reads `""`.

## Diff scope (4c)

`git diff f5dc842..6b52c12 --stat`: docs/MAP.md +1, app.py +2, error_pages.py (new), tests/test_ui_error_pages.py
(new), and the manifest. The diff only adds code: **no pre-existing line removed**, and every file is listed in
"What changed".

## Mode D (own browser, headless=False, port 8071, scratch root)

| # | scenario | result |
|---|---|---|
| A | delete a pinned case (409) | themed "409 Conflict" card; "Back to projects" -> `/` 200 |
| B | `/projects/does-not-exist` | themed 404 |
| C | `/this/route/does/not/exist` (Starlette's own 404) | themed 404 (new in 6b52c12, confirmed live) |
| D | real browser form POST to `/projects/no-such-slug/flowspec/approve` | themed 404 (AT-259 path, confirmed live) |
| E | onboard with a blank name | themed 400 "a project needs a name" |
| F | unvalidated echo `routes_credentials.py:196` (`key` form field) with `<img src=x onerror=alert(1)>` and with the seeded fake secret value | tag shown as escaped text with no dialog; secret absent, `REDACTED` present |
| G | GET on a POST-only route (405) | themed page renders, **but `Allow` is missing** (see FAIL) |
| H | curl JSON / no-Accept against B, C and D | `{"detail": ...}` and status codes unchanged |

Console: each non-2xx page logs exactly 1 Chromium network line ("Failed to load resource: ... status of NNN") for
the document itself. There were no page-script errors, so this is expected.

**405 reproduced by the checker independently** (TestClient against the worktree, read-only):
`application/json -> 405 application/json allow= POST`; `text/html,... -> 405 text/html allow= None`.

## Contract note

The builder asked whether this handler needs a new U-criterion. **No new criterion yet.** U5 already covers the
escaping, and the header gap is tracked as AT-605. If cycle 2 lands the header fix with a test, the behaviour is
pinned by tests and no contract change is needed.

---

# Verdict — at596-http-error-page, cycle 2

**Date:** 2026-09-26 · **Cycle checked:** 2 · **Checked commit:** fef6c3b (code), manifest 8755b99 · **Checker:** /checker session (claude-opus), own browser

```
VERDICT: PASS
SCOREBOARD: 6/6 unit claims met; the cycle-1 regression (AT-605, missing Allow on HTML 405) is closed
FAILURES: none
CAPABILITY-COVERAGE: 2/2 cycle-2 rows reproduced (own copies, 15/15 green before each edit)
LIVE-BROWSER: qa/evidence/browser-at596-http-error-page-2026-09-26-checker-c2/ (on master)
ISSUES-WRITTEN: none
EXECUTOR: maker builder (checker: claude-opus session)
EXPLANATION: `_error_page` now takes `headers` and the handler threads `exc.headers` through, so an HTML-negotiated 405 keeps `Allow: POST` and a 401 keeps `WWW-Authenticate`. JSON callers are unchanged. Each half of the fix is isolated by its own red test, and the live browser confirms the header on the themed page.
```

## What I re-ran

- `uv run pytest` (full suite, no -q) in the worktree: **1779 passed, 5 skipped, 32 xfailed, 0 failed** in 708.93 s, exit 0. The known flake AT-518 did not fire this run.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 2 violations, both `ledger-row-lost` for AT-605 (manifest and verdict name it). The row was filed on master (f9d9e7b) after this branch forked, so it clears on merge. This is the same pattern as cycle 1, not a unit defect.

## Capability coverage (checker's own copies)

| row | single-hunk edit | red after |
|---|---|---|
| 1 response carries headers | error_pages.py `HTMLResponse(..., headers=headers)` -> drop `headers=headers` | HTML-405 Allow test + 401 WWW-Authenticate test fail; the JSON-405 test stays green |
| 2 handler forwards them | handler `_error_page(exc.status_code, detail, exc.headers)` -> drop `exc.headers` | the same two tests fail; JSON stays green |

Both copies were 15/15 green before the edit (tests/test_ui_error_pages.py + tests/test_ui_error_page_headers.py).

## Diff scope (4c)

`6b52c12..fef6c3b` touches error_pages.py (signature + one call), the new tests/test_ui_error_page_headers.py (3 tests), a 4-line docstring note in tests/test_ui_error_pages.py, and the manifest. **No existing function, test or route removed.** Every file is listed in "What changed".

## Mode D (own browser, port 8093, scratch root)

- HTML GET on a POST-only route: 405, `text/html`, header `allow: POST`, themed h2 "405 Method Not Allowed" (405.png).
- Unmatched route: themed 404 (404-unmatched.png). The Back link lands on `/` with 200.
- JSON Accept on the same 405: `allow: POST`, `{"detail":"Method Not Allowed"}`.
- Console: only Chromium's own "Failed to load resource ... NNN" line per non-2xx document; no page-script errors.
- First attempt hit port 8072, which belongs to another project's mock server. It was discarded and re-run on 8093, and those screenshots replaced the bad ones.

AT-596 and AT-605 flip to fixed only after the merge is verified on master (`git merge-base --is-ancestor`).
