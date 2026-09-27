# Manifest — at477-explore-invalid-flowspec

**Unit:** an invalid `projects/<slug>/flowspec.json` must not turn a route that has already done
real work — a finished, saved crawl (`POST /explore`) or a rendering of one (`GET
/crawls/{crawl_id}`) — into an unhandled 500 that hides that work.
**Contract:** `qa/contracts/explore.md` X11 (artifacts are human-readable) + `qa/contracts/ui.md`
**Goal task:** none (issue-driven)
**Date:** 2026-09-25
**Fix cycle:** 1 of max 3
**Dual check:** no
**Issues addressed:** AT-477 (medium, open -> fixed)

## What changed

- `src/autotester/ui/routes_crawls.py:90-97` (new) — `_load_flowspec_safe(store)`: wraps
  `store.load_flowspec()` and turns the `ValueError` a broken `flowspec.json` raises (see
  `src/autotester/store/filestore.py:39-49`, `read_json`) into `(None, "the FlowSpec could not
  be read -- <Type>: <msg>")` instead of propagating it. Same trade-off AT-472 already made for
  the crawl record in `src/autotester/stages/crawl_coverage.py:96-114` (`of_run`), applied here
  to the two UI call sites that were still unguarded.
- `src/autotester/ui/routes_crawls.py:101-107` (new) — `_queue_coverage_gap(store, crawl)`:
  extracted from `start_crawl`'s tail (was inline `store.load_flowspec()` at the old line 251,
  named in AT-477's evidence) so it can call `_load_flowspec_safe` and also keep `start_crawl`
  under doctor's 50-line cap after the fix.
- `src/autotester/ui/routes_crawls.py:110-129` (new) — `_coverage_card(store, safe, safe_id,
  nodes)`: extracted from `crawl_page`'s body (was inline `store.load_flowspec()` at the old
  line 154, the crawl-page half of AT-477) for the same reason; now a three-way branch (spec
  unreadable / spec present / no spec yet) instead of the old two-way `if spec is not None`.
- `src/autotester/ui/routes_crawls.py:204` (was `:251`) — `start_crawl`'s post-crawl coverage
  diff now calls `_queue_coverage_gap(store, crawl)` — this runs **after** the crawl already ran
  and its `Crawl` record was saved (`explore_stage.run_crawl` inside the `try` above), so a
  broken spec here can no longer turn a completed crawl into a 500 that hides it; the route still
  redirects 303 to the crawl page.
- `src/autotester/ui/routes_crawls.py:264` (was `:154`) — `crawl_page` now calls
  `_coverage_card(...)`, which renders `theme.card(<message>, title="Against the FlowSpec")`
  when the spec can't be read, instead of raising before any HTML is returned.
- New imports: `FlowSpec` (`autotester.schema.flowspec`), `ScreenNode`
  (`autotester.schema.screen_graph`), `ProjectStore` (`autotester.store.project_store`) — all for
  the new helpers' type hints.
- `tests/test_ui_crawls.py` — new
  `test_the_crawl_page_states_the_flowspec_could_not_be_read`: seeds a crawl, writes
  `{ this is not a flowspec` straight to `store.paths.flowspec` (bypassing `save_flowspec`'s
  validation), asserts `GET /projects/demo/crawls/crawl_demo` is 200 and the page says the spec
  could not be read.
- `tests/test_ui_crawl_approval.py` — new
  `test_explore_survives_an_invalid_flowspec_after_the_crawl_finished`: same broken
  `flowspec.json`, `BrowserSession`/`explore_consent.require_consent`/`explore.run_crawl`
  monkeypatched to a stub (following the existing
  `test_one_bounds_object_reaches_preflight_and_run` pattern in the same file — no real browser,
  no real target) whose stub `run_crawl` calls `store.save_crawl(...)` itself so the test can
  assert the crawl record survives; asserts `POST /projects/demo/explore` still returns 303 and
  the redirected-to crawl page is 200, not 500.

File sizes after the change: `routes_crawls.py` 296 lines (was 272), `test_ui_crawls.py` 221
lines, `test_ui_crawl_approval.py` 172 lines — all under doctor's 300-line cap; longest new
function (`start_crawl`) is under the 50-line cap (confirmed by `autotester doctor`, below).

## How to verify (commands + expected)

- `uv run pytest tests/test_ui_crawls.py tests/test_ui_crawl_approval.py
  tests/test_ui_crawl_approval_list.py tests/test_crawl_coverage.py tests/test_explore_merge.py
  tests/test_ui_crawl_login.py` -> all pass
- `uv run ruff check src tests scripts` -> clean
- `uv run autotester doctor` -> clean

## Actual outputs (maker's own run)

- Red-first (current code, before the fix), both new tests, exact ValueError at the exact lines
  AT-477 names:
  ```
  src\autotester\ui\routes_crawls.py:251: in start_crawl
      spec = store.load_flowspec()
  ...
  E   ValueError: ...flowspec.json: 1 validation error for FlowSpec
  E     Invalid JSON: key must be a string at line 1 column 3 [type=json_invalid, ...]
  FAILED tests/test_ui_crawls.py::test_the_crawl_page_states_the_flowspec_could_not_be_read
  FAILED tests/test_ui_crawl_approval.py::test_explore_survives_an_invalid_flowspec_after_the_crawl_finished
  2 failed, 1 warning in 5.04s
  ```
