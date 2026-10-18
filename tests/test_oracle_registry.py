"""T-211 (multi-role-platform.md MP15): the oracle registry lists every G11 oracle by module name.

A module that is not there is reported `not built` in the run summary, never omitted. The importer
is injectable, so one module can be made absent without touching `stages/`.
"""

from __future__ import annotations

import types

import pytest
from cross_role_fakes import FakeClock, ScriptedPort, make_scenario

from autotester.schema.leak_evidence import LeakEvidence
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext, OracleRunSummary, OracleState
from autotester.stages.cross_role_runner import run_scenario
from autotester.stages.oracle_registry import module_name, oracle_statuses, run_oracles

ABSENT = OracleName.PAYMENT


def _finding(oracle: OracleName) -> MultiRoleFinding:
    return MultiRoleFinding(
        finding_id=f"f-{oracle.value}", finding_class=FindingClass.DATA_LEAK, title="rows leak",
        role="parent", platform_id="parent", url_template="/students/{id}",
        steps=["login parent-portal", "goto /students/{id}"], count=3, oracle=oracle,
        leak_evidence=LeakEvidence(
            foreign_row_count=3, field_names=["Name"], url_template="/students/{id}"))


def _stub(oracle: OracleName, *, findings: int = 0, raises: bool = False) -> types.ModuleType:
    mod = types.ModuleType(module_name(oracle))

    def run(context: OracleContext) -> list[MultiRoleFinding]:
        if raises:
            raise ValueError("secret detail that must not be reported")
        return [_finding(oracle)] * findings

    mod.run = run  # type: ignore[attr-defined]
    return mod


def _importer(missing: set[OracleName], **stubs: types.ModuleType):
    def importer(name: str) -> types.ModuleType:
        for oracle in OracleName:
            if module_name(oracle) == name:
                if oracle in missing:
                    raise ModuleNotFoundError(f"No module named {name!r}", name=name)
                return stubs.get(oracle.value, _stub(oracle))
        raise AssertionError(f"unexpected import {name}")
    return importer


def _context() -> OracleContext:
    return OracleContext(project_slug="demo", run_dir="runs/r1", scenario_id="s1",
                         role_ids=["teacher"], platform_ids=["primary"], steps=[],
                         assertion_outcomes=[])


def test_mp15_module_name_is_the_stage_module_for_every_oracle() -> None:
    assert module_name(OracleName.TENANT) == "autotester.stages.oracle_tenant"
    assert len({module_name(o) for o in OracleName}) == len(OracleName)


def test_mp15_one_absent_module_is_reported_not_built_and_not_omitted() -> None:
    summary = oracle_statuses(_importer({ABSENT}))
    by_oracle = {s.oracle: s for s in summary.statuses}
    assert set(by_oracle) == set(OracleName)                       # every oracle is listed
    assert by_oracle[ABSENT].state is OracleState.NOT_BUILT
    assert by_oracle[ABSENT].module == module_name(ABSENT)
    others = [s for o, s in by_oracle.items() if o is not ABSENT]
    assert all(s.state is OracleState.NOT_RUN for s in others)     # built, none selected


def test_mp15_the_real_tree_lists_all_thirteen_and_names_the_unbuilt_ones() -> None:
    summary = oracle_statuses()
    assert len(summary.statuses) == len(OracleName) == 13
    states = {s.state for s in summary.statuses}
    assert states <= {OracleState.NOT_BUILT, OracleState.NOT_RUN}   # nothing broken on import


def test_mp15_not_built_label_is_the_contract_wording() -> None:
    assert OracleState.NOT_BUILT.value == "not built"
    assert OracleState.NOT_RUN.value == "not run"


def test_a_module_that_fails_for_another_reason_is_errored_not_not_built() -> None:
    def importer(name: str) -> types.ModuleType:
        raise ModuleNotFoundError("No module named 'some_dependency'", name="some_dependency")

    summary = oracle_statuses(importer)
    assert {s.state for s in summary.statuses} == {OracleState.ERRORED}
    assert all("some_dependency" in (s.reason or "") for s in summary.statuses)


