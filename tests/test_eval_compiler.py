"""The eval compiler (T-166). Contract: qa/contracts/eval-compiler.md, one group per
criterion EC2-EC5 (EC1 is tests/test_knowledge_graph.py).

Fully offline: no browser, network or model. Provider is a `MockProvider`."""

from __future__ import annotations

from pathlib import Path

import pytest
from eval_compiler_fixtures import (
    BROWSE,
    LOGIN,
    ORPHAN,
    SLUG,
    branch,
    persona,
    provider,
    scenarios,
    spec,
)

from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, Result
from autotester.schema.flowspec import FlowSpec, Step
from autotester.schema.scenario import ScenarioSpec
from autotester.stages.eval_compiler import compile_evals, rollup_workflow
from autotester.stages.knowledge_graph import trace_of
from autotester.stages.review import FlowSpecNotReviewed
from autotester.store.project_store import ProjectStore


def _compile(*flows, scens=None, release=None):
    return compile_evals(spec(*flows), persona(*flows), scens or [], provider(*flows),
                         release=release)


# -- EC2: every eval traces to its source through a real graph edge --------

def test_every_compiled_case_resolves_a_trace_to_a_real_screen_and_flow(tmp_path: Path) -> None:
    out = _compile(LOGIN, BROWSE, scens=scenarios())
    assert out.cases, "a fixture with two flows must compile cases"
    store = ProjectStore(SLUG, tmp_path)
    store.save_portal_persona(persona(LOGIN, BROWSE).model_copy(update={"graph": out.graph}))
    graph = store.load_portal_persona().graph  # the graph as it is ON DISK
    for case in out.cases:
        path = trace_of(graph, case.id)
        kinds = [n.kind for n in path]
        assert kinds[0] == "case" and "flow" in kinds and "screen" in kinds, case.title
        for node in path:
            assert graph.node(node.id) is not None


def test_a_flow_with_no_resolvable_edge_produces_no_case_and_says_so() -> None:
    out = _compile(LOGIN, ORPHAN)
    assert {c.flow_id for c in out.cases} == {"flow_login"}
    assert out.untraced_flows == ["flow_orphan"]


def test_an_untraceable_flow_spends_no_model_call() -> None:
    """Even a model that would accept a class for the ORPHAN flow is never asked."""
    prov = provider(ORPHAN)
    prov.responses["agent"][0] = ExpandedSteps(
        steps=[Step(order=1, action=Action.CLICK, target="x")], rationale="r")
    out = compile_evals(spec(ORPHAN), persona(ORPHAN), [], prov)
    assert out.cases == [] and out.untraced_flows == ["flow_orphan"]
    assert prov.prompts == []


def test_a_model_proposed_class_case_is_edged_to_its_flow() -> None:
    prov = provider(LOGIN)
    prov.responses["agent"][0] = ExpandedSteps(
        steps=[Step(order=1, action=Action.FILL, target="email field", value="")], rationale="r")
    out = compile_evals(spec(LOGIN), persona(LOGIN), [], prov)
    assert len(out.cases) == 2  # the happy case + the one accepted class
    assert all(trace_of(out.graph, c.id) for c in out.cases)


def test_the_flowspec_must_be_reviewed_first() -> None:
    draft = FlowSpec(project=SLUG, flows=[LOGIN])
    with pytest.raises(FlowSpecNotReviewed):
        compile_evals(draft, persona(LOGIN), [], provider(LOGIN))


def test_a_release_node_is_edged_from_every_case() -> None:
    out = _compile(LOGIN, scens=scenarios()[:2], release="2026.10.7")
    targets = {e.src for e in out.graph.edges if e.kind == "targets"
               and e.dst == "release:2026.10.7"}
    assert targets == {f"case:{c.id}" for c in out.cases}


# -- EC3: a component PASS can never hide a workflow failure ------------

def test_all_components_pass_but_the_end_to_end_assertion_fails_is_never_pass() -> None:
    top = rollup_workflow(Result.FAIL, [Result.PASS] * 4)
    assert top is Result.FAIL


def test_a_missing_end_to_end_verdict_is_inconclusive_not_pass() -> None:
    assert rollup_workflow(None, [Result.PASS] * 4) is Result.INCONCLUSIVE
    assert rollup_workflow(Result.BLOCKED, [Result.PASS]) is Result.INCONCLUSIVE


