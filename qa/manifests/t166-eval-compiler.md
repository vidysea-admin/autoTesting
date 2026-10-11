# Manifest — T-166 eval compiler + JSON knowledge graph

Contract: qa/contracts/eval-compiler.md EC1-EC5 (DRAFT; goes ACTIVE on first PASS); core invariants C1, C2, C3, C5.
Goal task: T-166 (done_check `uv run pytest tests/test_eval_compiler.py`, exit 0)
Policy-Version: proportional-verification/2026-10-07.7
Fix cycle: 0
Phase: CHECKED
Status: checked-PASS
Tier: M — new multi-file feature (1 schema edit, 1 schema file, 2 stages) with five contract criteria; no UI, no live browser, no provider spend, no enforcement-path file. Not L: no security boundary or authority claim.
Dual check: not requested by the maker.
Base: c93e6330 (integrate/t125), branch `wave/t166-eval-compiler`, worktree `D:/autoTesting/.worktrees/t166`. Not pushed.
Audience: internal developer/operator code; no new UI or portal behaviour.
Metrics: suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=0 policy=proportional-verification/2026-10-07.7

## Criteria (verbatim from qa/contracts/eval-compiler.md)

### EC1 — The knowledge graph is the existing persona graph EXTENDED, never a second schema [D-041 verbatim]

`schema/portal_persona.py`'s `PersonaScreen` / `PersonaTransition` family gains typed nodes and edges
for screen, control, flow, scenario, case, verdict, API and release. It stays **JSON on the
filestore** (D-002). **No graph database. No GraphRAG.** Both are explicitly rejected by D-041.

Same C3 "one concept, one place" discipline as `ai-target.md` AI4's Catalog-reuse precedent.

**Verify:** `grep -rn "class.*Graph" src/autotester/schema/` resolves to the extended
`portal_persona.py` family only — no second graph-shaped model anywhere. And
`grep -rniE "neo4j|networkx|graph[_-]?db" pyproject.toml src/` returns nothing.

### EC2 — Every generated eval traces to its source through a real graph edge, not free text

A `Case` with no resolvable source edge **is not produced**. Provenance is structural, not a
sentence in a description field.

**Verify:** a fixture flow's generated cases each resolve a graph edge to a real screen/flow node on
disk. Removing the edge-population step fails a test asserting every case carries a non-null trace.

### EC3 — A component PASS can never hide a workflow failure

An aggregate or summary view must not report an overall PASS for a multi-step workflow whose
**end-to-end** assertion failed while each individual component step passed. The rollup is
**workflow-first**, never "AND of the components".

This one is genuinely new — it was checked against `grade.md` and `expand.md` and neither states it
today. It is also the highest-value criterion in this file, because "all the parts passed" is
exactly the shape of a green report over a broken product.

**Verify:** a fixture workflow where every component step's own assertion passes but the end-to-end
assertion fails → the compiled top-level verdict is FAIL or INCONCLUSIVE, **never PASS**. The
sabotage is to revert the rollup to "AND of components" and reproduce the false PASS.

### EC4 — Scenario variants are distinct, traceable graph nodes [D-041 EXTEND, AT-586]

A declared scenario variant is its own node with its own case set. It is not folded into the base
flow.

**Verify:** a fixture flow with 2 declared scenario variants produces 2 distinct scenario nodes,
each with its own traceable case set.

### EC5 — A scenario list is an input contract: a branch with no compiled case is reported UNCOVERED

