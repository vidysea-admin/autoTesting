"""T-219 (multi-role-platform.md MP32): negative input runs once per role that reaches the form.

A synthetic form with a rule matrix (required, min and max length, pattern, numeric range) is
enforced for `role-a` and mostly skipped for `role-b`, plus a non-idempotent submit for `role-b`.
Every matrix cell is asserted, passes included, so dropping the per-role loop turns role-b's cells
red. The fake port checks the declared constraints with its own code (negative_input_fakes.py).
"""

from __future__ import annotations

import json

import pytest
from negative_input_fakes import FakeFormPort, PortWithoutFill, make_form
from pydantic import ValidationError

from autotester.schema.enums import CaseClass
from autotester.schema.flowspec import FieldConstraints, InputField
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.negative_input_cell import InputRule
from autotester.schema.negative_input_form import NegativeInputForm
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.stages.oracle_negative_input import (
    FORMS_FILE,
    field_probes,
    findings_from_cells,
    form_probes,
    probe_cells,
    run,
)
from autotester.stages.oracle_registry import run_oracles

R = InputRule
C = CaseClass
ALL = frozenset(InputRule) - {R.DOUBLE_SUBMIT}
B_ENFORCES = frozenset({R.REQUIRED, R.MIN_LENGTH})

# (field, rule, class) of every cell one role produces on the fixture form.
MATRIX = [
    ("name", R.REQUIRED, C.INPUT_EMPTY),
    ("name", R.MIN_LENGTH, C.INPUT_BOUNDARY),
    ("name", R.MAX_LENGTH, C.INPUT_BOUNDARY),
    ("name", R.MAX_LENGTH, C.INPUT_UNICODE_OVERSIZE),
    ("name", R.PATTERN, C.INPUT_BOUNDARY),
    ("name", R.PATTERN, C.INPUT_UNICODE_OVERSIZE),
    ("age", R.REQUIRED, C.INPUT_EMPTY),
    ("age", R.MIN, C.INPUT_BOUNDARY),
    ("age", R.MAX, C.INPUT_BOUNDARY),
    (None, R.DOUBLE_SUBMIT, C.DOUBLE_SUBMIT),
]


def _port(form=None, **kw) -> FakeFormPort:
    form = form or make_form()
    return FakeFormPort(form, {"role-a": ALL, "role-b": B_ENFORCES},
                        kw.get("idempotent", frozenset({"role-a"})))


def _matrix(cells) -> dict:
    return {(c.role_id, c.field, c.rule, c.case_class): c.breached for c in cells}


def test_mp32_every_cell_of_the_rule_matrix_is_asserted_for_both_roles() -> None:
    form = make_form()
    cells = probe_cells([form], _port(form), [])
    expect = {}
    for role in ("role-a", "role-b"):
        for field, rule, klass in MATRIX:
            if rule is R.DOUBLE_SUBMIT:
                expect[(role, field, rule, klass)] = role == "role-b"
            else:
                expect[(role, field, rule, klass)] = role == "role-b" and rule not in B_ENFORCES
    assert len(cells) == 20
    assert _matrix(cells) == expect


def test_mp32_role_a_is_clean_and_role_b_gets_one_finding_per_skipped_cell() -> None:
    form = make_form()
    findings = findings_from_cells([form], probe_cells([form], _port(form), []))
    assert {f.role for f in findings} == {"role-b"}
    assert len(findings) == 7  # 6 skipped rules/classes + the double submit
    assert all(f.finding_class is FindingClass.NEGATIVE_INPUT for f in findings)
    assert all(f.oracle is OracleName.NEGATIVE_INPUT for f in findings)
    assert all(f.platform_id == "school" for f in findings)
    assert len({f.finding_id for f in findings}) == 7


def test_mp32_a_finding_names_role_form_rule_and_class() -> None:
    form = make_form()
    findings = findings_from_cells([form], probe_cells([form], _port(form), []))
    pattern = next(f for f in findings
                   if "pattern" in f.title and "unicode_oversize" in f.title)
    assert "role role-b" in pattern.title
    assert "signup" in pattern.title
    assert "on name" in pattern.title
    assert "the rule held for role role-a" in pattern.title
    assert pattern.steps == ["goto /signup", "fill name", "submit #save"]
    assert pattern.count == 1


def test_mp32_double_submit_creating_two_records_is_a_finding_with_count_two() -> None:
    form = make_form()
    findings = findings_from_cells([form], probe_cells([form], _port(form), []))
    dup = [f for f in findings if "double submit" in f.title]
    assert [f.role for f in dup] == ["role-b"]
    assert dup[0].count == 2
    assert dup[0].steps == ["goto /signup", "submit #save", "submit #save"]


def test_mp32_a_rule_enforced_for_every_role_gives_no_finding() -> None:
    form = make_form()
    port = FakeFormPort(form, {"role-a": ALL, "role-b": ALL}, frozenset({"role-a", "role-b"}))
    cells = probe_cells([form], port, [])
    assert len(cells) == 20
    assert not any(c.breached for c in cells)
    assert findings_from_cells([form], cells) == []


