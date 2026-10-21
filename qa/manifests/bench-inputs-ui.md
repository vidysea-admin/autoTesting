# Manifest — bench-inputs-ui

**Status:** ready-for-check
**Fix cycle:** 0
**Unit:** bench-inputs-ui — a person marks AutoTester findings "real bug" / "false positive" from the crawl and run pages (T-136), and uploads the private benchmark answer list from a project page (T-218). Umesh 2026-10-21: he will rule on the T-136 findings "from the product myself" and supply the CEO findings list "tool mai se".
**Contract:** `qa/contracts/bench.md` K3 (`BenchTrial.score` is the only scorer; adjudication added there, not a second scorer) · `qa/contracts/core-invariants.md`
**Goal task:** T-136, T-218 (input side only)
**Dual check:** required (auth: new authenticated routes with project.edit checks; security: private file upload and storage under `.work/`)
dual-trigger: auth src/autotester/ui/routes_bench_inputs.py:49
dual-trigger: security src/autotester/stages/bench_inputs.py:49
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 8956c9bc (worktree .worktrees/bench-inputs-ui, branch wave/bench-inputs-ui)
**Code SHA:** 16bcf2b4

## What changed
- `src/autotester/schema/bench.py` — `Finding.adjudication` (real / false_positive / None); `Mark`, `BenchMarks`; `BenchTrial.score()` adds `adjudicated_real`, `adjudicated_false_positives`, `unadjudicated`, `adjudicated_fp_rate` (false / (real + false), None when nothing is ruled). The legacy FP rate is untouched.
- `src/autotester/stages/bench_marks.py` (new) — marks overlay stored beside the bench files (`core/paths.py` `bench_marks`): `finding_key` (sha256 of source + text, crawl `(seen Nx ...)` tally stripped), `set_mark` (None undoes), `marked`, `apply_marks`. The marks file holds hashes and rulings, never finding text; a finding already matched to a known bug is never re-ruled; the stored trial is never rewritten, so a mark survives `bench_from_run` replacing the trial.
- `src/autotester/stages/acceptance_comparison.py:124` — the AutoTester column is built from the marked trial; with any mark the FP rate is over adjudicated findings only (`adjudicated_findings_only`), unmarked findings are counted in `unadjudicated` and not in the rate; with no mark the old rate and population are unchanged. `schema/acceptance.py` gets the three counts; `scripts/check_acceptance_comparison.py` prints them.
- `src/autotester/stages/bench_inputs.py` (new) — `save_atomic_list`: size cap 256 KiB, validated as `AtomicList` (errors carry location and message only, never the value), written via tmp + `os.replace` under `.work/ceo-bench/<slug>/`, sha256 pinned in `atomic-list.pin.json` with replaced hashes; `load_pinned_list` re-hashes against the pin. `schema/ceo_inputs.py` gets `AtomicListPin`.
- `src/autotester/ui/routes_bench_inputs.py` (new) — `GET /projects/{slug}/bench`; `POST .../bench/marks`; `POST .../bench/atomic-list`. Redirect target is limited to `/projects/{slug}/...`.
- `src/autotester/ui/bench_inputs_view.py` (new) — marking card (crawl and run pages), the page, the pin card; every interpolation escaped; the list is never read or linked, only its sha256 and counts shown.
- `src/autotester/ui/routes_crawls.py`, `routes_report.py`, `routers.py`, `project_view.py`, `theme.py`, `theme_style.py` — card mounted, router registered, project-page button, sidebar sub-link.
- `src/autotester/auth/policy.py:95,109` — `/bench` GET is project.view; `/bench/marks` and `/bench/atomic-list` POST are project.edit. `tests/test_ui_auth_policy_table.py` pinned rows updated.

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L - new authenticated routes, permission checks and a private-file upload
Round: 20 files, 3 criteria, est 180 min, about 540 src and 370 test lines changed, over the 400-line guide; kept as one builder because the marks overlay, the comparison and the routes share one data path and splitting would have meant two builders editing `bench.py` and `policy.py`
Owners: OG-BENCH-INPUTS
Base / checked state: 8956c9bc / 16bcf2b4, clean tree
Gate answers: none apply (no gate in qa/gates touches benchmark inputs; Umesh's 2026-10-21 answer is the authority for both inputs).
Affected tests / full-suite trigger: tests/test_bench_marks.py, tests/test_ui_bench_inputs.py, tests/test_ui_auth_policy_table.py, plus the 237-test affected set (bench, acceptance, crawls and report UI) run once before the policy-table fix; no full suite.
Tests[C1]: tests/test_bench_marks.py - one real, one false, one unmarked gives FP rate 0.5 and counts (1, 1, 1) and the checker script line; no mark leaves the old rate and population; mark survives trial replacement; undo; trial bytes unchanged by a mark; marks file holds no finding text; matched finding never re-ruled; crawl key ignores the tally. tests/test_ui_bench_inputs.py::test_c1_* - editor marks crawl and run findings and undoes; view-only sees rulings, no controls, 403 on POST; anonymous and cross-origin refused with nothing written; malformed 400; off-site next ignored.
Tests[C2]: tests/test_ui_bench_inputs.py::test_c2_* - editor upload stored under `.work/`, sha256 shown and pinned; list never served and `.work/` ignored; view-only no form and 403; seven bad lists (empty, not JSON, no items, extra `text` key, bad priority, duplicate ids, over the size cap) refused without echoing content and nothing stored; replacement records the old hash; list edited after pinning no longer loads; missing file field 400.
Tests[C3]: tests/test_ui_bench_inputs.py::test_c3_* - every control labelled and no external request in the page body; sidebar and project page link to the page; view-only can open the page, unknown project 404; finding text escaped. tests/test_ui_auth_policy_table.py - pinned rows for the three routes.
Falsification[C1]: copy-mutants in `.work/tmp/bi-mut/wt` (a copy of src, tests, scripts; worktree `.venv` python run with cwd in the copy; control 34 passed): `ruled = 0`: red 1; overlay removed (`apply_marks` skipped): red 3; unmarked counted as false positive: red 1; matched finding re-ruled: red 1; crawl key includes the tally: red 1; key is the finding text (marks file would hold text): red 1; POST routes opened to viewer (policy `_VIEW`): red 2; `may_mark` returns True: red 1.
Falsification[C2]: pin hashes `raw[:-1]`: red 2; validation replaced by a fixed list: red 6; error reason appends the pydantic input: red 1; page prints rows back (`A1` shown): red 1; POST routes open to viewer: red 2 (shared with C1).
Falsification[C3]: label removed from the file input: red 1; sidebar link disabled: red 1; off-site `next` redirect allowed (`safe_next` result used directly): red 1.
Pre-check[C1]: 16bcf2b4 uv run pytest tests/test_bench_marks.py tests/test_ui_bench_inputs.py tests/test_ui_auth_policy_table.py -> 36 passed t=3 blobs=tests/test_bench_marks.py:5a475f7,tests/test_ui_bench_inputs.py:34a04e0,tests/test_ui_auth_policy_table.py:e14f15c
Pre-check[C2]: 16bcf2b4 uv run pytest tests/test_ui_bench_inputs.py -> 25 passed t=1 blobs=tests/test_ui_bench_inputs.py:34a04e0
Pre-check[C3]: 16bcf2b4 uv run pytest tests/test_ui_bench_inputs.py tests/test_ui_auth_policy_table.py -> 27 passed t=2 blobs=tests/test_ui_bench_inputs.py:34a04e0,tests/test_ui_auth_policy_table.py:e14f15c
Lint: 16bcf2b4 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both MAP.md stale-generated / stale-committed (new modules). Judgement call: left to the merge-queue owner to regenerate with `autotester map`, per the T-208 and T-218 precedent; the base worktree is clean.
mutant-cap-raise: Tier L covers new authenticated routes and a private-file upload across three criteria; 17 mutants were run: 15 first, of which 2 survived (an include_input flag that never reached the output, and a key variant that never reached the file) and were replaced by 2 sharper ones that went red; 5 target permission and storage boundaries.
Metrics: start=2026-10-21T07:00:00Z end=2026-10-21T10:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=17 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-19.17 lane=normal check_s=unavailable mutants=17 defects_unit=0 defects_6c=0 tests=34 tests_min=1

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
