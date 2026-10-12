# AT-887 / AT-890 falsification floor (checker A, tree 6d70c0ec, 2026-10-11)

Method: per row a copy of src/ tests/ scripts/ docs/ pyproject.toml on C: (not D:), run with the
check tree's venv python and PYTHONPATH=<copy>/src (confirmed `autotester.__file__` inside the copy),
`pytest -p no:xdist -p no:cacheprovider -o addopts=`. One single-hunk mutant per copy, copy deleted after.
T=tests/test_expand_redaction.py (E) / test_explore_flows.py (F) / test_explore_flows_doors.py (D).

| Row | Mutant | Nodes | Green | After mutant |
|---|---|---|---|---|
| R1 | `guard_expand_prompt` returns prompt unchanged | E::test_the_provider_never_receives_the_raw_value, E::test_both_entry_points_guard_the_prompt, E::test_an_encoded_secret_is_refused_before_any_model_call | 13 passed | RED: `[declared-in-value]` `assert all(raw not in p ...)` |
| R2 | no mask_pii on steps_text | E::..raw_value, E::test_build_expand_prompt_masks_pii_on_its_own, E::test_without_a_saved_project_the_pii_mask_still_applies | 12 passed | RED: `raw_value[email-in-value]` assert all(raw not in p) |
| R2b | no mask_pii on flow.name only | same as R2 | 12 passed | RED: `raw_value[email-in-flow-name]` |
| R3 | `_store_secrets` returns None | E::..raw_value, E::test_both_entry_points_guard_the_prompt, E::test_an_encoded_...before_any_model_call | 13 passed | RED (no -x): raw_value[declared-in-value/target/name, undeclared-env-value, all-in-one], both_entry_points[expand_flow] AND [expand] |
| R4 | drop sorted() on nodes and edges (both lines) | F::test_same_crawl_same_proposals_whatever_the_storage_order, F::test_one_flow_per_leaf_path_from_the_landing_screen | 2 passed | RED: storage_order test, list-of-flows equality diff at index 0 |
| R5 | `new = list(proposed)` | F::test_merge_never_overwrites_a_reviewed_flow_and_re_arms_the_gate, F::test_remerging_the_same_crawl_changes_nothing, F::test_ids_are_the_path_not_the_crawl_so_a_re_crawl_adds_nothing | 3 passed | RED: never_overwrites `assert 4 == 3` (len(merged.flows)) |
| R6 | `"review": merged.review` instead of Review(DRAFT, note) | F::test_merge_adds_flows_as_draft_and_never_approves, F::test_merge_never_overwrites_..._re_arms_the_gate (+ whole F and explore_merge file, 33 tests) | 2 / 33 passed | RED only on merge_adds_flows_as_draft: `'2 flow(s)' in review.note` (note text). The status assertions do NOT go red: re_arms_the_gate and the version-once test still PASS, because merge_screens already left the spec DRAFT. A keep-old-APPROVED status is not killed by a status assertion in these fixtures. |
| R7 | `_CLICKED = set(Action)` | F::test_a_screen_reached_only_through_typed_input_gets_no_flow, F::test_a_link_edge_is_replayed_as_a_click_never_a_goto | 5 passed | RED: `typed_input...[fill]` `['node_048e..','node_9333..'] == ['node_048e..']` |
| R8 | remove `edge.outcome is not NAVIGATED` clause | F::test_orphans_cycles_and_unnavigated_discoveries_are_skipped_not_guessed | 1 passed | RED: `['node_5a2b..'] == ['node_34cb..']` (errored screen got a flow) |
| R9 | remove `parent in path or ` | F::test_orphans_cycles_and_unnavigated_discoveries_are_skipped_not_guessed (120 s timeout) | 1 passed | SURVIVED (1 passed, no hang). That test, despite its name, builds no cycle (an orphan with a missing edge and an ERRORED edge only); no test in the six files mentions or builds a real cycle. Likely also redundant with the `len(chain) >= _MAX_PATH` bound (not probed). |
| R10 | UI merge_crawl -> merge_screens | D::test_the_ui_button_proposes_flows_and_never_approves | 1 passed | RED: `assert (0 == 1)` len(flows) |
| R11 | CLI `_merge_into_flowspec` -> merge_screens | D::test_the_cli_door_proposes_flows_and_says_so | 1 passed | RED: `assert (0 == 1)` len(flows) |
| R12 | DISCOVER runner -> merge_screens(None, nodes, slug, crawl_id=) | D::test_orchestrated_discover_parks_flow_proposals_in_its_draft | 1 passed | RED: `0 == 1` len(flows) |
| R13 | `"version": merged.version + 1` always | F::test_flows_for_screens_the_spec_already_knows_still_bump_the_version_once, F::test_merge_adds_flows_as_draft_and_never_approves, F::test_remerging_the_same_crawl_changes_nothing; then all six files (58 tests) | 3 / 58 passed | SURVIVED both runs. No test asserts the version of a merge that adds NEW screens AND new flows (that case must bump once, the mutant bumps twice). |

Verdict summary: 11 of 13 killed; 2 SURVIVED (R9 cycle guard, R13 double version bump), 1 weak (R6: killed by note text only,
status reset unproven). All copies under fal-887a/<row> were deleted (`Remove-Item`-equivalent shutil.rmtree, verified: none remain).
