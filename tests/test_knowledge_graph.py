"""The knowledge graph (T-166, qa/contracts/eval-compiler.md EC1): the persona graph
EXTENDED with typed nodes and edges, JSON on the filestore, no graph database.

Fully offline: no browser, network or model."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from eval_compiler_fixtures import BROWSE, LOGIN, SLUG, persona, spec
from pydantic import ValidationError

from autotester.schema.enums import Result
from autotester.schema.portal_persona import GraphEdge, GraphNode, KnowledgeGraph, PortalPersona
from autotester.stages.knowledge_graph import build_graph, record_verdict, trace_of
from autotester.store.project_store import ProjectStore

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "autotester"


def _graph() -> KnowledgeGraph:
    return build_graph(persona(LOGIN, BROWSE), spec(LOGIN, BROWSE))


# -- EC1: one graph model, in the persona family --------------------------

def test_one_graph_model_lives_in_the_persona_family() -> None:
    """EC1 verify 1: `class.*Graph` under schema/ resolves to portal_persona.py only."""
    hits = {p.name for p in (SRC / "schema").glob("*.py")
            if re.search(r"^class \w*Graph", p.read_text(encoding="utf-8"), re.M)}
    assert hits == {"portal_persona.py"}


def test_no_graph_database_is_a_dependency() -> None:
    """EC1 verify 2 / D-041: no neo4j, networkx or graph-db anywhere."""
    pattern = re.compile(r"neo4j|networkx|graph[_-]?db", re.I)
    files = [ROOT / "pyproject.toml", *SRC.rglob("*.py")]
    offenders = [str(f) for f in files if pattern.search(f.read_text(encoding="utf-8"))]
    assert offenders == []


def test_build_graph_has_every_node_kind_the_persona_can_supply() -> None:
    graph = _graph()
    kinds = {n.kind for n in graph.nodes}
    assert {"screen", "control", "flow", "api"} <= kinds
    assert graph.node("screen:scr_signin") is not None
    assert graph.node("control:scr_signin/email field") is not None
    assert [n.id for n in graph.out("flow:flow_login", "visits")][:1] == ["screen:scr_signin"]
    assert "api:POST /api/login" in [n.id for n in graph.out("screen:scr_signin", "calls")]


def test_a_learned_transition_becomes_a_leads_to_edge() -> None:
    graph = _graph()
    edges = [e for e in graph.edges if e.kind == "leads_to"]
    assert [(e.src, e.dst, e.label) for e in edges] == [
        ("screen:scr_signin", "screen:scr_home", "Login button")]


def test_a_flow_the_persona_never_saw_has_no_visits_edge() -> None:
    from eval_compiler_fixtures import ORPHAN

    graph = build_graph(persona(ORPHAN), spec(ORPHAN))
    assert graph.node("flow:flow_orphan") is not None
    assert graph.out("flow:flow_orphan", "visits") == []


def test_build_is_idempotent_and_never_drops_what_is_known() -> None:
    first = _graph()
    seeded = persona(LOGIN, BROWSE).model_copy(update={"graph": first})
    again = build_graph(seeded, spec(LOGIN, BROWSE))
    assert again.model_dump() == first.model_dump()


# -- the model refuses an inconsistent graph ----------------------------

def test_an_edge_to_a_missing_node_is_refused() -> None:
    graph = KnowledgeGraph(nodes=[GraphNode.make("screen", "a")])
    with pytest.raises(ValueError, match="screen:b"):
        graph.add_edge(GraphEdge(kind="leads_to", src="screen:a", dst="screen:b"))
    with pytest.raises(ValidationError):
        KnowledgeGraph(nodes=[], edges=[GraphEdge(kind="visits", src="x", dst="y")])


def test_an_unknown_node_kind_is_refused() -> None:
    with pytest.raises(ValidationError):
        GraphNode(id="widget:1", kind="widget")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        GraphNode(id="screen:1", kind="screen", surprise=1)  # type: ignore[call-arg]


# -- the graph is JSON on the filestore, carried by the persona (D-002) ----

def test_the_graph_round_trips_through_the_persona_file(tmp_path: Path) -> None:
    store = ProjectStore(SLUG, tmp_path)
    saved = persona(LOGIN).model_copy(update={"graph": build_graph(persona(LOGIN), spec(LOGIN))})
    store.save_portal_persona(saved)
    assert store.paths.portal_persona.suffix == ".json"
    loaded = store.load_portal_persona()
    assert loaded is not None
    assert loaded.graph.model_dump() == saved.graph.model_dump()
    assert loaded.graph.node("flow:flow_login") is not None


def test_a_persona_written_before_the_graph_existed_still_loads() -> None:
    old = PortalPersona(project=SLUG).model_dump(mode="json")
    del old["graph"]
    assert PortalPersona.model_validate(old).graph.nodes == []


# -- trace + verdict nodes -------------------------------------------

def test_trace_of_is_empty_for_an_unknown_case() -> None:
    assert trace_of(_graph(), "case_nope") == []


def test_record_verdict_adds_a_verdict_node_edged_to_its_case() -> None:
    graph = _graph()
    graph.add_node(GraphNode.make("case", "c1"))
    record_verdict(graph, "c1", Result.FAIL, run_id="run_1")
    verdicts = [n for n in graph.nodes if n.kind == "verdict"]
    assert [v.label for v in verdicts] == ["FAIL"]
    assert [e.dst for e in graph.edges if e.kind == "verdict_of"] == ["case:c1"]
    with pytest.raises(ValueError, match="case:ghost"):
        record_verdict(graph, "ghost", Result.PASS, run_id="run_1")