*(Added 2026-09-29 from Umesh's verbatim 2026-09-24 meeting direction, `qa/feedback-inbox.md`
2026-09-24T16:10, 10:35-10:57 and 05:30-06:05: "Sabse pehle scenario likhne zaroori hai taki aap
koi scenario bhoolo nahi ... us scenario me saare options test kar lena. Yes, no. Yes, no.")*

When evals are compiled from a written scenario list, every branch a scenario enumerates (yes / no,
each option) must end up with a compiled case **or** be listed as **uncovered**. A branch that
silently produced no case is the failure this refuses (intent O4).

**Verify:** a fixture scenario list with 3 scenarios, each with a yes and a no branch, where the
compiler is made unable to produce a case for exactly one branch — the compiled output lists that
branch under an `uncovered` heading with its scenario id, and the coverage figure is **not** 100%.
Sabotage: drop the uncovered-listing step — the named test goes red on the missing branch, not on an
import error.

## What changed (existing files edited in place; one new module per concept, reasons below)

- `src/autotester/schema/portal_persona.py` (edited in place, 227 -> 299 lines): `NodeKind` / `EdgeKind`
  Literals, `GraphNode`, `GraphEdge`, `KnowledgeGraph` (add_node/add_edge/out, validator refuses a
  dangling edge or duplicate node id), and `PortalPersona.graph` (defaulted, so older persona files
  still load; `stages/portal_persona.py::_merge` uses `model_copy(update=)` from the existing persona,
  so the graph survives a rebuild without touching that 300-line file). EC1 says the graph lives in
  this family, so it is NOT a new `schema/knowledge_graph.py` (scout's guess).
- `src/autotester/schema/scenario.py` (new): `Branch`, `ScenarioSpec`, `UncoveredBranch`,
  `CompileResult`. Reason: a scenario list is an input contract and `CompileResult` is the compiler's
  output, neither is graph-shaped (EC1's grep stays clean) and `portal_persona.py` had 1 line left.
- `src/autotester/stages/knowledge_graph.py` (new): `build_graph`, `trace_of`, `flow_of`, `add_case`,
  `record_verdict`. Reason: graph construction/resolution needs its own home; `stages/portal_persona.py`
  is at the 300-line cap.
- `src/autotester/stages/eval_compiler.py` (new): `compile_evals`, `rollup_workflow`.
  Reuses `stages/expand.py::expand_flow` and `stages/review.py::require_reviewed` unchanged.
- `docs/MAP.md`: regenerated by `autotester map` (new modules and models).
- Tests: `tests/test_knowledge_graph.py`, `tests/test_eval_compiler.py`, helper `tests/eval_compiler_fixtures.py`.
- NOT touched: `stages/expand.py`, `stages/reconcile.py`, and every file on the do-not-touch list.

## Design notes the checker should know

- EC2 enforcement is twice: `compile_evals` skips a flow with no resolvable trace BEFORE the model is called
  (no spend, named in `untraced_flows`), and `add_case` refuses any case whose source does not resolve.
- EC3 is `rollup_workflow(end_to_end, steps)`: end-to-end FAIL or any FAIL step -> FAIL; PASS only when the
  end-to-end is PASS and no step is non-PASS; else INCONCLUSIVE (a missing/blocked end-to-end is never PASS).
  It is a pure function. No caller in the repo feeds run verdicts into it yet (the run/report surfaces own
  that wiring and are outside this unit's file list); `record_verdict` puts a verdict node in the graph.
- EC5's uncompilable branch in the fixture is a branch whose `values` names a step target the flow lacks
  (also: a scenario on an unknown or untraceable flow uncovers every branch, with the flow id in the reason).
- Reconcile: no code from `stages/reconcile.py` is needed by EC1-EC5; it is reused as-is upstream (it produces
  the FlowSpec this compiler reads). Nothing was redone.
- Not built (outside the contract): a loader/UI for scenario lists (`compile_evals` takes `list[ScenarioSpec]`),
  and automatic graph build inside `build_portal_persona`.
- `NodeKind`/`EdgeKind` are `Literal` aliases in `portal_persona.py` (precedent: `flowspec.FlowKind`), not
  `StrEnum`s in `enums.py`, which is at 300 lines.
- TDD note: tests were written before the implementation but I did not run them red first; the falsification
  table below is the evidence each test can fail.

## Capability coverage (each new claim -> its isolating falsification)

Falsifying edits applied only in throwaway copies under `%TEMP%/fals/<name>/` (src+tests+scripts copied,
run with `PYTHONPATH=<copy>/src`); the worktree was never edited for a falsification. Script: `%TEMP%/falsify.py`.
PASS-before for every row: the unedited run printed `33 passed in 1.67s` for both files together.

| Criterion | capability | check that covers it | falsifying edit | observed |
|---|---|---|---|---|
| EC1 | exactly one graph model, in the persona family | `tests/test_knowledge_graph.py::test_one_graph_model_lives_in_the_persona_family` | add `class ShadowGraph(BaseModel)` in `schema/shadow.py` | `FAILED tests/test_knowledge_graph.py::test_one_graph_model_lives_in_the_persona_family` / `1 failed, 32 passed` |
| EC1 | no graph database | `test_no_graph_database_is_a_dependency` | add a `# import networkx` line to `stages/knowledge_graph.py` | `FAILED tests/test_knowledge_graph.py::test_no_graph_database_is_a_dependency` / `1 failed, 32 passed` |
| EC2 | a case traces through a real edge to a flow and screen, round-tripped from disk | `test_every_compiled_case_resolves_a_trace_to_a_real_screen_and_flow` | delete the `traces_to` edge-population line in `add_case` | `FAILED ...::test_every_compiled_case_resolves_a_trace_to_a_real_screen_and_flow`, `...::test_a_model_proposed_class_case_is_edged_to_its_flow` (+2 EC4/EC5 tests) / `4 failed, 29 passed` |
| EC2 | an untraceable flow yields no case, is named in `untraced_flows`, and spends no model call | `test_a_flow_with_no_resolvable_edge_produces_no_case_and_says_so`, `test_an_untraceable_flow_spends_no_model_call` | in `compile_evals` drop the `flow_of(...) is None` pre-check (keep only `node is None`) | `FAILED tests/test_eval_compiler.py::test_a_flow_with_no_resolvable_edge_produces_no_case_and_says_so`, `FAILED ...::test_an_untraceable_flow_spends_no_model_call` / `2 failed, 31 passed` |
| EC3 | workflow-first rollup | `test_all_components_pass_but_the_end_to_end_assertion_fails_is_never_pass` | replace body with "PASS iff all components PASS, else FAIL" (AND of components) | `FAILED ...::test_all_components_pass_but_the_end_to_end_assertion_fails_is_never_pass` (false PASS reproduced), `...::test_a_missing_end_to_end_verdict_is_inconclusive_not_pass`, 2 truth-table rows / `4 failed, 29 passed` |
| EC4 | each variant is its own scenario node with its own case set | `test_two_declared_variants_make_two_scenario_nodes_with_their_own_cases` | edge scenario cases to the flow node instead of the scenario node (folded into base flow) | `FAILED ...::test_two_declared_variants_make_two_scenario_nodes_with_their_own_cases`, `...::test_exactly_the_uncompilable_branch_is_uncovered_and_coverage_is_not_full` / `2 failed, 31 passed` |
| EC5 | an uncompilable branch is listed UNCOVERED, coverage < 100% | `test_exactly_the_uncompilable_branch_is_uncovered_and_coverage_is_not_full` | replace the `uncovered += _uncover(...)` line with `pass` | `FAILED tests/test_eval_compiler.py::test_exactly_the_uncompilable_branch_is_uncovered_and_coverage_is_not_full` / `1 failed, 32 passed` (assertion on the missing `("s_browse","no")` row, not an import error) |

## Commands run and actual output

```
$ uv run pytest tests/test_knowledge_graph.py tests/test_eval_compiler.py      # done_check form: tests/test_eval_compiler.py alone exits 0 within this
.................................                                        [100%]
33 passed in 1.67s

$ uv run pytest tests/test_knowledge_graph.py tests/test_eval_compiler.py tests/test_portal_persona.py tests/test_schema.py tests/test_persona_diff_pipeline.py tests/test_persona_changes.py
(the four extra files exercise the edited `portal_persona.py`; one process, no xdist)
87 passed in 97.96s (0:01:37)

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-missing: T-125 — closed high-value task has no live/updated row
stale-generated: docs/SNAPSHOT.md — differs from regeneration; run `autotester snapshot`

2 violation(s)
```

Doctor: both remaining violations are pre-existing and not caused by this unit. `ledger-row-missing: T-125` is the
base's own close-out debt (the T-125 ledger row). `docs/SNAPSHOT.md` regenerates to a diff about T-125/T-154
status lines, which other sessions own; I reverted my regeneration to avoid a rebase conflict. `docs/MAP.md` is
regenerated and clean. No file-length, function-length or duplicate-concept violation.

Suite: the full suite was not run (suite_runs=0 by instruction).
