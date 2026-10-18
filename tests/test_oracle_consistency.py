"""T-215 (multi-role-platform.md MP23, MPI1, MPI2): the same entity read as N roles.

A scripted port plays the session: each (role, selector) shows a fixed text, or nothing. All values
are synthetic. The oracle must report a field the roles disagree about by value CLASS, skip a
declared role-specific field, and never write or return the raw text.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.entity_reading import EntityField, EntityHandle, FieldReading, ValueClass
from autotester.schema.multi_role_enums import FindingClass, OracleName, Priority
from autotester.schema.multi_role_finding import MultiRoleFinding, parse_repro_step
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.role_step import RoleStep
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_consistency import (
    HANDLES_FILE,
    check_entity,
    classify_value,
    run,
)
from autotester.stages.oracle_registry import run_oracles

STATUS = "#status"
NAME = "#name"
VOCAB = ["Pending", "Approved", "Rejected"]


class ReaderPort:
    """`shown[(role, selector)]` is the text on screen; absent key = the element is not there."""

    def __init__(self, shown: dict[tuple[str, str], str]) -> None:
        self.shown = shown
        self.performed: list[tuple[str, str]] = []

    def perform(self, step: RoleStep) -> None:
        self.performed.append((step.role_id, step.action))

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        text = self.shown.get((assertion.observer_role_id, assertion.target))
        return Observation(matched=text is not None, detail=text or "")


def handle(*, roles=("student", "parent"), fields=None) -> EntityHandle:
    fields = fields or [EntityField(name="status", selector=STATUS)]
    return EntityHandle(id="application", platform_id="portal", url_template="/applications/{id}",
                        open_action="goto /applications/{id}", roles=list(roles), fields=fields,
                        vocabulary=VOCAB)


def test_mp23_parent_sees_a_stale_status_is_a_finding_naming_each_roles_class():
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "Pending"})
    found = check_entity(handle(), port)
    assert len(found) == 1
    f = found[0]
    assert f.finding_class is FindingClass.ROLE_INCONSISTENCY and f.oracle is OracleName.CONSISTENCY
    assert "student=vocabulary:Approved" in f.title and "parent=vocabulary:Pending" in f.title
    assert f.role == "student" and f.platform_id == "portal" and f.count == 1
    assert priority_for(f.finding_class) is Priority.P1


def test_each_role_opens_the_entity_before_it_is_read():
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "Approved"})
    check_entity(handle(), port)
    assert port.performed == [("student", "goto /applications/{id}"),
                              ("parent", "goto /applications/{id}")]


def test_roles_that_agree_produce_no_finding_even_when_case_and_spacing_differ():
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "  approved "})
    assert check_entity(handle(), port) == []


def test_a_declared_role_specific_field_may_differ():
    fields = [EntityField(name="status", selector=STATUS),
              EntityField(name="note", selector="#note", role_specific=True)]
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "Approved",
                       ("student", "#note"): "your own note", ("parent", "#note"): "parent view"})
    assert check_entity(handle(fields=fields), port) == []


def test_only_the_undeclared_field_is_reported_when_two_differ():
    fields = [EntityField(name="status", selector=STATUS),
              EntityField(name="note", selector="#note", role_specific=True)]
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "Pending",
                       ("student", "#note"): "a", ("parent", "#note"): "b"})
    found = check_entity(handle(fields=fields), port)
    assert [f.finding_id for f in found] == ["consistency-application-status"]


def test_an_element_one_role_cannot_see_is_reported_as_missing():
    port = ReaderPort({("student", STATUS): "Approved"})
    f = check_entity(handle(), port)[0]
    assert "parent=missing" in f.title and "student=vocabulary:Approved" in f.title


def test_three_roles_the_odd_one_out_is_counted():
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "Pending",
                       ("teacher", STATUS): "Approved"})
    f = check_entity(handle(roles=("student", "parent", "teacher")), port)[0]
    assert f.count == 1
    assert len(f.steps) == 6 and parse_repro_step(f.steps[0])[1] == "student"


CANARY_NAME = "Zephyrina Quillfeather"
CANARY_OTHER = "Orlando Brackenridge"
CANARY_MAIL = "canary.person@example.invalid"
CANARY_PHONE = "+91 98765 43210"


@pytest.mark.parametrize(("a", "b", "classes"), [
    (CANARY_NAME, CANARY_OTHER, ("text_short", "text_short")),
    (CANARY_MAIL, "other.person@example.invalid", ("email", "email")),
    (CANARY_PHONE, "", ("phone", "empty")),
])
def test_mpi1_personal_values_are_reported_by_class_and_never_stored(tmp_path, a, b, classes):
    fields = [EntityField(name="person", selector=NAME)]
    port = ReaderPort({("student", NAME): a, ("parent", NAME): b})
    found = check_entity(handle(fields=fields), port)
    assert len(found) == 1
    blob = found[0].model_dump_json()
    for secret in (a, b):
        if secret:
            assert secret not in blob
    assert f"student={classes[0]}" in found[0].title and f"parent={classes[1]}" in found[0].title
    (tmp_path / "f.json").write_text(blob, "utf-8")
    assert all(s not in (tmp_path / "f.json").read_text("utf-8") for s in (a, b) if s)


@pytest.mark.parametrize(("text", "expected"), [
    (None, ValueClass.MISSING), ("   ", ValueClass.EMPTY), ("PENDING", ValueClass.VOCABULARY),
    ("x@y.example", ValueClass.EMAIL), ("2026-10-18", ValueClass.DATE),
    ("18 Oct 2026", ValueClass.DATE), ("+91 98765 43210", ValueClass.PHONE),
    ("1,234.50", ValueClass.NUMBER), ("85%", ValueClass.NUMBER),
    ("Short name", ValueClass.TEXT_SHORT),
    ("a long free text description of the thing", ValueClass.TEXT_LONG),
])
def test_value_class_matrix(text, expected):
    assert classify_value(text, VOCAB)[0] is expected


def test_only_a_declared_label_is_ever_named():
    assert classify_value("Approved", VOCAB) == (ValueClass.VOCABULARY, "Approved")
    assert classify_value("Approved", []) == (ValueClass.TEXT_SHORT, None)


def test_a_reading_cannot_carry_a_label_unless_it_is_vocabulary():
    with pytest.raises(ValidationError):
        FieldReading(field="x", role_id="parent", value_class=ValueClass.EMAIL, label="a@b.co")


@pytest.mark.parametrize("bad", [
    {"url_template": "/applications/12345"}, {"roles": ["student"]}, {"roles": ["a", "a"]},
    {"vocabulary": ["pat@example.invalid"]}, {"open_action": "teleport /x"},
    {"extra_field": 1}, {"fields": []},
])
def test_handle_schema_is_closed(bad):
    base = {"id": "application", "platform_id": "portal", "url_template": "/a/{id}",
            "open_action": "goto /a/{id}", "roles": ["student", "parent"],
            "fields": [{"name": "status", "selector": STATUS}]}
    with pytest.raises((ValidationError, ValueError)):
        EntityHandle(**{**base, **bad})


def _write_handles(run_dir: Path, h: EntityHandle) -> None:
    path = run_dir / HANDLES_FILE
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([h.model_dump(mode="json")]), "utf-8")


def _context(run_dir: Path, port, roles=("student", "parent")) -> OracleContext:
    return OracleContext(project_slug="demo", run_dir=str(run_dir), scenario_id="s1",
                         role_ids=list(roles), platform_ids=["portal"], port=port)


def test_run_reads_the_handles_file_and_stores_nothing_new(tmp_path):
    _write_handles(tmp_path, handle())
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "Pending"})
    before = sorted(p.name for p in tmp_path.rglob("*"))
    found = run(_context(tmp_path, port))
    assert [f.finding_id for f in found] == ["consistency-application-status"]
    assert isinstance(found[0], MultiRoleFinding)
    assert sorted(p.name for p in tmp_path.rglob("*")) == before


def test_run_with_no_handles_declared_finds_nothing_and_needs_no_port(tmp_path):
    assert run(_context(tmp_path, None)) == []


def test_run_refuses_a_role_that_is_not_in_the_scenario(tmp_path):
    _write_handles(tmp_path, handle())
    with pytest.raises(ValueError):
        run(_context(tmp_path, ReaderPort({}), roles=("student",)))


def test_through_the_registry_the_oracle_is_ran_with_its_count(tmp_path):
    _write_handles(tmp_path, handle())
    port = ReaderPort({("student", STATUS): "Approved", ("parent", STATUS): "Pending"})
    summary, findings = run_oracles(_context(tmp_path, port), [OracleName.CONSISTENCY])
    row = next(s for s in summary.statuses if s.oracle is OracleName.CONSISTENCY)
    assert (row.state, row.finding_count, len(findings)) == (OracleState.RAN, 1, 1)


def test_a_broken_port_is_errored_by_type_only_not_swallowed(tmp_path):
    class Broken(ReaderPort):
        def observe(self, assertion):
            raise ConnectionError(f"page said {CANARY_NAME}")

    _write_handles(tmp_path, handle())
    summary, _ = run_oracles(_context(tmp_path, Broken({})), [OracleName.CONSISTENCY])
    row = next(s for s in summary.statuses if s.oracle is OracleName.CONSISTENCY)
    assert row.state is OracleState.ERRORED and CANARY_NAME not in (row.reason or "")