def test_mp32_the_per_role_loop_visits_each_role_with_the_same_probes() -> None:
    form = make_form()
    port = _port(form)
    probe_cells([form], port, [])
    by_role = {r: [f for f in port.fills if f[0] == r] for r in ("role-a", "role-b")}
    assert by_role["role-a"]
    assert [(f, v) for _, f, v in by_role["role-a"]] == [(f, v) for _, f, v in by_role["role-b"]]


def test_mp32_a_role_the_run_has_no_account_for_is_not_probed() -> None:
    form = make_form()
    cells = probe_cells([form], _port(form), ["role-a"])
    assert {c.role_id for c in cells} == {"role-a"}


def test_probe_values_sit_on_the_declared_boundaries() -> None:
    by = {(p.field, p.rule, p.case_class): p.value for p in form_probes(make_form())}
    assert by[("name", R.REQUIRED, C.INPUT_EMPTY)] == ""
    assert len(by[("name", R.MIN_LENGTH, C.INPUT_BOUNDARY)]) == 2
    assert len(by[("name", R.MAX_LENGTH, C.INPUT_BOUNDARY)]) == 11
    assert len(by[("name", R.MAX_LENGTH, C.INPUT_UNICODE_OVERSIZE)]) > 10
    assert by[("age", R.MIN, C.INPUT_BOUNDARY)] == "17"
    assert by[("age", R.MAX, C.INPUT_BOUNDARY)] == "100"
    assert not by[("name", R.PATTERN, C.INPUT_BOUNDARY)].isalpha()
    assert not by[("name", R.PATTERN, C.INPUT_UNICODE_OVERSIZE)].isascii()


def test_a_field_with_no_pattern_gets_a_unicode_oversized_value() -> None:
    f = InputField(name="bio", constraints=FieldConstraints(max_length=5))
    probes = {(p.rule, p.case_class): p.value for p in field_probes(f)}
    value = probes[(R.MAX_LENGTH, C.INPUT_UNICODE_OVERSIZE)]
    assert len(value) > 5 and not value.isascii()
    assert len(probes[(R.MAX_LENGTH, C.INPUT_BOUNDARY)]) == 6


def test_only_the_classes_expand_py_asks_of_the_flow_are_probed() -> None:
    no_fill = form_probes(make_form(with_fill=False))
    assert [p.case_class for p in no_fill] == [C.DOUBLE_SUBMIT]
    no_dup = form_probes(make_form(duplicate=False))
    assert C.DOUBLE_SUBMIT not in {p.case_class for p in no_dup}
    assert len(no_dup) == 9


def test_mpi1_findings_never_hold_a_submitted_or_valid_value() -> None:
    form = make_form()
    port = _port(form)
    findings = findings_from_cells([form], probe_cells([form], port, []))
    text = json.dumps([f.model_dump(mode="json") for f in findings], ensure_ascii=False)
    submitted = {v for _, _, v in port.fills if v}
    assert not any(v in text for v in submitted if len(v) > 2)
    assert "Asha" not in text
    assert "é" not in text


def test_run_through_the_registry_reports_ran_with_the_finding_count(tmp_path) -> None:
    form = make_form()
    (tmp_path / FORMS_FILE).write_text(json.dumps([form.model_dump(mode="json")]), encoding="utf-8")
    ctx = OracleContext(project_slug="p", run_dir=str(tmp_path), scenario_id="s",
                        role_ids=["role-a", "role-b"], platform_ids=["school"], port=_port(form))
    summary, findings = run_oracles(ctx, [OracleName.NEGATIVE_INPUT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.NEGATIVE_INPUT)
    assert (status.state, status.finding_count) == (OracleState.RAN, 7)
    assert len(findings) == 7


def test_no_forms_file_is_an_error_not_a_clean_run(tmp_path) -> None:
    ctx = OracleContext(project_slug="p", run_dir=str(tmp_path), scenario_id="s", port=_port())
    summary, _ = run_oracles(ctx, [OracleName.NEGATIVE_INPUT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.NEGATIVE_INPUT)
    assert (status.state, status.reason) == (OracleState.ERRORED, "NegativeInputPlanMissing")


def test_a_port_that_cannot_type_is_refused(tmp_path) -> None:
    form = make_form()
    (tmp_path / FORMS_FILE).write_text(json.dumps([form.model_dump(mode="json")]), encoding="utf-8")
    ctx = OracleContext(project_slug="p", run_dir=str(tmp_path), scenario_id="s",
                        port=PortWithoutFill())
    with pytest.raises(TypeError):
        run(ctx)


def test_the_form_schema_is_closed() -> None:
    good = make_form().model_dump(mode="json")
    with pytest.raises(ValidationError):
        NegativeInputForm.model_validate({**good, "surprise": 1})
    with pytest.raises(ValidationError):
        NegativeInputForm.model_validate({**good, "valid_values": {"name": "Asha"}})
    with pytest.raises(ValidationError):
        NegativeInputForm.model_validate(
            {**good, "valid_values": {"name": "Asha", "age": "a.b@example.com"}})
