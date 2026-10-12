# Build brief - t178-failure-bundle-fb4-fb5 (T-178 FB4 + FB5 + loader containment, readiness pass 2026-10-11, READY)

Written by a read-only readiness pass. Nothing here was built or run. Where the repo does not say, this brief says `unknown`.
Verdict: **READY**. The contract exists (DRAFT, goes ACTIVE on T-178's first PASS), the plan was independently reviewed (APPROVED-AS-AMENDED), and a complete uncommitted build exists as INPUT. Dispatch trigger: none outstanding. Scope is deliberately narrower than the codex input (see section 4 and section 10).

## 1. Policy and tier

- `Policy-Version: proportional-verification/2026-10-10.9`
- Tier: **L**. Triggers: (a) a security change to a file-reading path, the bundle loader (`src/autotester/stages/failure_bundle.py:203`, `target = path / f.name`, joins an unrestricted manifest name); (b) a data-shape migration, `Case` gains `priority` and legacy case files must still load; (c) a persisted-state write, step-less proposals and their human approvals are stored under the project directory.
- `Dual check: required`. Trigger: `security src/autotester/stages/failure_bundle.py:203`. The independent plan review (`.work/t178-completion-plan-review.md`, amendment 3) found that a tampered manifest name can make the loader hash a file outside the bundle, and says this "supplies an actual .8 security dual trigger"; ordinary priority/proposal changes alone do not. The dual check judges the whole FB1-FB5 feature, not only the loader.

## 2. Root and base

- Root: `D:/autoTesting`
- Base: master `3a16616cf2c99a63c8d763150a1ca6410dfc0acc` (re-read `git -C D:/autoTesting rev-parse master` at dispatch; between `ff7f4ff2`, the codex input's base, and this sha `src/`, `tests/`, `pyproject.toml` and `uv.lock` changed only in `schema/bench.py`, `stages/bench.py`, `tests/test_bench.py`, none of them touched by this unit).
- Branch: fresh `wave/t178-failure-bundle-fb4-fb5` from master. Reason: D-080 item 1 makes master the single trunk and says worktrees are INPUT only. Existing `wave/t178-failure-bundle` is the checked FB1-FB3 unit and is already merged (`b4265f2f`); `codex/t178-completion` (`D:/autoTesting/.worktrees/codex-t178-completion`, HEAD `ff7f4ff2`, 22 modified files + 1 untracked manifest, uncommitted, manifest `Status: BUILDING`) is INPUT: read its diff, re-apply it by hand in the files listed in section 5, do not copy the tree, its manifest, its QA files or its history.
- Dependency lock: this unit does not touch `pyproject.toml` or `uv.lock`.

## 3. Acceptance criteria (verbatim from `qa/contracts/failure-bundle.md`, status DRAFT, goes ACTIVE on T-178's first checker PASS)

Judged in this unit: **FB4 and FB5** (FB1-FB3 are already PASS at cycle 0, verdict `qa/verdicts/t178-failure-bundle.md`, commit `b4265f2f`; they must keep passing and are re-run by the existing tests). Plus the containment repair, which is not a contract criterion but a review-mandated amendment of FB1 (section 4).

### FB4 - Case priority is real, selectable, and does not weaken `pinned`

`Case.priority ∈ {p0, p1, p2, p3}` in `schema/` (`extra="forbid"`), with a stated default. A regression
run can select by priority. Pinned cases (AT-585) are `p0`, and `ProjectStore.delete_case` still
**refuses** to delete them — the AT-585 guarantee is preserved through the migration, not dropped with
the flag. A case saved before this unit still loads.

**Verify:** four fixture cases, one per priority — selecting `p0` runs exactly the `p0` case(s) and
the count is asserted. Pin a case, then attempt `delete_case` — refused, as before. Load a case file
written without a priority — it loads with the stated default. Sabotage: make selection ignore the
priority — the count assertion goes red.

### FB5 - Human pruning happens before provider spend

Proposed cases are staged as **proposals** (class, title, rationale — no steps yet) for a human to
approve or prune, and **only approved proposals reach the provider calls that generate steps**. The
review gate is not bypassable (the `review-gate.md` shape).

**Verify:** a fixture with 5 proposals, 3 pruned — a counting fake provider records **exactly 2**
step-generation calls; prune all 5 and the count is **0**. With no approval recorded, nothing is
generated. Sabotage: generate before the approval check — the pruned-proposals count goes red.

### Contract text the builder must also honour (verbatim)

- Contract no-fire list: "A UI for pruning (the requirement is that pruning happens before spend, not its screen) — if the build adds one, `docs/plan.md` row 13 already marks a persona walk `required`." and "Retiring `Case.pinned` as a field — allowed by the source comment, not required here."
- FB1 (already PASS, must not regress): "It is written under a `.partial` name and renamed only when every part is present; a write that dies leaves the `.partial` marker." FB2: "assembling a bundle from artifacts of more than one run is a hard refusal, not a warning." FB3: "`Redactor.scrub` on text, masked secret inputs in screenshots."
- Plan-review amendments binding on this unit (`.work/t178-completion-plan-review.md`, Result `APPROVED-AS-AMENDED`, bound plan SHA256 `817008D7FF2D1BE60DB62DE262B5732D4A9F9327C59DC2EA93C0538EC6CD0A25`, root-adopted in `.work/t178-completion-plan.md` "Root adoption of independent amendments, 2026-10-08"):
  1. Priority: default `p2`; legacy pinned cases normalise to `p0`; a priority selection is the selected priorities UNION pinned `p0`, deduplicated by case id (selecting `p0` is exactly the p0 rows; selecting `p1` also keeps pinned p0); the default regression keeps every case and the existing cheap-first order. Ordinary (unpinned) p0 deletion is not newly forbidden.
  2. Happy path: staging always includes a step-less HAPPY proposal; a flow's expansion succeeds only with the human's recorded HAPPY approval, else it stays pending; an attempted HAPPY prune leaves the flow pending; an approved expansion emits exactly one verbatim observed-step happy case with zero provider calls. The counted 2/0/0 oracle uses five NON-HAPPY proposals with a separately recorded happy approval. No implicit approval from FlowSpec approval, HTTP presence, provider availability or generator defaults.
  3. Containment: `BundleFile.name` (`src/autotester/schema/failure_bundle.py:48`) rejects absolute, traversal and non-POSIX names, and `load_bundle` resolves containment, symlink and junction escape included, before reading or hashing.

## 4. What exists and what is missing

- **Merged on master (FB1-FB3):** `stages/failure_bundle.py::build_failure_bundle:155` and `::load_bundle:191`, `schema/failure_bundle.py`, `core/paths.py::bundles_dir`, `tests/test_failure_bundle.py` (230 lines). Verdict `qa/verdicts/t178-failure-bundle.md` (cycle 0, FB1-FB3 only; manifest keeps T-178 `pending`), commit `b4265f2f`. Defect found by the plan review, not covered by that PASS: `load_bundle:203` joins `path / f.name` unconfined.
- **Missing on master (all of FB4 and FB5):** `Case` has `pinned` and `pinned_issue_id` (`schema/case.py`) but no `priority`; `ProjectStore.list_cases` has no priority argument; there is no proposal artifact; `stages/expand.py::expand` (`expand_flow:114`, `expand:133`) calls the provider for every applicable class with no approval step; callers are `cli.py::expand_cases`, `ui/routes_learn.py::generate_cases` and `stages/eval_compiler.py::compile_evals:104` (`expand_flow(flow, spec.project, provider, docs)`).
- **Built as uncommitted INPUT in `codex/t178-completion`** (manifest `.worktrees/codex-t178-completion/qa/manifests/t178-completion.md`; no checker verdict exists; its own evidence is maker evidence only: 194 affected tests passed, six source-bound fault controls RED then restored GREEN, scoped ruff clean). The pieces this brief takes from it:
  - `schema/case.py`: `CasePriority` literal p0-p3, default p2, pinned forces p0 at load, `with_fixed_step` keeps priority/pin/issue trace; a strict step-less `CaseProposal` (identity includes the exact spec snapshot, project, flow, class, title, rationale).
  - `store/project_store.py`: `list_cases(priorities=None)` (union pinned p0, dedup by id, default order unchanged), `stage_case_proposals`, `review_case_proposal` (needs human attribution; a HAPPY prune persists as proposed and clears prior approval), `list_case_proposals`, `preflight_case_proposals(spec, ids, flow_id)`.
  - `core/paths.py`: `ProjectPaths.case_proposals` (`case_proposals.jsonl`).
  - `stages/expand.py`: `propose_cases(spec)`, `_reviewed_batch`, `_expand_reviewed_flow`; `expand`/`expand_flow` take `store=` and `proposal_ids=` and refuse (`ValueError`) without saved approvals, before building any prompt.
  - `stages/failure_bundle.py` + `schema/failure_bundle.py`: the name and containment repair (`BundleFile.name` validator; resolved-path containment and `.partial` alias refusal before read).
  - `cli.py::expand_cases`: `--proposals`, repeatable `--approve ID`, `--prune ID`, `--by NAME` (CLI is the human review door, permitted by the contract no-fire list). `ui/routes_learn.py::generate_cases`: stages proposals and refuses with a themed page naming the CLI command when approval is missing. `ui/routes_runs.py::trigger_run`: repeatable `priority` query literal.
- **Known gap in the input the builder must close:** `stages/eval_compiler.py::compile_evals` still calls `expand_flow` with the old signature; with the new gate it would raise. It has no production caller today (only `tests/test_eval_compiler.py`), but it is real code and `grep -rn "expand_flow(" src` shows it. Thread `store` (and optional `proposal_ids`) through `compile_evals` as keyword arguments and update its tests to use an approved fixture store.
- **Deliberately NOT in this unit (differs from the codex input):** the run/report bundle wiring, `stages/run_case_pipeline.py`, `ui/run_execution.py`, `stages/report_export.py`, `ui/routes_report.py` (bundle persistence after a failing run, report links to the bundle id, `persist_failure_bundle`, `bundle_reference`, `failure_step`). That wiring already exists as a separate checked-PASS unit `wave/at787-bundle-wiring` (`bundle_if_failed`, manifest `qa/manifests/at787-bundle-wiring.md`, "Merge T-177 first, then this"). Building it again here would define "write a bundle after a failed run" in two places (core invariant: one concept, one place). FB1-FB5 in the contract do not require it. Do not port those hunks. Whether a report-link unit follows AT-787 is an owner decision (section 10).

## 5. Files the builder will touch (line counts on master `3a16616c`)

Product, all EXISTING, edited in place. Cap check: file <= 300 lines, function <= 50.

| # | Path | Lines now | Change | Cap note |
|---|---|---|---|---|
| 1 | `src/autotester/schema/case.py` | 177 | `CasePriority`, `Case.priority`, pinned->p0, `CaseProposal`, `with_fixed_step` | input reached 258, ok |
| 2 | `src/autotester/schema/failure_bundle.py` | 63 | `BundleFile.name` validator | input 73 |
| 3 | `src/autotester/stages/failure_bundle.py` | 209 | `load_bundle` containment | input 286, ok |
| 4 | `src/autotester/stages/expand.py` | 141 | `propose_cases`, approval gate on `expand`/`expand_flow` | input 175 |
| 5 | `src/autotester/store/project_store.py` | 299 | priority selection, proposal staging/review/preflight | **AT the cap.** Input stays at 299 only by compacting docstrings elsewhere in the file. |
| 6 | `src/autotester/core/paths.py` | 300 | `ProjectPaths.case_proposals` | **AT the cap.** Input stays at 300 only by shortening two docstrings. |
| 7 | `src/autotester/cli.py` | 295 | `expand_cases` flags and review path | **near cap**; input 292 by compacting docstrings. T-174 also edits this file (section 10). |
| 8 | `src/autotester/ui/routes_learn.py` | 300 | `generate_cases` stages and refuses | **AT the cap**; input 299 |
| 9 | `src/autotester/ui/routes_runs.py` | 204 | `trigger_run(priority=...)` | shared with T-202/T-203/T-204/T-205 (section 10) |
| 10 | `src/autotester/stages/eval_compiler.py` | 110 | thread `store` into `compile_evals` | not in the input; builder adds it |

Tests, all EXISTING, extended in place (no new test file; the pinned tests already live in `tests/test_pinned_regression.py` 146 lines and are re-run, not edited unless a signature changed):

| Path | Lines now |
|---|---|
| `tests/test_schema.py` | 153 |
| `tests/test_store.py` | 224 |
| `tests/test_expand.py` | 161 |
| `tests/test_expand_cli.py` | 218 |
| `tests/test_failure_bundle.py` | 230 |
| `tests/test_ui_learn.py` | 275 |
| `tests/test_ui_runs.py` | 250 |
| `tests/test_eval_compiler.py` | 178 (fixtures in `tests/eval_compiler_fixtures.py`, 95) |

- No new module. Reason: new modules are a human gate (D-072 item 2 does not list T-178; `qa/gates/new-module-authorization.md` answers AT-710 only). The input avoided one by compacting docstrings. The builder may compact a docstring only if one line plus the issue id (`AT-228`, `AT-239`, `AT-260`, `AT-264`, ...) still carries the rationale; if a cap cannot be met without deleting load-bearing rationale or a split is needed, STOP, write the exact file and function to the manifest, and report a gate. Do not create a file.
- Also expected in the same branch, not product code: `qa/manifests/t178-failure-bundle-fb4-fb5.md` (maker-owned) and `docs/MAP.md` regenerated with `uv run autotester map` as the LAST commit step (it is generated and conflicts in every branch).

## 6. Test scope (exact nodes; never a directory; no full suite)

Run only these, with `uv run pytest <path>::<node>`, no `-q` (pyproject addopts already sets it; AT-503):

- `tests/test_schema.py::test_case_priority_and_legacy_default_preserve_identity`, `::test_pinned_legacy_and_fixed_case_remain_p0_with_issue_trace`, `::test_case_proposal_rejects_steps_changed_identity_and_anonymous_review` (names from the input; keep or rename in place)
- `tests/test_store.py::test_priority_selection_adds_pinned_p0_once_and_preserves_default_order`, `::test_proposal_restage_preserves_only_exact_identity_and_content`
- `tests/test_pinned_regression.py` (whole file, 146 lines; it is the AT-585 guarantee, one file, not a directory)
- `tests/test_expand.py::test_five_nonhappy_proposals_prune_before_spend`, `::test_no_recorded_approval_or_missing_happy_spends_nothing`, `::test_all_flows_preflight_before_any_prompt_and_happy_prune_invalidates`, `::test_forged_or_stale_proposal_input_cannot_reach_provider`, `::test_expand_runs_all_flows_once_approved`, plus the existing nodes in that file `::test_happy_case_uses_the_flows_own_steps_verbatim`, `::test_model_declining_a_class_produces_no_case_for_it`, `::test_login_flow_produces_at_least_twelve_cases`
- `tests/test_expand_cli.py::test_cli_proposal_review_is_signed_and_pending_generation_spends_nothing`
- `tests/test_failure_bundle.py::test_bundle_manifest_rejects_nonlocal_names_before_read`, `::test_bundle_refuses_resolved_symlink_escape_before_read`, `::test_loader_refuses_real_directory_link_escape_before_hashing` (the junction test needs Windows; it must still prove the escaped-file hashing assertion, not setup) plus the existing FB1-FB3 nodes in the same file (run the file's FB1-FB3 nodes by name, the builder lists them with `--collect-only` on that single file)
- `tests/test_ui_learn.py::test_generate_stages_pending_without_implicit_happy_approval`
- `tests/test_ui_runs.py::test_trigger_runs_exact_selected_priority_plus_pinned_once`
- `tests/test_eval_compiler.py` (whole file, 178 lines, because the `compile_evals` signature changes; single file)
- Lint and doctor on the touched paths only: `uv run ruff check <the 10 product files and 8 test files>`, then `uv run autotester doctor` once at the end.
- The UI nodes use Starlette `TestClient`. On this Windows machine the input recorded a stall in the first `TestClient` node that was traced to native localhost socketpair IPC, not to the product (manifest "Subsequent measured runtime"). If a UI node hangs, do not weaken the guards; report it and ask the orchestrator to run that node under the ScopedWindows runner.

## 7. Reachable test cases per criterion (happy path first)

**FB4**
1. Happy: four fixture cases p0..p3; `list_cases(priorities=["p0"])` returns exactly the one p0 row, count asserted; through the real entry, `POST /projects/<slug>/run?priority=p0` (`trigger_run`) runs exactly that set, asserted on the saved `case_ids`.
2. Happy: no `priority` argument returns every case in the existing cheap-first order (RU3/F-058 intact).
3. Union: with a pinned case that is stored p1, selecting `p0` returns p0 rows plus the pinned one once; selecting `p1` also keeps the pinned p0 (assert both counts, deduplicated).
4. Legacy: a case JSON written without `priority` loads with `p2`; a legacy `pinned: true` case loads as `p0`.
5. Safety: `ProjectStore.delete_case` on a pinned case still refuses; `Case.with_fixed_step` keeps priority, `pinned` and `pinned_issue_id`.
6. Sabotage (isolated copy): make `list_cases` ignore `priorities` - the p0 count assertion goes red on the count, not on an import error.
7. Reject: `priority="p9"` is a validation error (`extra="forbid"`, literal set).

**FB5**
1. Happy: 5 non-happy proposals, happy approved, 2 approved and 3 pruned -> a counting fake `Provider.act` records exactly 2 calls and returns one verbatim happy case plus the two generated cases.
2. Prune all 5 -> exactly 0 provider calls (the happy case still comes from the approved happy proposal with no call).
3. No approval recorded -> zero cases persisted, zero calls, and `expand` raises/returns pending; same through `autotester expand <project>` (exit nonzero) and `POST /projects/<slug>/cases/generate` (themed refusal page naming `autotester expand <slug> --proposals`).
4. Review door: `autotester expand <project> --proposals` lists step-less proposals; `--approve ID --by NAME` records a signed approval; `--approve` without `--by`, or the same id both approved and pruned, is refused.
5. Boundaries: a stale proposal (FlowSpec edited after approval), a foreign-project proposal, and a hand-edited approval row each produce zero calls; the whole batch is validated before the first prompt is built (a bad row anywhere means no call for any flow).
6. Happy-prune: pruning the HAPPY proposal leaves that flow pending and generates nothing for it.
7. Bytes: inspect the staged `case_proposals.jsonl` - no `steps` key in any row.
8. Caller: `compile_evals(..., store=approved_store)` reaches `expand_flow` only for approved proposals; without a store it raises `ValueError` and spends 0 calls.
9. Sabotage (isolated copy): call the provider before the approval check - the pruned-proposals count goes red.

**Containment (FB1 amendment)**
1. Happy: a complete bundle still loads (existing FB1 test).
2. A manifest naming `../x`, an absolute path, `C:\x` or a backslash name is refused before any read or hash.
3. A name that resolves outside the bundle directory through a symlink or a Windows directory junction is refused before hashing; a resolved `.partial` alias is refused.
4. Sabotage (isolated copy): remove the resolved-containment check - the escaped-file test goes red on the hashing assertion.

## 8. Gate answers

Applicable `Answered:` lines (verbatim, with file):

- `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md:73`: `Answered: 2026-09-29 — A — "A: order only, never skip (Recommended)"; CT6 narrowed to ordering + reporting, RU3/F-058 intact, tiers_to_run() wired as ordering helper only; Umesh via AskUserQuestion in session autotesting-23, re-confirmed to the maker session; recorded as D-057`
- `qa/gates/t125-ct6-tiered-dispatch-vs-ru3.md:75`: `Answered: 2026-10-07T06:34:21Z — A — chat (Umesh): run every case, cheapest tier first, cheap failures surfaced at the top; never skip. RU3/F-058 intact.` (so priority selection is an opt-in filter on top of the default, never a replacement for it.)
- `qa/gates/write-policy-tier.md:4`: `**Answered by:** Umesh, 2026-09-27. Asked once; this file is the record so it is never asked again.` (not a blocker here; this unit adds no write-policy behaviour.)
- Authorization for the whole feature: D-041 (full T-178), D-081 (owner asked for all remaining work to run; queue row `t178-failure-bundle`, `approved: 2026-10-10`).
- New module: `none` is needed, and none is authorized. `qa/gates/new-module-authorization.md:77` reads `Answered: 2026-09-29 — A — "A: new ledger/citations.py (Recommended)", AT-710 only (standing-rule variant not chosen); Umesh via AskUserQuestion in session autotesting-23, re-confirmed to the maker session; recorded as D-057`. It covers AT-710 only, so the builder edits in place and stops at a cap (section 5).
- No T-178-specific gate exists in `qa/gates/` (checked by the plan, "No T178-specific Answered gate was found in public qa/gates").
- Choices the input made that are NOT owner-answered facts and need the checker to accept: default `p2` (plan review accepted it as a stated default); CLI-only human review door (contract no-fire list permits it). The plan review resolved the pin/union rule; it is not an `Answered:` line.

## 9. UI surface and persona walk

- `Persona walk: required (dev)` (`docs/plan.md` row 15: "required (dev)"; spec R24).
- Changed surfaces a person reaches: the Learn page "generate cases" action (`ui/routes_learn.py::generate_cases`) now stages proposals and, with no approval, shows a themed refusal naming the CLI command; the run trigger accepts `?priority=`. There is no in-UI approve/prune screen in this scope (CLI-only door, allowed by the contract no-fire list); the walk must confirm the refusal page is understandable and that the dev can complete review at the CLI and then generate. If the owner wants an in-UI approve/prune screen, that is a separate unit (section 10).
- The walk is the checker's, in a visible browser (browser lane max 1, `qa/adapter.json`). The builder runs no browser; `TestClient` route tests prove behaviour, not UX (the input's own manifest says so).

## 10. Dependencies and conflicts

- Must land first: nothing (queue row `t178-failure-bundle`: `after: none`; T-125 done).
- Parallel with: t177 plan review and t174 plan review (different files), AT-119 vocab, G10 briefs that do not touch the files below.
- Shared files and proposed ONE owner per file:

| File | Also touched by | Proposed owner (this unit?) | Rule |
|---|---|---|---|
| `store/project_store.py` | none pending | **T-178** (queue: "this row") | at the cap, no one else edits it meanwhile |
| `schema/case.py`, `stages/expand.py`, `schema/failure_bundle.py`, `stages/failure_bundle.py` | AT-787 touches `stages/failure_bundle.py` (adds `recorded_failing_step`, `bundle_if_failed`, file to 270 lines) | **T-178** for the `load_bundle` hunk; AT-787 for its own hunks | whoever lands second rebases; the two hunks are in different functions |
| `core/paths.py` | T-203, T-204, T-205 (G1) edit it | **T-178 lands the one `case_proposals` property**; the Group 10 rows keep their "owns until PASS" ordering for the rest | file is at 300: the second landing must free lines itself |
| `cli.py` | **T-174** (+2 lines), T-202 (`codex/t202-completion` edits `cli.py`) | **T-178** first (net -3 lines), then T-174, then T-202 | T-174 must land after T-178 |
| `ui/routes_learn.py` | **T-202** (`wave/t202-litellm`: provider factory), T-205 | T-178 and T-202 conflict textually in `generate_cases`; input notes T-202 requires its named-model/availability refusal (LL11) to run before proposal preflight is mentioned in a refusal | the second to land reconciles, keeping both refusals and the order "pure availability refusal first, then proposal refusal"; the T-178 builder must NOT change the credential/availability guard order |
| `ui/routes_runs.py` | T-203 (first, per queue), T-202, T-204, T-205 | T-203 first (queue line 40), T-178's 10-line `priority` hunk after; **T-178 owns only the `trigger_run` signature and `list_cases(priorities=...)` call** | land order: t203, then t178, then t205/t204 |
| `stages/eval_compiler.py` | none pending | T-178 | - |
| `docs/MAP.md` | every branch | the last commit of each unit; regenerated, never merged by hand | - |

- Not shared with T-178 and therefore safe to run in parallel with it: all of T-174's new files, T-177's `agent_*`, `browser_use_backend`, `schema/agent_fallback.py`, `pyproject.toml`, `uv.lock`.
- Not in this unit, owner decision: (a) landing `wave/at787-bundle-wiring` (needs `wave/t177-followup` or `wave/t177-agent-fallback` merged first); (b) a follow-up unit for report links to bundle ids (`report_export.py`, `routes_report.py`) with the `persist_failure_bundle`/`bundle_reference` input in `codex-t178-completion`; (c) an in-UI approve/prune screen.
- Stale doc: `docs/ARCHITECTURE.md` needs a `case_proposals` line; edit it only under an authorizing `docs/DECISIONS.md` entry written first (Lab Protocol), so leave it to the maker and record it in the manifest.

## 11. Budget and process rules

- Budget: **L, 45 minutes** of builder wall-clock. At the budget, stop and write the state to the manifest; do not extend silently.
- The builder runs only the nodes in section 6; no full suite (the maker runs the integration suite once, under the machine lock, after the checker is satisfied).
- Falsification (the sabotage steps above) happens only in a throwaway copy of the touched files, one named green / red / restored run per changed criterion; never mutate the working tree and never leave a mutant behind. A red that is an import or setup error does not count.
- Kill only PIDs the builder started itself, verified by identity before stopping them.
- No git write beyond the unit's own branch commits made by the maker flow: no force, no merge of codex branches, no `git stash`. Use `git -C D:/autoTesting ...`, never `cd X && ...`.
- Handshake is files: manifest `Status: ready-for-check`, `Fix cycle: N`, `Policy-Version: proportional-verification/2026-10-10.9`, `Tier: L`, `Dual check: required`, `dual-trigger: security src/autotester/stages/failure_bundle.py:203`; checker verdict at `qa/verdicts/t178-failure-bundle-fb4-fb5.md`. Maker never edits `qa/contracts/`.
- Secrets: no live credential, provider call or browser in the build. Tests use fakes; the scrub gate (`scripts/check_no_secrets.py`) must stay clean on any bundle directory a test writes.
- Input hashes to pin before use (from the input manifest; recheck, they are for the codex worktree and change if it is edited): `schema/case.py` `037582995036AB204FCCA47F7E7DF606FA319D039E53E00A279E3C5395B7C5AF`, `stages/expand.py` `6EDEF722C497508D690AB7AC01573B2C231FC2A4B4D7C31BAD1E7BAAF27CE875`, `store/project_store.py` `A71105B1683F09F39C36C2016A63D53228820029FB4FEE716876CF37CF62FA8D`, `stages/failure_bundle.py` `E1DE7A5C3480CA44F14F585C2D515621FF4ECD2F8D0A81D6B969109D1885B319`. The input's `stages/failure_bundle.py` also holds `persist_failure_bundle`, `failure_step`, `bundle_reference` (run/report wiring): take only the `load_bundle` containment hunk and the `BundleFile.name` validator.
