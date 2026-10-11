# Falsification, coordinator A, a7d3fa6c (each mutant in its own copy; green before, red after, restored)
Runner: falsify-runner.py (one pytest process at a time, `-p no:xdist`, copy of `git archive a7d3fa6c`).
| id | mutation | node | before | after (assertion) |
|---|---|---|---|---|
| FB4 | `store/project_store.py list_cases`: `if priorities is None:` -> `if True:` (selection ignores priority) | tests/test_store.py::test_priority_selection_adds_pinned_p0_once_and_preserves_default_order | 1 passed | red: list equality `Left contains 3 more items` |
| FB5 | `schema/case.py approved_batch`: `[p for p in batch if p.status == "approved"]` -> `[p for p in batch]` (pruned proposals reach provider) | tests/test_expand.py::test_five_nonhappy_proposals_prune_before_spend | 2 passed | red: `assert 5 == 2` and `assert 5 == 0` |
| CONTAIN | `stages/failure_bundle.py`: containment `is_relative_to(root)` check removed | tests/test_failure_bundle.py::test_loader_refuses_real_directory_link_escape_before_hashing | 1 passed | red: `escaped file reached hashing/read` |
| QUEUE | `ui/routes_runs.py _run_queued`: `_prepare_run(entry.project, entry.priorities)` -> `_prepare_run(entry.project)` (filter dropped between submit and execution) | tests/test_ui_runs.py::test_trigger_runs_exact_selected_priority_plus_pinned_once | 2 passed | red: selected-set equality, `Left contains 2 more items` |
Extra FB4 probe (fb4-legacy-queue-probe.py): case JSON without priority -> p2; legacy pinned stored p3 -> p0; priority p9 and unknown key rejected; delete_case on a pinned case raises PinnedCaseError; an old run_queue.json row without `priorities` loads (None = every case); a queue priority outside p0-p3 is rejected.
