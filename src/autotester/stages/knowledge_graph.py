"""KNOWLEDGE GRAPH: build the typed graph from the persona + FlowSpec, and resolve a
case back to its source (T-166, qa/contracts/eval-compiler.md EC1/EC2).

The graph is `schema/portal_persona.py::KnowledgeGraph` — the persona graph extended, JSON
on the filestore (D-002/D-041). Nothing here owns a second shape. Provenance is structural:
a case is traceable only if a `traces_to` edge leads to a flow (directly, or through a
scenario's `variant_of`) that `visits` at least one real screen node.
"""

from __future__ import annotations

from autotester.schema.case import Case
from autotester.schema.enums import Result
from autotester.schema.flowspec import Flow, FlowSpec
from autotester.schema.portal_persona import (
    EdgeKind,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    PortalPersona,
)


def _link(graph: KnowledgeGraph, kind: EdgeKind, src: str, dst: str, label: str = "") -> None:
    graph.add_edge(GraphEdge(kind=kind, src=src, dst=dst, label=label))


def _add_screens(graph: KnowledgeGraph, persona: PortalPersona) -> None:
    for screen in persona.screens:
        node = GraphNode.make("screen", screen.id, screen.name)
        graph.add_node(node)
        for control in screen.controls:
            ctl = GraphNode.make("control", f"{screen.id}/{control}", control)
            graph.add_node(ctl)
            _link(graph, "has_control", node.id, ctl.id)


def _add_transitions(graph: KnowledgeGraph, persona: PortalPersona) -> None:
    """Persisted transitions name screens by crawl-node id OR by name; resolve both."""
    by_ref = {s.id: s.id for s in persona.screens}
    by_ref.update({" ".join(s.name.casefold().split()): s.id for s in persona.screens})

    def ref(name: str | None) -> str | None:
        return by_ref.get(name or "") or by_ref.get(" ".join((name or "").casefold().split()))

    for t in persona.transitions:
        src, dst = ref(t.from_screen), ref(t.to_screen)
        if src and dst:
            _link(graph, "leads_to", f"screen:{src}", f"screen:{dst}", t.control)


def _add_flow(graph: KnowledgeGraph, flow_id: str, name: str, screen_ids: list[str]) -> None:
    node = GraphNode.make("flow", flow_id, name)
    graph.add_node(node)
    for sid in screen_ids:
        if graph.node(f"screen:{sid}") is not None:
            _link(graph, "visits", node.id, f"screen:{sid}")


def _flow_screens(flow: Flow) -> list[str]:
    ids = [flow.entry_screen, *(s.screen_id for s in flow.steps), flow.exit_screen]
    return list(dict.fromkeys(i for i in ids if i))


def _add_flows(graph: KnowledgeGraph, persona: PortalPersona, spec: FlowSpec | None) -> None:
    flows = {f.id: f for f in (spec.flows if spec else [])}
    for taught in persona.taught_flows:
        screens = [taught.entry_screen, taught.exit_screen or ""]
        _add_flow(graph, taught.id, taught.name, screens if taught.id not in flows else [])
    for flow in flows.values():
        _add_flow(graph, flow.id, flow.name, _flow_screens(flow))
        for step in flow.steps:
            for pattern in step.expected.network:
                api = GraphNode.make("api", pattern)
                if step.screen_id and graph.node(f"screen:{step.screen_id}"):
                    graph.add_node(api)
                    _link(graph, "calls", f"screen:{step.screen_id}", api.id)


def build_graph(persona: PortalPersona, spec: FlowSpec | None = None) -> KnowledgeGraph:
    """The persona's graph, plus every screen, control, transition, flow and API the persona
    and FlowSpec know. Add-only and idempotent: rebuilding never drops what is already there."""
    graph = persona.graph.model_copy(deep=True)
    _add_screens(graph, persona)
    _add_transitions(graph, persona)
    _add_flows(graph, persona, spec)
    return graph


def flow_of(graph: KnowledgeGraph, source: GraphNode) -> GraphNode | None:
    """The flow node a flow or scenario node stands for, only if it visits a real screen."""
    flow = source if source.kind == "flow" else next(iter(graph.out(source.id, "variant_of")), None)
    if flow is None or flow.kind != "flow" or not graph.out(flow.id, "visits"):
        return None
    return flow


def trace_of(graph: KnowledgeGraph, case_id: str) -> list[GraphNode]:
    """The case's provenance as graph nodes: case, its source (scenario and/or flow), and the
    screens the flow visits. Empty when any link is missing — an untraceable case."""
    case = graph.node(f"case:{case_id}")
    for source in graph.out(f"case:{case_id}", "traces_to"):
        flow = flow_of(graph, source)
        if case is not None and flow is not None:
            via = [source] if source is not flow else []
            return [case, *via, flow, *graph.out(flow.id, "visits")]
    return []


def add_case(graph: KnowledgeGraph, case: Case, source: GraphNode,
             release: str | None = None) -> bool:
    """Put `case` in the graph, edged to its `source` flow/scenario node. A case whose source
    does not resolve to a real flow and screen is NOT added (EC2); returns whether it was."""
    if flow_of(graph, source) is None:
        return False
    node = GraphNode.make("case", case.id, case.title)
    graph.add_node(node)
    _link(graph, "traces_to", node.id, source.id)
    if release:
        graph.add_node(GraphNode.make("release", release))
        _link(graph, "targets", node.id, f"release:{release}")
    return True


def record_verdict(graph: KnowledgeGraph, case_id: str, result: Result, *, run_id: str) -> None:
    """One verdict node per (run, case), edged to its case node."""
    if graph.node(f"case:{case_id}") is None:
        raise ValueError(f"verdict names a case that is not a node: case:{case_id}")
    node = GraphNode.make("verdict", f"{run_id}/{case_id}", result.value)
    graph.add_node(node)
    _link(graph, "verdict_of", node.id, f"case:{case_id}")