- After the fix: `59 passed, 1 warning in 11.72s` (first targeted run), reconfirmed
  `69 passed, 1 warning in 74.42s` including the login/approval-list files.
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean`
- Full non-browser suite: **NOT RUN** — free RAM measured 1.72 GB
  (`Get-CimInstance Win32_OperatingSystem`: `FreePhysicalMemory` 1,763,356 KB of 24,866,680 KB
  total), below the 3.5 GB ceiling. Declared gap, not run.

## Capability coverage

| capability | check | falsifying edit | observed |
|---|---|---|---|
| `GET /projects/{slug}/crawls/{crawl_id}` renders 200 with a stated read failure instead of 500 when `flowspec.json` is invalid | `tests/test_ui_crawls.py::test_the_crawl_page_states_the_flowspec_could_not_be_read` | in `_coverage_card`, replace `spec, spec_error = _load_flowspec_safe(store)` with `spec, spec_error = store.load_flowspec(), None` (the unguarded call AT-477 originally hit) | throwaway copy outside the worktree (`scratchpad/at477-falsify`, reusing the worktree's own `.venv` interpreter via `PYTHONPATH`, never git). Before: `2 passed in 2.77s`. After: `ValueError: ...flowspec.json: ... Invalid JSON ...` / `1 failed in 3.37s` — the exact AT-477 500 returns. Reverted; copy is byte-identical to the worktree again (`diff` confirmed) and both tests pass. |
| `POST /projects/{slug}/explore` still redirects 303 (and the already-saved crawl survives) instead of 500 when `flowspec.json` is invalid | `tests/test_ui_crawl_approval.py::test_explore_survives_an_invalid_flowspec_after_the_crawl_finished` | in `_queue_coverage_gap`, replace `spec, _spec_error = _load_flowspec_safe(store)` with `spec, _spec_error = store.load_flowspec(), None` | same throwaway copy. Before: `2 passed in 2.77s` (both tests run together). After (this test alone): `ValueError: ...flowspec.json: ... Invalid JSON ...` / `1 failed in 4.61s`. Reverted; re-confirmed both green. |

## Live browser evidence

**This unit changes what the crawl page and the explore route render/return (X16/X18 surfaces),
so it needs a Mode D pass. Not run by the maker this cycle** — no browser tool was available in
this session (Playwright MCP connection timed out), and the task brief for this unit scoped
execution to `TestClient` with the crawl stubbed, no real browser, no real target.

**Correction for the checker:** the brief's suggested `uv run autotester ui` does not exist —
`uv run autotester --help` lists no `ui` command (checked this cycle; full list: `doctor
providers map snapshot expand login loop-status explore approve orchestrate ledger flowspec
report ingest issues`). The UI is actually launched with
`uv run uvicorn autotester.ui.app:app --host 127.0.0.1 --port 8069` (verified against
`docker/entrypoint.sh`'s own launch line, same module/app object, `--port 8000` there for the
container).

**Suggested reproduction for the checker's Mode D (local fixtures only, no live target):**

1. From an isolated extract of this branch (own `AUTOTESTER_ROOT`, e.g. a fresh temp dir), serve
   `tests/fixtures/crawl_site` locally: `python -m http.server 0 --directory
   tests/fixtures/crawl_site --bind 127.0.0.1` (or reuse the `serve_dir` pattern
   `tests/conftest.py:60-80` already uses for the real-browser suite) to get a `base_url`.
2. Create a project (`slug=covbadspec`) with that `base_url`, `allowed_domains=["127.0.0.1"]`,
   and grant a crawl approval for it (`uv run autotester approve` or the credentials page's
   crawl-approval card) — same shape `tests/test_explore_live.py`'s `crawl_result` fixture uses.
3. Launch the UI: `uv run uvicorn autotester.ui.app:app --host 127.0.0.1 --port 8069`.
4. In a real browser, open `http://127.0.0.1:8069/projects/covbadspec/crawls` and submit "Explore
   now" with default bounds — this exercises `start_crawl` end-to-end against the local fixture
   site; expect a 303 to the new crawl's page and a 200 render (crawl record now exists,
   `flowspec.json` does not yet, so this step alone doesn't touch AT-477's guard — it proves the
   crawl completes and saves normally first).
5. Write `{ this is not a flowspec` directly into that project's `flowspec.json` on disk (do NOT
   go through the FlowSpec review UI, which would validate it).
6. Reload the crawl page: expect 200, not 500, with the "Against the FlowSpec" card stating the
   spec could not be read (this is the AT-477 crawl-page half, matching AT-472's precedent).
7. Submit "Explore again" from the crawls list: expect a 303 redirect to the new crawl's page
   (not 500), and the crawl's own record (screens/actions/status) visible on that page — this is
   the AT-477 `POST /explore` half, i.e. the crawl's own result survives the broken spec.
8. Console: expect 0 new console errors from either request (the original AT-477 evidence had 2,
   both the 500s this fix removes).

## Known limits (disclosed, not claimed)

- **No live-browser run this cycle.** The fix and both regression tests are proven at the
  route/store layer only (FastAPI `TestClient`, crawl stubbed). The reproduction steps above are
  provided for the checker's Mode D rather than executed here, per this unit's brief.
- **Full non-browser suite not run** (RAM gap, 1.72 GB free vs 3.5 GB ceiling) — only the six
  targeted test files above were run, chosen because they're every test file that imports or
  exercises `routes_crawls.py`.
- **The error message text is new** (`"the FlowSpec could not be read -- ..."`), not reused
  verbatim from `crawl_coverage.of_run`'s `spec_error` string (`"could not read the FlowSpec --
  ..."`) — deliberately close but not identical, since the UI-facing wording and the
  workbook-facing wording are two different call sites with no shared constant today; flagged
  here in case the checker wants them unified into one string.

## Status: checked-PASS (cycle 1, ad31a72)
