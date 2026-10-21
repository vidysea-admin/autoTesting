# Manifest — bench-inputs-ui

**Status:** checked-PASS
**Fix cycle:** 1
**Unit:** bench-inputs-ui — a person marks AutoTester findings "real bug" / "false positive" from the crawl and run pages (T-136), and uploads the private benchmark answer list from a project page (T-218). Umesh 2026-10-21: he will rule on the T-136 findings "from the product myself" and supply the CEO findings list "tool mai se".
**Contract:** `qa/contracts/bench.md` K3 (`BenchTrial.score` is the only scorer; adjudication added there, not a second scorer) · `qa/contracts/core-invariants.md`
**Goal task:** T-136, T-218 (input side only)
**Dual check:** required (auth: new authenticated routes with project.edit checks; security: private file upload and storage under `.work/`)
dual-trigger: auth src/autotester/ui/routes_bench_inputs.py:49
dual-trigger: security src/autotester/stages/bench_inputs.py:49
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 8956c9bc (worktree .worktrees/bench-inputs-ui, branch wave/bench-inputs-ui)
**Code SHA:** 2203990e

## What changed
- `src/autotester/schema/bench.py` — `Finding.adjudication` (real / false_positive / None); `Mark`, `BenchMarks`; `BenchTrial.score()` adds `adjudicated_real`, `adjudicated_false_positives`, `unadjudicated`, `adjudicated_fp_rate` (false / (real + false), None when nothing is ruled). The legacy FP rate is untouched.
- `src/autotester/stages/bench_marks.py` (new) — marks overlay stored beside the bench files (`core/paths.py` `bench_marks`): `finding_key` (sha256 of source + text, crawl `(seen Nx ...)` tally stripped), `set_mark` (None undoes), `marked`, `apply_marks`. The marks file holds hashes and rulings, never finding text; a finding already matched to a known bug is never re-ruled; the stored trial is never rewritten, so a mark survives `bench_from_run` replacing the trial.
- `src/autotester/stages/acceptance_comparison.py:124` — the AutoTester column is built from the marked trial; with any mark the FP rate is over adjudicated findings only (`adjudicated_findings_only`), unmarked findings are counted in `unadjudicated` and not in the rate; with no mark the old rate and population are unchanged. `schema/acceptance.py` gets the three counts; `scripts/check_acceptance_comparison.py` prints them.
- `src/autotester/stages/bench_inputs.py` (new) — `save_atomic_list`: size cap 256 KiB, validated as `AtomicList` (errors carry location and message only, never the value), written via tmp + `os.replace` under `.work/ceo-bench/<slug>/`, sha256 pinned in `atomic-list.pin.json` with replaced hashes; `load_pinned_list` re-hashes against the pin. `schema/ceo_inputs.py` gets `AtomicListPin`.
- `src/autotester/ui/routes_bench_inputs.py` (new) — `GET /projects/{slug}/bench`; `POST .../bench/marks`; `POST .../bench/atomic-list`. Redirect target is limited to `/projects/{slug}/...`.
- `src/autotester/ui/bench_inputs_view.py` (new) — marking card (crawl and run pages), the page, the pin card; every interpolation escaped; the list is never read or linked, only its sha256 and counts shown.
- `src/autotester/ui/routes_crawls.py`, `routes_report.py`, `routers.py`, `project_view.py`, `theme.py`, `theme_style.py` — card mounted, router registered, project-page button, sidebar sub-link.
- `src/autotester/auth/policy.py:95,109` — `/bench` GET is project.view; `/bench/marks` and `/bench/atomic-list` POST are project.edit. `tests/test_ui_auth_policy_table.py` pinned rows updated.
- Cycle 1 (checker A and B FAIL on C1): `stages/bench_marks.py::set_mark` now loads, changes and writes under `file_lock` on a sidecar `.lock` with a bounded retry on the Windows `os.replace` PermissionError; `core/file_lock.py` tolerates the first-creation write race that this exposed (a second thread writing the init byte while the first held its lock); `ui/routes_bench_inputs.py::upload_atomic_list` streams through `ui/upload_stream.py::stream_upload` (new optional `vet` name check, default unchanged) with the 256 KiB cap and a `.json` name check, so an oversize body is refused 413 without being spooled; `stages/bench_inputs.py::save_atomic_list` reads the pin and writes list and pin under a lock and writes the list through `write_bytes` (unique temp name). Left for the ledger: the redirect dot-segments, unknown-key marks, the adjudicated-rate design question, the unwired T-218 reader.

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L - new authenticated routes, permission checks and a private-file upload
Round: 9 files in the cycle-1 fix (3 src edited in place, upload_stream and file_lock one small edit each, 1 new test file, 2 test files edited, MAP.md regenerated), 2 defects plus 3 folded items, est 90 min; cycle 0 was one builder over the 400-line guide (shared data path)
Owners: OG-BENCH-INPUTS
Base / checked state: 8956c9bc / 2203990e, clean tree
Gate answers: none apply (no gate in qa/gates touches benchmark inputs; Umesh's 2026-10-21 answer is the authority for both inputs).
Affected tests / full-suite trigger: tests/test_bench_marks.py, tests/test_ui_bench_inputs.py, tests/test_ui_auth_policy_table.py, plus the 237-test affected set (bench, acceptance, crawls and report UI) run once before the policy-table fix; no full suite.
Tests[C1]: tests/test_bench_marks.py - one real, one false, one unmarked gives FP rate 0.5 and counts (1, 1, 1) and the checker script line; no mark leaves the old rate and population; mark survives trial replacement; undo; trial bytes unchanged by a mark; marks file holds no finding text; matched finding never re-ruled; crawl key ignores the tally. tests/test_ui_bench_inputs.py::test_c1_* - editor marks crawl and run findings and undoes; view-only sees rulings, no controls, 403 on POST; anonymous and cross-origin refused with nothing written; malformed 400; off-site next ignored. Cycle 1 adds tests/test_bench_marks.py::test_simultaneous_set_mark_calls_lose_no_ruling (32 threads behind a barrier, every ruling stored, no writer raises) and tests/test_ui_bench_inputs.py::test_c1_simultaneous_marks_over_http_all_stored_and_none_errors (24 simultaneous editor POSTs, all 303, all stored).
Tests[C2]: tests/test_ui_bench_inputs.py::test_c2_* - editor upload stored under `.work/`, sha256 shown and pinned; list never served and `.work/` ignored; view-only no form and 403; six bad lists (empty, not JSON, no items, extra `text` key, bad priority, duplicate ids) refused without echoing content and nothing stored; replacement records the old hash; list edited after pinning no longer loads; missing file field 400. Cycle 1 adds tests/test_bench_inputs_stage.py (a valid-JSON list of exactly MAX_BYTES accepted, MAX_BYTES+1 refused and the earlier pin untouched; 12 simultaneous uploads leave the list matching its pin and every hash recorded) and tests/test_ui_bench_inputs.py::test_c2_an_oversize_list_is_refused_413_without_the_body_being_spooled (413 with `Request.form` forbidden, a `.exe` name 400 before storage, a non-multipart body 400, staging removed).
Tests[C3]: tests/test_ui_bench_inputs.py::test_c3_* - every control labelled and no external request in the page body; sidebar and project page link to the page; view-only can open the page, unknown project 404; finding text escaped. tests/test_ui_auth_policy_table.py - pinned rows for the three routes.
Falsification[C1]: copy-mutants in `.work/tmp/bi-mut/wt` (a copy of src, tests, scripts; worktree `.venv` python run with cwd in the copy; control 34 passed): `ruled = 0`: red 1; overlay removed (`apply_marks` skipped): red 3; unmarked counted as false positive: red 1; matched finding re-ruled: red 1; crawl key includes the tally: red 1; key is the finding text (marks file would hold text): red 1; POST routes opened to viewer (policy `_VIEW`): red 2; `may_mark` returns True: red 1.
Falsification[C2]: pin hashes `raw[:-1]`: red 2; validation replaced by a fixed list: red 6; error reason appends the pydantic input: red 1; page prints rows back (`A1` shown): red 1; POST routes open to viewer: red 2 (shared with C1).
Falsification[C3]: label removed from the file input: red 1; sidebar link disabled: red 1; off-site `next` redirect allowed (`safe_next` result used directly): red 1.
Falsification[C1 cycle 1]: copy-mutants in `.work/tmp/bi-mut/wt` (control 37 passed): `set_mark` lock replaced by `nullcontext`: red 2 (the thread test and the HTTP test), red 1 with only the thread test selected. Checker B repro `qa/evidence/bench-inputs-ui-B/race.py` re-run against the fixed worktree (copy at `.work/tmp/bi-race/race_fixed.py`): 10 rounds of 20 simultaneous `set_mark`, 0 lost, 0 errors (was 10 of 10 rounds lost, 147 PermissionError).
Falsification[C2 cycle 1]: atomic-list lock replaced by `nullcontext`: red 1; size check `if False`: red 1; `>=` instead of `>`: red 1; `await request.form()` added before the stream (spooled body): red 1; route limit raised to 50 MiB: red 1. One survivor, fixed temp name (`atomic-list.json.tmp`) kept: green, because the lock now serialises writers; the unique temp name from `write_bytes` is a second guard, not isolated by a test.
Pre-check[C1]: 2203990e uv run pytest tests/test_bench_marks.py tests/test_ui_bench_inputs.py tests/test_bench_inputs_stage.py tests/test_ui_auth_policy_table.py -> 39 passed t=4 blobs=tests/test_bench_marks.py:4dde7d1,tests/test_ui_bench_inputs.py:8a55914,tests/test_bench_inputs_stage.py:915d697,tests/test_ui_auth_policy_table.py:e14f15c
Pre-check[C2]: 2203990e uv run pytest tests/test_bench_inputs_stage.py tests/test_ui_bench_inputs.py -> 27 passed t=2 blobs=tests/test_bench_inputs_stage.py:915d697,tests/test_ui_bench_inputs.py:8a55914
Pre-check[C3]: 2203990e uv run pytest tests/test_ui_bench_inputs.py tests/test_ui_auth_policy_table.py -> 27 passed t=2 blobs=tests/test_ui_bench_inputs.py:8a55914,tests/test_ui_auth_policy_table.py:e14f15c
Lint: 2203990e `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean (docs/MAP.md regenerated with `autotester map` and committed in this fix). Also run, to cover the shared-helper edits: tests/test_ui_intake.py tests/test_ui_project_intake.py tests/test_intake_gate_auth.py (upload_stream) -> passed within a 94-test run; tests/test_issue_ids.py tests/test_ui_env_editor.py plus the schedule and tick tests (file_lock users) -> 280 passed, 1 skipped.
mutant-cap-raise: Tier L covers new authenticated routes and a private-file upload across three criteria; 17 mutants were run: 15 first, of which 2 survived (an include_input flag that never reached the output, and a key variant that never reached the file) and were replaced by 2 sharper ones that went red; 5 target permission and storage boundaries. Cycle 1 adds 8 more (7 red, 1 survivor kept green by the new lock) for the two reproduced races and the streamed cap.
Metrics: start=2026-10-21T07:00:00Z end=2026-10-21T10:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=25 cycle=1 resumes=2 tokens=unavailable policy=proportional-verification/2026-10-19.17 lane=normal check_s=unavailable mutants=25 defects_unit=0 defects_6c=0 tests=39 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_bench_marks.py tests/test_ui_bench_inputs.py tests/test_ui_auth_policy_table.py` -> expected: 36 passed.
- `uv run ruff check src tests scripts` -> All checks passed.
- `uv run autotester doctor` -> only the two MAP.md staleness violations.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | marks reach the scorer; unmarked stay unadjudicated; only editors mark | tests/test_bench_marks.py::test_one_real_one_false_one_unmarked_gives_fp_rate_over_the_two_adjudicated; tests/test_ui_bench_inputs.py::test_c1_a_view_only_account_sees_the_ruling_without_controls_and_cannot_mark | `ruled = 0`; overlay removed; unmarked as FP; POST open to viewer | red on each (1, 3, 1, 2 failed) |
| C2 | list validated, stored under `.work/`, never served, hash pinned | tests/test_ui_bench_inputs.py::test_c2_an_editor_uploads_the_list_it_is_stored_privately_and_its_hash_is_pinned; ::test_c2_a_bad_list_is_refused_without_echoing_its_content_and_nothing_is_stored | wrong hash; no validation; input echoed; rows shown back | red on each (2, 6, 1, 1 failed) |
| C3 | labelled controls, no external request, CSRF and permission, sidebar link | tests/test_ui_bench_inputs.py::test_c3_every_new_control_has_a_visible_label_and_no_page_loads_anything_external; ::test_c1_anonymous_and_cross_origin_marks_are_refused_and_nothing_is_written | label removed; sidebar link off; off-site next | red on each (1, 1, 1 failed) |

## Live browser evidence
SKIP - maker smoke only; the checker runs Mode D when the UI changed (crawl page, run page, `/projects/{slug}/bench`, sidebar).

## Status: ready-for-check
