"""T-209 (multi-role-platform.md MP7): leak and privilege findings are always P0.

The priority is a pure function of the finding class: no model input, no override argument, and
`MultiRoleFinding` carries no priority field a caller could set to anything else.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from autotester.schema.leak_evidence import LeakEvidence
from autotester.schema.multi_role_enums import FindingClass, Priority
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.stages import finding_priority
from autotester.stages.finding_priority import is_release_blocking, priority_for

LEAKY = (FindingClass.DATA_LEAK, FindingClass.PRIVILEGE_ESCALATION)


def _finding(cls: FindingClass, **over: object) -> MultiRoleFinding:
    fields: dict[str, object] = {
        "finding_id": f"f-{cls.value}", "finding_class": cls, "title": "Parent sees other rows",
        "role": "Parent", "platform_id": "parent", "url_template": "/students/{id}",
        "steps": ["login as Parent", "goto /students/{id}"], "count": 3}
    if cls is FindingClass.DATA_LEAK:
        fields["leak_evidence"] = LeakEvidence(
            foreign_row_count=3, field_names=["Name"], url_template="/students/{id}")
    return MultiRoleFinding(**{**fields, **over})


def _assert_every_leaky_class_is_p0() -> None:
    for cls in FindingClass:
        if cls in LEAKY:
            assert priority_for(cls) is Priority.P0, cls


@pytest.mark.parametrize("cls", list(FindingClass))
def test_priority_by_class_over_every_class(cls: FindingClass) -> None:
    if cls in LEAKY:
        assert priority_for(cls) is Priority.P0
        assert is_release_blocking(_finding(cls)) is True
    else:
        assert priority_for(cls) is not Priority.P0
        assert is_release_blocking(_finding(cls)) is False


def test_table_covers_every_class_so_a_new_class_forces_a_decision() -> None:
    assert set(FindingClass) == set(finding_priority.PRIORITY_BY_CLASS)
    assert frozenset(LEAKY) == finding_priority.LEAK_CLASSES


def test_there_is_no_model_input_and_no_override_argument() -> None:
    params = inspect.signature(priority_for).parameters
    assert list(params) == ["finding_class"]
    assert list(inspect.signature(is_release_blocking).parameters) == ["finding"]
    with pytest.raises(TypeError):
        priority_for(FindingClass.DATA_LEAK, Priority.P1)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        priority_for(FindingClass.DATA_LEAK, override=Priority.P1)  # type: ignore[call-arg]


def test_a_finding_cannot_carry_its_own_priority() -> None:
    with pytest.raises(ValidationError):
        _finding(FindingClass.DATA_LEAK, priority="P1")
    assert "priority" not in MultiRoleFinding.model_fields


def test_the_invariant_goes_red_when_one_class_is_lowered(monkeypatch: pytest.MonkeyPatch) -> None:
    _assert_every_leaky_class_is_p0()
    for cls in LEAKY:
        lowered = {**finding_priority.PRIORITY_BY_CLASS, cls: Priority.P1}
        monkeypatch.setattr(finding_priority, "PRIORITY_BY_CLASS", lowered)
        with pytest.raises(AssertionError):
            _assert_every_leaky_class_is_p0()
        monkeypatch.undo()
