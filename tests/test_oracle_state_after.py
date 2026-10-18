"""T-220 (multi-role-platform.md MP33): state is checked before, after and after a reload, per role.

The fixture app has three faults and one correct counter (synthetic shapes, MPI2): a counter that
is not incremented, one incremented only for the actor, one reverted on reload (plus a wrong-sized
one and a status reader). Each fault is a finding that cites all three readings; the correct
counter, whose non-actor page is stale until reload, is clean.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from state_after_fakes import StatePort

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.flowspec import ExpectedState
from autotester.schema.multi_role_enums import AssertChannel, FindingClass, OracleName
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.role_step import RoleStep
from autotester.schema.state_probe import ReaderKind, StateProbe
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_registry import run_oracles
from autotester.stages.oracle_state_after import PROBES_FILE, run

ACTION = RoleStep(id="send", role_id="teacher", action="click #send")


def _probe(name: str, readers: list[str], **over: object) -> StateProbe:
    fields: dict[str, object] = {
        "id": name, "platform_id": "parent", "kind": ReaderKind.COUNTER,
        "reader_channel": AssertChannel.UI, "reader_target": name, "reader_url": "/inbox",
        "action": ACTION, "reader_role_ids": readers, "expected_delta": 1}
    return StateProbe(**{**fields, **over})


def _context(tmp_path: Path, probes: list[StateProbe], port: object) -> OracleContext:
    text = "[" + ",".join(p.model_dump_json() for p in probes) + "]"
    (tmp_path / PROBES_FILE).write_text(text, encoding="utf-8")
    return OracleContext(project_slug="demo", run_dir=str(tmp_path), scenario_id="s1",
                         role_ids=["teacher", "parent"], port=port)  # type: ignore[arg-type]


def _matrix(tmp_path: Path):
    modes = {"not-incremented": "not_incremented", "actor-only": "actor_only",
             "reverted": "reverted", "correct": "correct"}
    probes = [_probe("not-incremented", ["teacher", "parent"]),
              _probe("actor-only", ["teacher", "parent"]),
              _probe("reverted", ["teacher"]),
              _probe("correct", ["teacher", "parent"])]
    return run(_context(tmp_path, probes, StatePort(modes)))


def test_each_fault_is_reported_and_the_correct_counter_is_not(tmp_path: Path) -> None:
    findings = _matrix(tmp_path)
    assert {f.finding_id for f in findings} == {
        "state-not-incremented-teacher", "state-not-incremented-parent",
        "state-actor-only-parent", "state-reverted-teacher"}
    assert not [f for f in findings if "correct" in f.finding_id]


def test_a_finding_cites_all_three_readings_and_the_fault(tmp_path: Path) -> None:
    by_id = {f.finding_id: f for f in _matrix(tmp_path)}
    assert "missing" in by_id["state-not-incremented-teacher"].title
    assert "before=3 after=3 reload=3" in by_id["state-not-incremented-teacher"].title
    assert "not_persisted" in by_id["state-reverted-teacher"].title
    assert "before=3 after=4 reload=3" in by_id["state-reverted-teacher"].title
    assert "before=3 after=3 reload=3" in by_id["state-actor-only-parent"].title


def test_findings_are_state_class_p1_with_a_replayable_repro(tmp_path: Path) -> None:
    findings = _matrix(tmp_path)
    for f in findings:
        assert f.finding_class is FindingClass.STATE_NOT_PERSISTED
        assert f.oracle is OracleName.STATE_AFTER
        assert priority_for(f.finding_class).value == "P1"
        assert f.steps[0] == "login teacher" and f.steps[-1] == "goto /inbox"
        assert "click #send" in f.steps and f.url_template == "/inbox"
    assert [f.role for f in findings if f.finding_id.endswith("-parent")] == ["parent"] * 2


def test_the_oracle_loads_every_reader_acts_once_then_reloads_every_reader(
        tmp_path: Path) -> None:
    port = StatePort({"c": "correct"})
    run(_context(tmp_path, [_probe("c", ["teacher", "parent"])], port))
    assert port.performed == ["teacher:goto /inbox", "parent:goto /inbox", "teacher:click #send",
                              "teacher:goto /inbox", "parent:goto /inbox"]


def test_a_wrong_sized_change_is_a_finding(tmp_path: Path) -> None:
    port = StatePort({"double": "double"})
    findings = run(_context(tmp_path, [_probe("double", ["teacher"])], port))
    assert len(findings) == 1
    assert "wrong_size" in findings[0].title and "before=3 after=5 reload=5" in findings[0].title
    assert findings[0].count == 1


def test_a_stale_non_actor_page_that_is_right_after_reload_is_clean(tmp_path: Path) -> None:
    port = StatePort({"correct": "correct"})
    assert run(_context(tmp_path, [_probe("correct", ["parent"])], port)) == []


class QueuePort:
    """A reader whose successive readings are scripted per role."""

    def __init__(self, readings: dict[str, list[str]], fail_observe: bool = False) -> None:
        self.readings = {k: list(v) for k, v in readings.items()}
        self.fail_observe = fail_observe

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        if self.fail_observe:
            raise ConnectionError("lost")
        return Observation(matched=True, detail=self.readings[assertion.observer_role_id].pop(0))


def _status_probe(readers: list[str]) -> StateProbe:
    return _probe("grade-status", readers, kind=ReaderKind.STATUS, expected_delta=None,
                  expected_state=ExpectedState(visible_text=["Published"], absent_text=["Draft"]))


def test_a_status_that_is_published_and_stays_published_is_clean(tmp_path: Path) -> None:
    port = QueuePort({"teacher": ["Draft", "Published", "Published"]})
    assert run(_context(tmp_path, [_status_probe(["teacher"])], port)) == []


def test_a_status_that_reverts_on_reload_is_not_persisted_and_cites_labels(tmp_path: Path) -> None:
    port = QueuePort({"teacher": ["Draft", "Published", "Draft for jo@example.org"]})
    (finding,) = run(_context(tmp_path, [_status_probe(["teacher"])], port))
    assert "not_persisted" in finding.title
    assert "before=none after=Published reload=none" in finding.title
    assert "example.org" not in finding.model_dump_json()


def test_an_unreadable_reader_is_a_finding_not_a_pass(tmp_path: Path) -> None:
    port = StatePort({"c": "correct"}, unreadable={"c"})
    (finding,) = run(_context(tmp_path, [_probe("c", ["teacher"])], port))
    assert "unreadable" in finding.title
    erroring = QueuePort({"teacher": []}, fail_observe=True)
    (finding,) = run(_context(tmp_path, [_status_probe(["teacher"])], erroring))
    assert "unreadable" in finding.title


def test_readings_are_numbers_only_never_the_page_text(tmp_path: Path) -> None:
    port = StatePort({"c": "correct"}, texts={"c": "3 unread from jo@example.org +91 98765 43210"})
    (finding,) = run(_context(tmp_path, [_probe("c", ["teacher"])], port))
    dumped = finding.model_dump_json()
    assert "example.org" not in dumped and "98765" not in dumped


def test_no_probe_file_means_nothing_to_check_and_no_port_is_an_error(tmp_path: Path) -> None:
    ctx = OracleContext(project_slug="demo", run_dir=str(tmp_path), scenario_id="s1",
                        port=StatePort({}))
    assert run(ctx) == []
    (tmp_path / PROBES_FILE).write_text("[]", encoding="utf-8")
    bare = OracleContext(project_slug="demo", run_dir=str(tmp_path), scenario_id="s1")
    with pytest.raises(RuntimeError):
        run(bare)


def test_a_failing_action_propagates_and_the_registry_reports_the_type_only(
        tmp_path: Path) -> None:
    class Broken(StatePort):
        def perform(self, step: RoleStep) -> None:
            if step.action.startswith("click"):
                raise RuntimeError("page text that must not be copied")

    ctx = _context(tmp_path, [_probe("c", ["teacher"])], Broken({"c": "correct"}))
    summary, findings = run_oracles(ctx, [OracleName.STATE_AFTER])
    status = next(s for s in summary.statuses if s.oracle is OracleName.STATE_AFTER)
    assert (status.state, status.reason, findings) == (OracleState.ERRORED, "RuntimeError", [])


def test_the_registry_runs_this_module_and_counts_its_findings(tmp_path: Path) -> None:
    ctx = _context(tmp_path, [_probe("actor-only", ["teacher", "parent"])],
                   StatePort({"actor-only": "actor_only"}))
    summary, found = run_oracles(ctx, [OracleName.STATE_AFTER])
    status = next(s for s in summary.statuses if s.oracle is OracleName.STATE_AFTER)
    assert (status.state, status.finding_count) == (OracleState.RAN, 1) and len(found) == 1
