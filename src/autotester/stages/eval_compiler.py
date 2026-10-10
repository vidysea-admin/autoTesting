"""EVAL COMPILER: compile evals from the knowledge graph, the FlowSpec and a written scenario
list — every one traced to its source (T-166, qa/contracts/eval-compiler.md EC2-EC5).

Taxonomy cases come from `stages/expand.py::expand_flow` (reused, not redone); scenario
branches compile deterministically. A case enters the result only if
`knowledge_graph.add_case` could edge it to a flow that visits a real screen (EC2). A scenario
branch that yields no case is returned as `UncoveredBranch`, never dropped (EC5).
"""

from __future__ import annotations

from collections.abc import Iterable

from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, Result
from autotester.schema.flowspec import ExpectedState, Flow, FlowSpec, Step
from autotester.schema.portal_persona import GraphEdge, GraphNode, KnowledgeGraph, PortalPersona
from autotester.schema.scenario import Branch, CompileResult, ScenarioSpec, UncoveredBranch
from autotester.stages.expand import expand_flow
from autotester.stages.knowledge_graph import add_case, build_graph, flow_of
from autotester.stages.review import require_reviewed


def rollup_workflow(end_to_end: Result | None, steps: Iterable[Result]) -> Result:
    """The workflow's top-level verdict, WORKFLOW-FIRST (EC3). The end-to-end assertion decides:
    a failed end-to-end is FAIL however many component steps passed, and a missing,
    blocked or inconclusive one can never be PASS. PASS needs the end-to-end PASS *and* no
    component that is not PASS — "all the parts passed" alone is exactly a green report over a
    broken product."""
    parts = list(steps)
    if end_to_end is Result.FAIL or Result.FAIL in parts:
        return Result.FAIL
    if end_to_end is Result.PASS and all(p is Result.PASS for p in parts):
        return Result.PASS
    return Result.INCONCLUSIVE


def _branch_case(flow: Flow, project: str, scenario: ScenarioSpec,
                 branch: Branch) -> tuple[Case | None, str]:
    """The flow's own steps with this branch's values typed in, ending on its expected text.
    (None, why) when the branch names a step the flow does not have."""
    missing = sorted(set(branch.values) - {s.target for s in flow.steps})
    if missing:
        return None, f"branch values name step target(s) {missing} that flow {flow.id} lacks"
    if not flow.steps:
        return None, f"flow {flow.id} has no steps to compile"
    steps = [s.model_copy(update={"value": branch.values.get(s.target, s.value)})
             for s in sorted(flow.steps, key=lambda s: s.order)]
    tag = f"scenario {scenario.id}/{branch.id}"
    steps[0] = steps[0].model_copy(update={"note": "; ".join(filter(None, [steps[0].note, tag]))})
    if branch.expect_text:
        steps.append(Step(order=steps[-1].order + 1, action=Action.ASSERT, target="page",
                          expected=ExpectedState(visible_text=branch.expect_text)))
    case = Case(project=project, flow_id=flow.id, kind=branch.kind, case_class=CaseClass.HAPPY,
                title=f"{flow.name} — {scenario.id}/{branch.id}", rationale=branch.label,
                steps=steps)
    return case, ""


def _uncover(scenario: ScenarioSpec, reason: str,
             only: Iterable[Branch] | None = None) -> list[UncoveredBranch]:
    return [UncoveredBranch(scenario_id=scenario.id, branch_id=b.id, reason=reason)
            for b in (only if only is not None else scenario.branches)]


def _compile_scenario(spec: FlowSpec, graph: KnowledgeGraph, scenario: ScenarioSpec,
                      release: str | None) -> tuple[list[Case], list[UncoveredBranch]]:
    flow = next((f for f in spec.flows if f.id == scenario.flow_id), None)
    flow_node = graph.node(f"flow:{scenario.flow_id}")
    if flow is None or flow_node is None or flow_of(graph, flow_node) is None:
        return [], _uncover(scenario, f"scenario flow {scenario.flow_id} has no graph trace")
    node = GraphNode.make("scenario", scenario.id, scenario.name)
    graph.add_node(node)
    graph.add_edge(GraphEdge(kind="variant_of", src=node.id, dst=flow_node.id))
    cases: list[Case] = []
    uncovered: list[UncoveredBranch] = []
    for branch in scenario.branches:
        case, why = _branch_case(flow, spec.project, scenario, branch)
        if case is None or not add_case(graph, case, node, release):
            uncovered += _uncover(scenario, why or "no graph trace", [branch])
        else:
            cases.append(case)
    return cases, uncovered


def compile_evals(spec: FlowSpec, persona: PortalPersona, scenarios: list[ScenarioSpec],
                  provider: Provider, docs: RepoDocs | None = None, *,
                  release: str | None = None) -> CompileResult:
    """Compile evals from an APPROVED FlowSpec, the persona's graph and a scenario list.

    A flow with no resolvable graph trace gets no case and costs no model call (EC2); it is
    named in `untraced_flows`. Every scenario branch ends as a case or an `uncovered` row
    (EC5); each scenario is its own node with its own case set (EC4)."""
    require_reviewed(spec)
    graph = build_graph(persona, spec)
    result = CompileResult(graph=graph, total_branches=sum(len(s.branches) for s in scenarios))
    for flow in spec.flows:
        node = graph.node(f"flow:{flow.id}")
        if node is None or flow_of(graph, node) is None:
            result.untraced_flows.append(flow.id)
            continue
        result.cases += [c for c in expand_flow(flow, spec.project, provider, docs)
                         if add_case(graph, c, node, release)]
    for scenario in scenarios:
        cases, uncovered = _compile_scenario(spec, graph, scenario, release)
        result.cases += cases
        result.uncovered += uncovered
    return result
