# Verdict - t166-eval-compiler (cycle 0)

Cycle checked: 0
Checked commit b2c1f7cf on wave/t166-eval-compiler (merged with origin/master). Policy-Version: proportional-verification/2026-10-07.7. Tier M, single checker, no full suite.

## Verdict: PASS

EC1-EC5 are met. Three non-blocking findings are filed as AT-821..AT-823. One test failure in the affected set is pre-existing on master (below).

## Check plan

1. Diff vs the merge base (new: schema/scenario.py, stages/knowledge_graph.py, stages/eval_compiler.py; edit: schema/portal_persona.py).
2. Back-compat of a persona saved before the change under `extra="forbid"`.
3. Design rules: 300-line cap, one concept one place, expand.py / reconcile.py unchanged, expand_flow reused.
4. Merge origin/master, affected tests (one pytest process, `-p no:xdist`), ruff, doctor.
5. At least one falsification per EC in a throwaway copy, re-run by me.
6. Whether any EC requires the unwired rollup or the missing scenario loader.

## Evidence

**Merge.** `git merge origin/master` conflicted only in docs/SNAPSHOT.md (a generated file). I took master's copy, then `uv run autotester snapshot` produced no diff. No other conflict. A second merge of origin/master afterwards was clean (issues.jsonl only).

**Design rules (check 3).** portal_persona.py 299 lines, scenario.py 80, eval_compiler.py 110, knowledge_graph.py 131. `git diff origin/master HEAD -- stages/expand.py stages/reconcile.py` is empty. `compile_evals` imports and calls `stages.expand.expand_flow` (eval_compiler.py:21,104), no copy of it. `grep -rn "class.*Graph" src/autotester/schema/` gives only portal_persona.py:207,221,232 (GraphNode, GraphEdge, KnowledgeGraph). `grep -rniE "neo4j|networkx|graph[_-]?db" pyproject.toml src/` returns nothing.

**Back-compat (check 2).** No persona JSON is committed or on disk in any project dir, so I made one. With the pre-change schema (asserted: `GraphNode` absent from the module) I built a PortalPersona with 2 screens and 1 transition, dumped it (no `graph` key), and loaded it with the t166 code under `extra="forbid"`: `LOADED 2 screens; graph nodes: 0`. Also `test_a_persona_written_before_the_graph_existed_still_loads` passes.

**Tests (check 4).** One pytest process, `-p no:xdist`: test_knowledge_graph, test_eval_compiler plus every test file importing portal_persona or `autotester.schema` (test_catalog, test_explore_completeness, test_explore_traversal, test_goal_contract_registration, test_persona_changes, test_persona_diff_pipeline, test_portal_persona, test_schema): `1 failed, 138 passed in 542.80s`. The failure is `test_goal_contract_registration.py::test_revised_goal_contract_is_registered`, last assert: `.goal/dashboard.html` says 63/92 tasks while goal.json says done=65. `git diff origin/master HEAD -- .goal` is empty, so this is identical on master and not caused by T-166 (the dashboard is stale on master). Not filed as a T-166 defect. `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: doctor: clean (before this commit's goal edits). The two new test files are re-run after the final merge below.

**Falsification (check 5).** Throwaway copy at the scratchpad (`fals/`), PYTHONPATH on the copy, baseline `33 passed`. I re-ran these myself:

| EC | falsifying edit (copy only) | observed |
|---|---|---|
| EC1 | add `class ShadowGraph(BaseModel)` in schema/shadow.py | `FAILED test_one_graph_model_lives_in_the_persona_family` (hits = persona + shadow), 1 failed 32 passed |
| EC2 | delete the `traces_to` edge line in `add_case` | `test_every_compiled_case_resolves_a_trace...` fails (IndexError on the empty trace), plus the model-proposed-class test and two EC4/EC5 tests |
| EC3 | `rollup_workflow` = AND of components | `assert PASS is FAIL` at test_eval_compiler.py:96 (false PASS reproduced), plus the missing-e2e test and truth-table rows |
| EC4 | edge scenario cases to the flow node, not the scenario node | `FAILED test_two_declared_variants_make_two_scenario_nodes_with_their_own_cases`, `FAILED test_exactly_the_uncompilable_branch...`; 2 failed 31 passed |
| EC5 | replace the `uncovered += _uncover(...)` line with `pass` | `assert [] == [('s_browse','no')]` (the missing branch, not an import error), 1 failed 32 passed |

EC2 pre-call guard: `test_an_untraceable_flow_spends_no_model_call` asserts `prov.prompts == []`; the code skips an untraced flow before `expand_flow` (eval_compiler.py:100-103).

**Per criterion.**
- EC1 PASS: persona-family extension, JSON on the filestore (`test_the_graph_round_trips_through_the_persona_file`), no graph DB, node kinds screen/control/flow/scenario/case/verdict/api/release all in `NodeKind`.
- EC2 PASS: a case enters the result only if `add_case` resolves a flow that `visits` a real screen; trace is read back from the persisted persona file.
- EC3 PASS at the criterion's own verify level (fixture: all components PASS, e2e FAIL gives FAIL; e2e missing/BLOCKED gives INCONCLUSIVE).
- EC4 PASS: 2 variants give 2 scenario nodes, each with 2 own cases and no overlap.
- EC5 PASS: 3 scenarios x yes/no, one uncompilable: `uncovered == [("s_browse","no")]`, coverage 5/6.

## Product claims (check 6)

The builder admits `rollup_workflow` has no feed of real verdicts, and that `compile_evals` has no scenario-list loader or UI. I read EC1-EC5 for both. EC3 asks that "an aggregate or summary view must not report PASS" but its Verify is a fixture workflow and "the compiled top-level verdict", the contract names no surface, and it says nothing of the sabotage reaching a report. EC5 verifies on a fixture list passed to the compiler. No criterion requires a loader or UI. So neither is a FAIL. Filed instead: AT-821 (rollup unwired), AT-822 (no loader, no caller, graph never built into real personas), AT-823 (duplicate scenario ids fold into one node; reproduced: nodes `['scenario:s']`, 3 cases).

## Issues filed

AT-821 (low, gap), AT-822 (low, gap), AT-823 (low, bug). Ids chosen after fetching origin/master (highest AT-820); the coordinator reserved AT-810/811 for an unpushed branch.

Metrics: suite_runs=0 repeat_runs=0 falsifications=5 cycle=0 resumes=0 checkers=1 pytest_wall=543s policy=proportional-verification/2026-10-07.7
