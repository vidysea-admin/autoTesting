# Manifest - at887-crawl-to-flows (AT-887 + AT-890, D-084 items 1 and 2)

Contract: qa/contracts/explore.md (X12, X13 as extended below); review-gate.md (R1, R2, R5(c)); expand.md (X1, X5, X6); core-invariants.md C2, C5
Issues: AT-887 (a crawl's screens never become flows or cases), AT-890 (expand prompt sent unmasked to a provider)
Authority: docs/DECISIONS.md D-084 item 1 (approved for build) and item 2 (for the student test account, cases come from the crawled screens). No new D-entry needed; no contract edited.
Status: ready-for-check
Fix cycle: 0
Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Base: master 3748cb83594c9b23310f50db0965ca0732e1258b, branch wave/at887-crawl-to-flows (worktree .worktrees/at887-crawl-to-flows)
Product commit: 75b23672fc547a7fb90ea89861abc0460dc1bce3 (a manifest cannot name its own commit)
Executor: claude-sonnet-subagent (maker build subagent). Started about 2026-10-11T04:15Z; a 600 s stall of the run was resumed by the coordinator; ready 2026-10-11T07:05Z.
Dual check: required
dual-trigger: security src/autotester/stages/expand.py:183
Dual trigger reason: line 183 is the new redaction call (`guard_expand_prompt`: `Redactor.scrub` then `SecretStore.guard_prompt`) immediately before `provider.act` in `_expand_reviewed_flow`; it is the gate that keeps credentials out of an external model call.

## Criteria served (quoted from the contracts; none edited)

- explore.md X12: "`run_crawl` takes no provider at all. No stop condition, no action choice, and no safety decision depends on model output". Served by extension: the transformation crawl -> Flow is a pure function (no provider, clock or randomness).
- explore.md X13: "`merge_screens` **never rewrites an existing `Screen`** ... When the merge adds anything, the spec's `Review` is reset to `DRAFT` and `version` is bumped ... When it adds nothing the spec is returned untouched: re-merging the same crawl produces no version bump, no second review reset ... and the persisted `flowspec.json` is byte-identical." and "sabotage the `Review(...)` reset - at least one test must fail." Served for flows by `merge_screens_and_flows`.
- review-gate.md R5(c): "No stage approves on a human's behalf and no stage waits for approval." Crawl flows land in a DRAFT spec with `review.by` None; nothing here calls `approve`.
- expand.md X1: "`expand` applies the review gate first ... A spec the gate still blocks raises `FlowSpecNotReviewed` before any provider call is made." Unchanged; tested on a crawl-derived spec.
- expand.md X2/X6 (door): the happy case is the flow's own steps verbatim, and `expand` is reachable from `autotester expand` and the Generate button; now it has crawl-derived flows to work on.
- expand.md X5: the prompt "leave[s] a genuinely-needed real credential's `{{SECRET:KEY}}` placeholder untouched". Now also enforced in code for the placeholder path (test `test_a_secret_placeholder_survives_untouched`).
- core-invariants C5: "Prompts and stored steps carry `{{SECRET:KEY}}` placeholders" and "Everything in that file is masked from logs, prompts, and artifacts, declared or not."
- core-invariants C2: "File <= 300 lines, function <= 50 lines" (cli_crawl.py is at exactly 300).

## Design note (written before the code, followed)

1. A crawl is a discovery tree: one landing screen, every other `ScreenNode` has `discovered_by` = the `ScreenEdge` that first reached it. Each LEAF of that tree is one replayable journey, so the producer emits ONE `Flow` per leaf (not per screen: a prefix screen is already a step of its leaf's flow, with its own `expected.url`).
2. Steps: step 1 `NAVIGATE` to the landing screen's `url_example`; each later step is a `CLICK` on the discovering edge's locator target. The crawl records a link as `Action.NAVIGATE` with a LOCATOR target and clicks it; `execute` would `goto()` that locator, so every edge is replayed as `CLICK`. A path through a typed or non-click edge (FILL/SELECT/BACK/HOVER..., which store no value), a failed discovery, a missing edge or a cycle is not replayable and is skipped, never guessed (the screen itself is still merged by `merge_screens`).
3. `expected` asserts only what the crawl knows: the URL path (substring, as `browser/assertions.py` compares) when a click changed it. No visible_text or absent_text is invented.
4. Provenance: every `Step.source_ref = SourceRef(source_id=<crawl id>, locator=<edge id | url>)` and a note "crawl-derived, not human-reviewed"; `Flow.source_id` therefore reads the crawl id; the flow name starts "crawl path:"; `spec.source_ids` gains the crawl id. `Flow.kind`/`ideal_basis` stay None (reconcile's fields, never set here). `requires_auth` and a precondition name the crawl's login case.
5. Identity: `Flow.id = content_id("flow", {node ids along the path, edge targets})` - the path, not the crawl - so the same path found by a later crawl is the same flow and is not duplicated; the same crawl always gives the same rows (inputs are sorted; pinned by a shuffle test).
6. Review: no new gate. `merge_screens_and_flows` calls `merge_screens` then appends flows whose id the spec does not already hold (an existing flow, reviewed or edited, is never replaced), resets `Review` to DRAFT (by/at empty) and bumps the version once; nothing new -> the same spec object back. The existing `autotester flowspec approve` then `expand --proposals --approve` steps (t178 `stage_and_review`) are the human steps; `expand` itself is unchanged apart from AT-890.
7. Wiring ("existing seam"): the three doors that already called `merge_screens` - `cli_crawl._merge_into_flowspec`, `ui/routes_crawls.py::merge_crawl` (the button) and `orchestrate_runners.make_discover_runner` - now call `merge_stored_crawl` / `merge_screens_and_flows`, so none can skip the flows.
8. AT-890: `build_expand_prompt` masks emails and phones (`core.redact.mask_pii`) in the flow name and the rendered steps; `guard_expand_prompt` (Redactor.scrub of every `.env` value, declared or not, then `SecretStore.guard_prompt`, which also refuses folded/encoded spellings) runs on the finished prompt right before `provider.act`. `expand`/`expand_flow` take an optional `secrets=` and otherwise build the store from the saved project like `ux_advisory` and `ingest` do, so all three callers (CLI, UI button, `eval_compiler`) are covered with no signature change on their side.

## New modules (D-082 item 1)

- `src/autotester/stages/explore_flows.py` (92 lines). One job: derive reviewable `Flow` proposals from a crawl's discovery tree (docstring states it). Needed because `stages/explore_merge.py` sat at 298 of 300 lines; the new function is the path derivation, kept apart from the screen merge. `explore_merge.py` (now 226) holds `merge_screens_and_flows` and `merge_stored_crawl`.
- New test files (not product modules): `tests/test_explore_flows.py` (204 lines), `tests/test_explore_flows_doors.py` (98), `tests/test_expand_redaction.py` (146).
- No new schema model: `Flow`, `Step`, `SourceRef`, `ExpectedState` already fit.

## Files changed (lines after)

stages/expand.py 217 · stages/explore_merge.py 226 · stages/explore_flows.py 92 (new) · stages/orchestrate_runners.py 127 · cli_crawl.py 300 (was 300; a docstring was tightened to pay for the flow count in the echo line, cli.py untouched) · ui/routes_crawls.py 286 · docs/MAP.md and docs/SNAPSHOT.md regenerated (SNAPSHOT was already stale at the base).

## Pre-checks (final sha 75b23672; every run `uv --directory D:/autoTesting/.worktrees/at887-crawl-to-flows run ...`, pytest rootdir confirmed to be the worktree; `-p no:xdist -o addopts=`; no full suite)

Pre-check[C5]: 75b23672 uv --directory <worktree> run pytest -p no:xdist -o addopts= tests/test_expand_redaction.py -> 21 passed in 154.12s (6 processes in parallel on a loaded machine; 27 s when alone). Provider spy: declared secret / undeclared .env value / email / phone, each in value, target and flow name; placeholder survives; unrendered nested fields (note, narration, on_screen_text, expected) never reach the prompt; a base64-encoded secret is refused before any call.
Pre-check[C2]: 75b23672 uv --directory <worktree> run ruff check src tests scripts, then autotester doctor, then autotester map -> exit 0 (All checks passed!; doctor: clean; map regenerated, committed; every touched file <= 300 lines, cli_crawl.py exactly 300)
Pre-check[X13]: 75b23672 uv --directory <worktree> run pytest -p no:xdist -o addopts= tests/test_explore_flows.py tests/test_explore_flows_doors.py -> 23 passed in 51.87s (never overwrites a reviewed flow, DRAFT reset, no-op re-merge incl. persisted file byte-identical, three doors)
Pre-check[X12]: 75b23672 same command as X13 -> 23 passed (same run; determinism under shuffled input, id is the path not the crawl, typed/failed/orphan/cyclic paths skipped, no provider in the module)
Pre-check[X1]: 75b23672 uv --directory <worktree> run pytest -p no:xdist -o addopts= tests/test_expand.py tests/test_expand_cli.py tests/test_eval_compiler.py -> 48 passed in 211.51s (existing expand behaviour unchanged by the masking)
Pre-check[DOORS]: 75b23672 uv --directory <worktree> run pytest -p no:xdist -o addopts= tests/test_explore_merge.py tests/test_orchestrate_runners.py tests/test_cli_orchestrate_resume.py -> 23 passed in 56.15s; and tests/test_ui_learn.py tests/test_ui_crawls.py -> 29 passed in 68.66s; and tests/test_coverage_wiring.py -> 8 passed in 14.36s
Pre-check[ADVICE]: 75b23672 uv --directory <worktree> run pytest -p no:xdist -o addopts= tests/test_cli_advice_resolves.py -> 32 passed in 104.39s
Pre-check[PII]: 75b23672 uv --directory <worktree> run pytest -p no:xdist -o addopts= tests/test_redact_pii.py -> 133 passed in 7.86s (run alone). In the first six-process parallel run, 3 wall-clock-bound `test_mask_pii_is_linear_on_adversarial_input` cases (dashed, many_at, parens) exceeded their 1 s budget on a loaded machine; `core/redact.py` is untouched by this unit and they pass alone.

## Falsification (throwaway copy of src/tests/scripts/docs/qa under the session scratchpad, PYTHONPATH at the copy, import path checked to be the copy; each green before, red after; copies deleted)

- Falsify[X13]: sabotage the `Review` reset (`"review": merged.review if True else Review(...)`) -> `test_merge_adds_flows_as_draft_and_never_approves` red. Green before: 17 passed. (t=36 s green, 70 s red)
- Falsify[X13b]: drop the skip-existing filter (`new = list(proposed)`) -> `test_merge_never_overwrites_a_reviewed_flow_and_re_arms_the_gate` and `test_remerging_the_same_crawl_changes_nothing` red (2 failed). Green before: 17 passed.
- Falsify[X12]: drop the input sort in `flows_from_crawl` (`by_node = {n.id: n for n in nodes}`) -> `test_same_crawl_same_proposals_whatever_the_storage_order` red. Green before: 17 passed.
- Falsify[SKIP]: `_CLICKED = set(Action)` -> the four `test_a_screen_reached_only_through_typed_input_gets_no_flow[...]` red. Green before: 17 passed.
- Falsify[C5]: remove the `guard_expand_prompt(...)` call before `provider.act` (line 183) -> 8 failed, including `undeclared-env-value`, `all-in-one`, both `test_both_entry_points_guard_the_prompt` and `test_an_encoded_secret_is_refused_before_any_model_call`. Green before: 21 passed.
- Falsify[PII]: remove `mask_pii` from the rendered steps -> 6 failed (`email-in-target`, `phone-in-value`, `bare-ten-digit-phone`, `test_without_a_saved_project_the_pii_mask_still_applies`, `test_build_expand_prompt_masks_pii_on_its_own`, ...). Green before: 21 passed.

Metrics: suite_runs=0 mutations=6 cycle=0

## Contract gaps (for the checker; nothing decided silently, no contract touched)

1. No criterion governs crawl-derived flows. explore.md's no-fire list still says "merging crawl-discovered *flows* (only screens are merged)" and X13 names only `merge_screens`. Provenance, one-flow-per-leaf, typed-edge skipping and the `crawl path:` naming are this builder's design (see design note) and need a criterion or an owner veto.
2. review-gate R5(b)/(a): "reconciled" means every flow has `kind` set. Crawl flows keep `kind=None` (I did not claim `ideal`/`ideal_basis="crawl"`, which reconcile assigns). Today `require_reviewed` is unconditional, so this changes nothing; once R5 lands a crawl-flow spec would count as UNRECONCILED and block until a human approves or reconcile runs. Owner question: should crawl flows be `kind="ideal", ideal_basis="crawl"` (generate from DRAFT) or stay unreconciled (always need a human)?
3. Review is spec-level only. Adding crawl flows to an APPROVED spec resets the whole spec to DRAFT (same as `merge_screens` does for screens), so human-reviewed flows lose their approval until re-approved. No per-flow status exists; no contract says which is right.
4. PII masking has no governing criterion: C5 covers `.env` secrets; emails/phones in prompts are covered only for reconcile (AT-780). Person NAMES (`mask_name_value`) are NOT masked in expand prompts (not asked for, and masking them would blank useful values).
5. Consequence of masking: the model sees `<email>`, `<phone>`, `[REDACTED]:KEY`, so a non-happy case it writes can carry the mask text in a step value instead of the original. The HAPPY case keeps the real steps (tested).
6. With no saved project (`store.load_project()` is None) there is no declared secret set to guard; only the PII mask applies (tested). expand.md X5 says the secret rule is prompt-level only; the code gate is new and not in any criterion.
7. AT-887's second `expected` clause (a pre-run reachability warning listing cases whose first target is absent from the crawled screens) is NOT built; out of this brief. AT-887 and AT-890 stay open until the checker decides whether the producer alone closes AT-887.
8. Volume: a crawl of 73 screens with 56 leaves gives 56 flows and, at ~14 classes each, hundreds of proposals for a human to prune; there is no cap by design (the t178 prune step is the control). Not run against the real Pathlynks crawl (instructed).
9. `expected.url` is a concrete example path from one crawl (e.g. a record id). It is correct for the same account and surface; on a different account a path with an id would be unmet. Only changed paths are asserted.
10. `eval_compiler.compile_evals` is covered through `expand_flow`'s default store-derived secrets and its existing 48-test group; there is no dedicated provider-spy test on that door.
11. The review-agent step of the lifecycle (senior-software-engineer on code written) was not dispatched by this builder; the dual check is the independent review.

## Open owner questions

- Gap 2 (crawl flows `kind`) and gap 3 (should adding crawl flows demote an APPROVED spec).
- Whether the student account's crawl should be re-merged now (`autotester explore ... merge` or the Merge button) - not done here; no real crawl or run was touched.