def test_a_built_module_without_a_run_callable_is_errored() -> None:
    mod = types.ModuleType(module_name(OracleName.TENANT))
    summary = oracle_statuses(_importer(set(), tenant=mod))
    assert next(s for s in summary.statuses if s.oracle is OracleName.TENANT).state \
        is OracleState.ERRORED


def test_selected_oracles_run_and_their_findings_are_returned_with_counts() -> None:
    importer = _importer({ABSENT}, tenant=_stub(OracleName.TENANT, findings=2))
    summary, findings = run_oracles(
        _context(), [OracleName.TENANT, OracleName.MAILBOX, ABSENT], importer)
    by_oracle = {s.oracle: s for s in summary.statuses}
    assert by_oracle[OracleName.TENANT].state is OracleState.RAN
    assert by_oracle[OracleName.TENANT].finding_count == 2
    assert by_oracle[OracleName.MAILBOX].state is OracleState.RAN
    assert by_oracle[ABSENT].state is OracleState.NOT_BUILT        # selected but missing: said so
    assert by_oracle[OracleName.CONSISTENCY].state is OracleState.NOT_RUN
    assert [f.finding_id for f in findings] == ["f-tenant", "f-tenant"]


def test_an_oracle_that_raises_is_errored_with_the_type_only() -> None:
    importer = _importer(set(), tenant=_stub(OracleName.TENANT, raises=True))
    summary, findings = run_oracles(_context(), [OracleName.TENANT], importer)
    status = next(s for s in summary.statuses if s.oracle is OracleName.TENANT)
    assert status.state is OracleState.ERRORED
    assert status.reason == "ValueError"
    assert "secret detail" not in summary.model_dump_json() and findings == []


def test_an_oracle_returning_the_wrong_type_is_errored() -> None:
    mod = types.ModuleType(module_name(OracleName.TENANT))
    mod.run = lambda context: ["not a finding"]  # type: ignore[attr-defined]
    summary, findings = run_oracles(_context(), [OracleName.TENANT],
                                    _importer(set(), tenant=mod))
    assert next(s for s in summary.statuses if s.oracle is OracleName.TENANT).state \
        is OracleState.ERRORED and findings == []


def test_the_summary_model_refuses_an_omitted_or_duplicated_oracle() -> None:
    full = oracle_statuses(_importer(set())).statuses
    with pytest.raises(ValueError, match="every oracle"):
        OracleRunSummary(statuses=full[:-1])
    with pytest.raises(ValueError, match="every oracle"):
        OracleRunSummary(statuses=[*full[:-1], full[0]])


def test_the_scenario_result_carries_the_registry_summary_and_findings() -> None:
    clock = FakeClock()
    importer = _importer({ABSENT}, tenant=_stub(OracleName.TENANT, findings=1))
    result = run_scenario(make_scenario(within_s=5), ScriptedPort(clock, 2.0), clock,
                          project_slug="demo", run_dir="runs/r1", platform_ids=["primary"],
                          oracles=[OracleName.TENANT], importer=importer)
    states = {s.oracle: s.state for s in result.oracle_summary.statuses}
    assert len(states) == 13
    assert states[OracleName.TENANT] is OracleState.RAN and states[ABSENT] is OracleState.NOT_BUILT
    assert [f.finding_id for f in result.findings] == ["f-tenant"]


def test_the_oracle_receives_the_live_port_but_it_is_never_serialised() -> None:
    seen: list[OracleContext] = []
    mod = types.ModuleType(module_name(OracleName.TENANT))
    mod.run = lambda context: seen.append(context) or []  # type: ignore[attr-defined]
    clock = FakeClock()
    port = ScriptedPort(clock, 2.0)
    run_scenario(make_scenario(within_s=5), port, clock, project_slug="demo", run_dir="runs/r1",
                 oracles=[OracleName.TENANT], importer=_importer(set(), tenant=mod))
    assert seen[0].port is port
    assert seen[0].role_ids == ["teacher", "parent"] and seen[0].assertion_outcomes
    assert "port" not in seen[0].model_dump()
