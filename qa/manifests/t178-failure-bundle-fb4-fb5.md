# Manifest - t178-failure-bundle-fb4-fb5 (T-178: FB4 + FB5 + bundle loader containment)

Contract: qa/contracts/failure-bundle.md (FB4, FB5 judged here; FB1-FB3 already PASS, `qa/verdicts/t178-failure-bundle.md`, must keep passing); review-gate.md shape; core-invariants C2/C5
Goal task: T-178 (stays pending until a checker PASS here; the maker closes it)
Brief: qa/briefs/t178-failure-bundle-fb4-fb5.md
Status: ready-for-check
Fix cycle: 1
Repair base: a7d3fa6c (checker seat A full suite FAIL: tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed; the unit's two `autotester expand <slug> --proposals` advice sites were not registered)
Integrated master: 8791b76bf97ff0bfdd65e2228afb70bb65f37b1f (merge commit 2587a7b18699e5e24036dd8bf14922f51fc3ee77); conflicts only in src/autotester/cli.py and src/autotester/core/paths.py (both docstring-only, master's wording taken)
Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Base: master 3d8f7d5af028299ac4b4567f26ce196a417af569 (now merged up to 8791b76b), branch wave/t178-failure-bundle-fb4-fb5 (worktree .worktrees/t178-failure-bundle)
Product commit: c142f8f10a2cd1fe0d99e8aa75868e4b1ea3a68b (fix cycle 1; the cycle-0 product was bb76275f304efcc5b094066c6804b673e8ff8dbe, repair base a7d3fa6c). The repair is the master merge 2587a7b1 plus c142f8f1 (tests/test_cli_advice_resolves.py only); docs/MAP.md regenerates to no change. A manifest cannot name its own commit.
Executor: claude-sonnet-subagent (maker build subagent)
Manifest name: `t178-failure-bundle-fb4-fb5`, NOT `t178-failure-bundle`. Master already holds a checked-PASS manifest `qa/manifests/t178-failure-bundle.md` and verdict `qa/verdicts/t178-failure-bundle.md` for FB1-FB3; reusing the slug would overwrite that record and the handshake. The checker's verdict goes to `qa/verdicts/t178-failure-bundle-fb4-fb5.md` (brief section 11).

Dual check: required
dual-trigger: security src/autotester/stages/failure_bundle.py:211-212
Round cap: SECURITY CLASS -- the bundle loader joined an unrestricted manifest name to the bundle directory (lines 211-212 now resolve it and refuse an escape before hashing); the plan review named this a real security dual trigger. The dual check judges FB1-FB5 as a whole.
Round cap (non-security files, for the record): counted by `grep -l <path> qa/verdicts/*.md`, which counts verdicts that NAME a file, not PASS lines, so it overstates. Checker A counted seven seams past the cap of 2: schema/case.py (11), stages/expand.py (12), core/project_store.py [src/autotester/store/project_store.py] (15), core/paths.py (16), cli.py (10), ui/routes_runs.py (17), ui/routes_learn.py (2 at cycle 0, 3 with this unit). Other touched files at or under the cap: schema/failure_bundle.py 1, stages/failure_bundle.py 1, stages/eval_compiler.py 1, ui/run_queue.py 1, schema/run_queue.py 0. **An owner waiver is owed before merge** for the seven seams; the unit also rests on SECURITY CLASS for the dual check.
Persona walk: required (dev), docs/plan.md row 15 / spec R24. NOT done by the builder (the checker walks it, visible browser, browser lane max 1). Surfaces changed: Learn page "generate cases" (`ui/routes_learn.py::generate_cases` now stages proposals and refuses with a themed page naming `autotester expand <slug> --proposals` when approval is missing); `POST /projects/<slug>/run?priority=p0` (new repeatable query). No browser, model or network call was made by the builder; all tests use fakes.
Gate answers: qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md:73 and :75 (order only, never skip: priority selection is an opt-in filter, the default keeps every case in the cheap-first order); no T-178-specific gate exists; no new module (none authorized, none created); D-041, D-081.

## Criteria (verbatim from the contract)

### FB4 - Case priority is real, selectable, and does not weaken `pinned`

`Case.priority ∈ {p0, p1, p2, p3}` in `schema/` (`extra="forbid"`), with a stated default. A regression
run can select by priority. Pinned cases (AT-585) are `p0`, and `ProjectStore.delete_case` still
**refuses** to delete them - the AT-585 guarantee is preserved through the migration, not dropped with
the flag. A case saved before this unit still loads.

**Verify:** four fixture cases, one per priority - selecting `p0` runs exactly the `p0` case(s) and
the count is asserted. Pin a case, then attempt `delete_case` - refused, as before. Load a case file
written without a priority - it loads with the stated default. Sabotage: make selection ignore the
priority - the count assertion goes red.

### FB5 - Human pruning happens before provider spend

Proposed cases are staged as **proposals** (class, title, rationale - no steps yet) for a human to
approve or prune, and **only approved proposals reach the provider calls that generate steps**. The
review gate is not bypassable (the `review-gate.md` shape).

**Verify:** a fixture with 5 proposals, 3 pruned - a counting fake provider records **exactly 2**
step-generation calls; prune all 5 and the count is **0**. With no approval recorded, nothing is
generated. Sabotage: generate before the approval check - the pruned-proposals count goes red.

### Containment (review-mandated amendment of FB1, not a contract criterion)

`BundleFile.name` rejects absolute, traversal and non-POSIX names; `load_bundle` resolves containment (symlink and junction escape included) before reading or hashing.

## What changed (all existing files, edited in place; no new module)

- `src/autotester/schema/case.py` (258): `CasePriority`, `Case.priority` (default `p2`; pinned forces `p0` at load; `with_fixed_step` keeps priority/pin/issue trace), step-less `CaseProposal` (identity = exact spec snapshot, project, flow, class, title, rationale; review needs a human name and time).
- `src/autotester/store/project_store.py` (299, at the cap; docstring compaction keeps the issue ids): `list_cases(priorities=None)` (selected priorities UNION pinned p0, deduplicated by id, default order unchanged), `stage_case_proposals`, `review_case_proposal` (HAPPY prune persists as proposed), `list_case_proposals`, `preflight_case_proposals`.
- `src/autotester/core/paths.py` (300, at the cap): `ProjectPaths.case_proposals`.
- `src/autotester/stages/expand.py` (188; +`stage_and_review`, moved from cli.py in fix cycle 1): `propose_cases`, approval gate on `expand`/`expand_flow` (`store=`, `proposal_ids=`); the whole batch is validated before the first prompt is built.
- `src/autotester/stages/eval_compiler.py` (114): `compile_evals(..., store=, proposal_ids=)` threaded to `expand_flow` (brief's known gap; without a store it raises `ValueError` and spends 0 calls).
- `src/autotester/schema/failure_bundle.py` (73): `BundleFile.name` validator. `src/autotester/stages/failure_bundle.py` (219): `load_bundle` containment only; the input's `persist_failure_bundle` / `failure_step` / `bundle_reference` run-and-report wiring is NOT ported (owned by `wave/at787-bundle-wiring`).
- `src/autotester/cli.py` (300; fix cycle 1: after the master merge the review block moved into `stages/expand.py::stage_and_review` to stay at the cap): `expand` gains `--proposals`, `--approve ID`, `--prune ID`, `--by NAME` (CLI is the review door). `src/autotester/ui/routes_learn.py` (300, at the cap): `generate_cases` stages proposals and refuses on a themed page when approval is missing; the credential/availability guard order is untouched.
- `src/autotester/ui/routes_runs.py` (266): `trigger_run(priority=...)` and `_prepare_run(slug, priorities)`. **Deviation from the brief, forced by the hosting re-land:** `trigger_run` no longer runs cases; it queues and returns, and the queue calls `_prepare_run(entry.project)` later. Passing the filter only to the press-time `_prepare_run` would have run EVERY case. So the priorities ride the queue entry: `src/autotester/schema/run_queue.py` (53) `QueueEntry.priorities` (default None, so old `run_queue.json` rows still load) and `src/autotester/ui/run_queue.py` (231) `RunQueue.submit(..., priorities=)`; `_run_queued` passes `entry.priorities`. Two files beyond the brief's list.
- Not touched: `ui/run_execution.py`, `tests/test_ui_runs_serial_resilience.py` (`wave/at733-bounded` owns them), `pyproject.toml`, `uv.lock`, `qa/contracts/`, the root checkout.
- `docs/MAP.md` regenerated as the last commit. `docs/ARCHITECTURE.md` NOT edited (Lab Protocol: needs an authorizing DECISIONS entry written first); it still owes a `case_proposals` line and the `QueueEntry.priorities` note. For the maker.
- Tests, extended in place: `tests/test_schema.py`, `test_store.py`, `test_expand.py`, `test_expand_cli.py`, `test_failure_bundle.py`, `test_ui_learn.py`, `test_ui_runs.py`, `test_eval_compiler.py` (+2 FB5 caller tests, `tests/eval_compiler_fixtures.py::approved_store`). The input's test_ui_runs docstring reflow of an unrelated test was not ported.

## Verification scope

Affected tests: the eight extended files, `tests/test_pinned_regression.py` (AT-585 guarantee), `tests/test_run_queue.py`, `test_run_queue_resilience.py`, `test_ui_runs_queue.py` (QueueEntry/submit changed), `test_regression_proof.py`, `test_cli_issues.py` (call `list_cases`). One pytest process at a time, `-p no:xdist`, no full suite and no directory run; the maker runs the integration suite once under the machine lock.

Pre-check[FB4]: c142f8f1 uv run pytest -p no:xdist tests/test_schema.py tests/test_store.py tests/test_pinned_regression.py tests/test_ui_runs.py -> 60 passed, 1 warning in 2.41s
Pre-check[FB5]: c142f8f1 uv run pytest -p no:xdist tests/test_expand.py tests/test_expand_cli.py tests/test_ui_learn.py tests/test_eval_compiler.py -> 61 passed, 1 warning in 18.46s
Pre-check[CONTAIN]: c142f8f1 uv run pytest -p no:xdist tests/test_failure_bundle.py -> 23 passed in 2.83s (FB1-FB3 nodes plus the three containment tests; the junction test makes a real `mklink /J` and asserts on the hashing step)
Pre-check[C2]: c142f8f1 uv run autotester doctor -> exit 0, doctor: clean (file <= 300, function <= 50; also uv run ruff check src tests scripts: All checks passed!; uv run autotester map: no diff)
Pre-check[C5]: c142f8f1 uv run pytest -p no:xdist tests/test_failure_bundle.py -> 23 passed in 2.83s (same run as CONTAIN; includes the planted-secret and check_no_secrets FB3 nodes; this unit adds no new bundle writer)
Pre-check[ADVICE]: c142f8f1 uv run pytest -p no:xdist tests/test_cli_advice_resolves.py -> 32 passed in 14.31s (the fix-cycle-1 repair: EXPECTED_SITES gains `("cli.py", "expand")` and `("ui/routes_learn.py", "expand")`, EXPECTED_SITE_COUNT 21 -> 23; `autotester expand --help` shows `--proposals`, `--approve`, `--prune`)
Pre-check[GUARDS]: c142f8f1 uv run pytest -p no:xdist, one process each: tests/test_cli_surface.py -> 46 passed in 2.28s; tests/test_cli_harness_safety.py -> 4 passed in 4.18s; tests/test_ui_origin_guard.py -> 87 passed, 1 warning in 2.37s
Pre-check: c142f8f1 uv run pytest -p no:xdist <the 8 extended files + test_pinned_regression + test_run_queue + test_run_queue_resilience + test_ui_runs_queue + test_regression_proof + test_cli_issues, 12 processes> -> 208 passed, 0 failed, plus the ADVICE and GUARDS runs above (32 + 137 passed)
Metrics: unavailable

## Falsification (throwaway copy of src/tests/scripts under the session scratchpad, `PYTHONPATH` at the copy; the worktree was never modified by them; every mutant red by assertion on the expected count, restored copy green)

- Falsify[FB4]: `list_cases` ignores `priorities` (`if priorities is None:` -> `if True:`) -> `test_priority_selection_adds_pinned_p0_once_and_preserves_default_order` and `test_trigger_runs_exact_selected_priority_plus_pinned_once` red: "Left contains 3 more items" (all four fixture cases ran, not the p0 pair). Green before: 9 passed.
- Falsify[FB5]: pruned proposals reach the provider (`approved_batch` returns `status != "x"` instead of `== "approved"`) -> `test_five_nonhappy_proposals_prune_before_spend` red both ways: `assert 5 == 2` and `assert 5 == 0`. Green before: 2 passed.
- Falsify[CONTAIN]: removed the `target.is_relative_to(root)` check in `load_bundle` -> `test_loader_refuses_real_directory_link_escape_before_hashing` red on "escaped file reached hashing/read" (the hashing assertion, not setup). Green before: 3 passed.
- Falsify[ADVICE] (fix cycle 1): in a throwaway copy of src/tests/scripts (scratchpad `falsify-t178-r1-7q2`), deleted the `("ui/routes_learn.py", "expand")` entry from EXPECTED_SITES -> `test_no_advice_site_can_vanish_unnoticed` red on `assert found == EXPECTED_SITES` with `new: [('ui/routes_learn.py', 'expand')]` (1 failed, 31 passed); restored -> 32 passed.

## Held / not claimed

- Nothing is held on an owner answer: every needed answer exists (D-081, the two RU3 gate lines, the plan-review amendments). Choices the checker must accept, none an `Answered:` fact: default `p2`; CLI-only human review door (contract no-fire list); the `QueueEntry.priorities` plumbing above.
- No in-UI approve/prune screen (separate unit, owner decision). Report links to bundle ids and landing `wave/at787-bundle-wiring` stay out of scope.
- A persona walk is owed by the checker (see above). The builder ran no browser.

## PROPOSED-ISSUE (no ids; the checker files them)

- PROPOSED-ISSUE: `trigger_run` with a priority set that selects zero cases answers "project has no cases to run" (400), which is misleading when the project has cases but none match; low.
- PROPOSED-ISSUE: `Case.priority` is not editable from the Cases page, so an operator cannot demote or promote a case in the UI (only by editing `cases.jsonl`); low.
- PROPOSED-ISSUE: `core/paths.py`, `store/project_store.py` and `ui/routes_learn.py` sit exactly on the 300-line cap, so the next edit in each must free lines first (the brief predicted this); low.
