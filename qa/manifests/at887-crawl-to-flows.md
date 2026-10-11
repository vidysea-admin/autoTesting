# Manifest - at887-crawl-to-flows (AT-887 + AT-890, D-084 items 1 and 2)

Contract: qa/contracts/explore.md (X12, X13 as extended below); review-gate.md (R1, R2, R5(c)); expand.md (X1, X5, X6); core-invariants.md C2, C5
Issues: AT-887 (a crawl's screens never become flows or cases), AT-890 (expand prompt sent unmasked to a provider)
Authority: docs/DECISIONS.md D-084 item 1 (approved for build) and item 2 (for the student test account, cases come from the crawled screens). No new D-entry needed; no contract edited.
Status: ready-for-check
Fix cycle: 1
Repair base: 6d70c0ec
Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Base: master 3748cb83594c9b23310f50db0965ca0732e1258b, branch wave/at887-crawl-to-flows (worktree .worktrees/at887-crawl-to-flows)
Product commit: 54dced40 (cycle 1 repair; cycle 0 product commit was 75b23672fc547a7fb90ea89861abc0460dc1bce3). A manifest cannot name its own commit.
Executor: claude-sonnet-subagent (maker build subagent). Started about 2026-10-11T04:15Z; a 600 s stall of the run was resumed by the coordinator; ready 2026-10-11T07:05Z. Cycle 1 repair: claude-sonnet-subagent (maker builder), 2026-10-12.
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

- `src/autotester/stages/explore_flows.py` (92 lines). One job: derive reviewable `Flow` proposals from a crawl's discovery tree (docstring states it). Kept apart because folding screens into a spec and deriving paths from the screen graph are two jobs. (Cycle 0 claimed explore_merge.py sat at 298 of 300 lines; that was false, it was 178 at the base. Retracted; the split stands on the one-job reason.) `explore_merge.py` (now 226) holds `merge_screens_and_flows` and `merge_stored_crawl`.
- New test files (not product modules): `tests/test_explore_flows.py` (204 lines), `tests/test_explore_flows_doors.py` (98), `tests/test_expand_redaction.py` (146).
- No new schema model: `Flow`, `Step`, `SourceRef`, `ExpectedState` already fit.

## Files changed (lines after)

stages/expand.py 217 · stages/explore_merge.py 226 · stages/explore_flows.py 92 (new) · stages/orchestrate_runners.py 127 · cli_crawl.py 300 (was 300; a docstring was tightened to pay for the flow count in the echo line, cli.py untouched) · ui/routes_crawls.py 286 · docs/MAP.md and docs/SNAPSHOT.md regenerated (SNAPSHOT was already stale at the base).

Cycle 1 changed: stages/explore_merge.py 246 · stages/explore_flows.py 92 (docstring) · stages/expand.py 219 · ui/routes_learn.py 300 · tests/test_explore_flows.py 247 · tests/test_explore_flows_doors.py 151 · tests/test_expand_redaction.py 179 · tests/test_ui_learn_guard.py 57 (new test file; test_ui_learn.py was already at 299).

## Pre-checks (cycle 1; product sha 54dced40; every run `uv --directory D:/autoTesting/.worktrees/at887-crawl-to-flows run ...`, `autotester.__file__` confirmed inside the worktree; `-p no:xdist -o addopts=`; no full suite)

Pre-check[C5]: 54dced40 pytest tests/test_expand_redaction.py tests/test_ui_learn_guard.py -> 25 passed. Includes the phone-ordinal prompt test (full expected lines), the compile_evals provider spy (scrubbed prompt only) and the Generate-button guard refusal (400 themed page, 0 provider calls, 0 cases, neither the secret nor its base64 spelling in the page).
Pre-check[C2]: 54dced40 ruff check src tests scripts then autotester doctor then autotester map -> exit 0 (ruff all checks passed; doctor clean; docs/MAP.md unchanged). explore_merge.py 246, explore_flows.py 92, expand.py 219, routes_learn.py exactly 300 (was 300; one comment line folded into the `try:` line to pay for the message), cli_crawl.py untouched at 300.
Pre-check: 54dced40 [X13] pytest tests/test_explore_flows.py tests/test_explore_flows_doors.py -> 31 passed. New: rediscovered screen cited by the existing id with a stable flow id (model level and three doors, `dangling_references(spec) == []`), schema+flow merge bumps the version exactly once, flows-only merge is DRAFT with by/at empty.
Pre-check: 54dced40 [X12] same run as X13 -> 31 passed. New: a real 2-cycle (A to B to A) in the crawl graph yields no flow.
Pre-check: 54dced40 [X1] pytest tests/test_expand.py tests/test_expand_cli.py tests/test_eval_compiler.py -> passed within the 175-test affected group below.
Pre-check: 54dced40 [DOORS] pytest tests/test_explore_flows.py tests/test_explore_flows_doors.py tests/test_expand.py tests/test_expand_cli.py tests/test_expand_redaction.py tests/test_explore_merge.py tests/test_eval_compiler.py tests/test_ui_learn.py tests/test_ui_learn_guard.py tests/test_ui_crawls.py tests/test_orchestrate_runners.py tests/test_cli_orchestrate_resume.py tests/test_coverage_wiring.py tests/test_merge_flowspec.py -> 175 passed in 86.70s.
Pre-check: 54dced40 [ADVICE] pytest tests/test_cli_advice_resolves.py tests/test_redact_pii.py -> 165 passed in 23.29s (core/redact.py untouched).

## Falsification (throwaway copy of src/tests/scripts/docs/qa under the session scratchpad, PYTHONPATH at the copy, import path checked to be the copy; each green before, red after; copies deleted)

- Falsify[X13]: sabotage the `Review` reset (`"review": merged.review if True else Review(...)`) -> `test_merge_adds_flows_as_draft_and_never_approves` red. Green before: 17 passed. (t=36 s green, 70 s red)
- Falsify[X13b]: drop the skip-existing filter (`new = list(proposed)`) -> `test_merge_never_overwrites_a_reviewed_flow_and_re_arms_the_gate` and `test_remerging_the_same_crawl_changes_nothing` red (2 failed). Green before: 17 passed.
- Falsify[X12]: drop the input sort in `flows_from_crawl` (`by_node = {n.id: n for n in nodes}`) -> `test_same_crawl_same_proposals_whatever_the_storage_order` red. Green before: 17 passed.
- Falsify[SKIP]: `_CLICKED = set(Action)` -> the four `test_a_screen_reached_only_through_typed_input_gets_no_flow[...]` red. Green before: 17 passed.
- Falsify[C5]: remove the `guard_expand_prompt(...)` call before `provider.act` (line 183) -> 8 failed, including `undeclared-env-value`, `all-in-one`, both `test_both_entry_points_guard_the_prompt` and `test_an_encoded_secret_is_refused_before_any_model_call`. Green before: 21 passed.
- Falsify[PII]: remove `mask_pii` from the rendered steps -> 6 failed (`email-in-target`, `phone-in-value`, `bare-ten-digit-phone`, `test_without_a_saved_project_the_pii_mask_still_applies`, `test_build_expand_prompt_masks_pii_on_its_own`, ...). Green before: 21 passed.

Cycle 1 falsifications (throwaway copy of src, tests, scripts on C: under the session scratchpad `fz-at887-c1`, PYTHONPATH at the copy, import path checked to be the copy; each green before, red after; copy deleted):
- Falsify[X13c] item 1: drop the alias rewrite (`proposed = [f for f in flows_from_crawl(...)]`) -> 4 failed: `test_a_rediscovered_screen_is_referenced_by_the_existing_id_and_the_flow_id_is_stable`, the CLI and UI door tests, `test_a_rediscovery_changes_the_screen_reference_not_the_flow_id`. Green before: 31 passed.
- Falsify[X6] item 2: narrow the `except` back to `ProviderError` -> `test_a_guard_refusal_is_a_themed_400_with_nothing_written_sent_or_echoed` red (the raw ValueError escapes the route). Green before: 1 passed.
- Falsify[PII2] item 3: mask the joined steps text again -> `test_a_phone_at_the_end_of_a_step_does_not_swallow_the_next_step_number` red (steps 2 and 3 fused). Green before: 23 passed.

Metrics: suite_runs=0 mutations=9 cycle=1

## Cycle 1 repairs (verdicts at qa/verdicts/at887-crawl-to-flows.a.md and .b.md, both FAIL at cycle 0)

1. Dangling screen ids (A:B7/P1, B:P1). `stages/explore_merge.py::_rediscovered_ids` maps each crawl node that `merge_screens` skips as a rediscovery (`_is_rediscovery`, same test) to the existing screen's id; `merge_screens_and_flows` rewrites the proposed flows with the repo's own `screen_identity.rewrite_screen_refs`. The flow id is computed in `explore_flows` from the crawl node ids before the rewrite, so it is stable across re-crawls and identical for flows with no rediscovery (both asserted). Orchestrated door: DISCOVER merges with no spec (nothing to rediscover); the MODEL fold adds the node-id screens, so no dangling there either (asserted, as it passes before and after).
2. Guard refusal = HTTP 500 (A:P2, B:P3). `ui/routes_learn.py::generate_cases`: `except (ProviderError, ValueError)`; a ValueError shows a fixed line ("a prompt was refused unsent"), never the exception text, so no secret or prompt text is echoed. The file stays at 300 lines.
3. Phone swallows the next ordinal (B:P2). `stages/expand.py::build_expand_prompt` masks each step line separately, then joins; the flow name was already masked separately. `core/redact.py` untouched.
4. Missing tests added: version bumped once for screens+flows; flows-only merge is DRAFT; a real cycle yields no flow; `compile_evals` provider spy.
5. Docstring in `explore_flows.py` fixed; the false "298 of 300" claim retracted above.

## Merge notes

- `ui/routes_learn.py::generate_cases` is also edited by branch t202 (litellm provider). This unit's hunk is the `try:`/`except` header and the message of the `except` (4 changed lines, net 0). Merge by keeping t202's provider construction and this `except (ProviderError, ValueError)` clause; re-run `tests/test_ui_learn_guard.py` after the merge.

## Open (not built in this unit, by instruction)

- AT-887 clause 2: the pre-run reachability warning for cases whose first target is absent from the crawled screens.
- URL-encoded email (`%40`) is not masked by `mask_pii`.
- A per-use provider approval for `expand`.
- No saved project means no `.env` scrub (library callers only; every real caller passes a store with a project).
- `Flow.kind` for crawl flows is unchanged (None).
- A pruned crawl flow returns on the next merge (no tombstone); the contract lines for crawl flows, PII masking and the prompt guard belong to the checker.

## HUMAN_GATE questions (for Umesh)

1. Should crawl-derived flows be `kind="ideal", ideal_basis="crawl"` (generation allowed from DRAFT once review-gate R5 lands) or stay `kind=None` (always need a human approve or reconcile)?
2. Should `expand` need a per-use approval before a masked prompt goes to an external provider?

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