@pytest.mark.parametrize(("e2e", "steps", "expected"), [
    (Result.PASS, [Result.PASS, Result.PASS], Result.PASS),
    (Result.PASS, [], Result.PASS),
    (Result.PASS, [Result.PASS, Result.FAIL], Result.FAIL),
    (Result.PASS, [Result.PASS, Result.INCONCLUSIVE], Result.INCONCLUSIVE),
    (Result.FAIL, [Result.FAIL], Result.FAIL),
    (Result.INCONCLUSIVE, [Result.PASS], Result.INCONCLUSIVE),
    (None, [Result.FAIL], Result.FAIL),
])
def test_rollup_truth_table(e2e, steps, expected) -> None:
    assert rollup_workflow(e2e, steps) is expected


# -- EC4: scenario variants are distinct, traceable nodes ------------------

def test_two_declared_variants_make_two_scenario_nodes_with_their_own_cases() -> None:
    two = [s for s in scenarios() if s.flow_id == "flow_login"]
    out = _compile(LOGIN, scens=two)
    nodes = [n for n in out.graph.nodes if n.kind == "scenario"]
    assert sorted(n.id for n in nodes) == ["scenario:s_new", "scenario:s_valid"]
    sets = {}
    for node in nodes:
        assert [n.id for n in out.graph.out(node.id, "variant_of")] == ["flow:flow_login"]
        sets[node.id] = {e.src for e in out.graph.edges
                         if e.kind == "traces_to" and e.dst == node.id}
        assert len(sets[node.id]) == 2  # yes + no
    assert not sets["scenario:s_new"] & sets["scenario:s_valid"]
    base = {f"case:{c.id}" for c in out.cases if c.flow_id == "flow_login"}
    assert set().union(*sets.values()) <= base


def test_a_scenario_case_applies_only_its_own_branch_values() -> None:
    out = _compile(LOGIN, scens=scenarios()[:1])
    no_case = next(c for c in out.cases if c.title.endswith("s_valid/no"))
    pw = next(s for s in no_case.steps if s.target == "password field")
    assert pw.value == "bad"
    assert no_case.steps[-1].expected.visible_text == ["Invalid"]
    yes_case = next(c for c in out.cases if c.title.endswith("s_valid/yes"))
    assert next(s for s in yes_case.steps if s.target == "password field").value == "pw"


# -- EC5: a branch with no compiled case is reported UNCOVERED ----------

def test_exactly_the_uncompilable_branch_is_uncovered_and_coverage_is_not_full() -> None:
    out = _compile(LOGIN, BROWSE, scens=scenarios())
    assert [(u.scenario_id, u.branch_id) for u in out.uncovered] == [("s_browse", "no")]
    assert out.total_branches == 6
    assert out.coverage == pytest.approx(5 / 6) and out.coverage < 1.0
    covered = {(e.dst.split(":")[1], e.src) for e in out.graph.edges if e.kind == "traces_to"
               and e.dst.startswith("scenario:")}
    assert len(covered) == 5


def test_a_fully_compilable_list_has_nothing_uncovered() -> None:
    good = [s for s in scenarios() if s.id != "s_browse"]
    out = _compile(LOGIN, scens=good)
    assert out.uncovered == [] and out.coverage == 1.0


def test_a_scenario_on_an_unknown_flow_uncovers_every_branch_with_a_reason() -> None:
    lost = ScenarioSpec(id="s_lost", flow_id="flow_nope", name="lost",
                        branches=[branch("yes", "y"), branch("no", "n")])
    out = _compile(LOGIN, scens=[lost])
    assert [(u.scenario_id, u.branch_id) for u in out.uncovered] == [
        ("s_lost", "yes"), ("s_lost", "no")]
    assert all("flow_nope" in u.reason for u in out.uncovered)
    assert out.coverage == 0.0


def test_a_scenario_on_a_flow_with_no_graph_trace_is_uncovered() -> None:
    lost = ScenarioSpec(id="s_orphan", flow_id="flow_orphan", name="o",
                        branches=[branch("yes", "y")])
    out = _compile(LOGIN, ORPHAN, scens=[lost])
    assert [u.branch_id for u in out.uncovered] == ["yes"]
    assert not [n for n in out.graph.nodes if n.id == "scenario:s_orphan"]
