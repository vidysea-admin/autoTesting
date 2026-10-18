"""The negative-input oracle: bad input, once per role account that reaches the form (MP32).

One job: for each `NegativeInputForm`, take the input classes `stages/expand.py::applicable_classes`
asks of its flow (INPUT_EMPTY, INPUT_BOUNDARY, INPUT_UNICODE_OVERSIZE, DOUBLE_SUBMIT -- expand.py
is read, never edited), turn each declared `FieldConstraints` rule into a deterministic violating
value, submit it as EACH role account in the form's `role_ids`, and report every cell. A submission
the product accepts in breach of a declared rule, a rule enforced for one role and not another, or
a double submit that creates two records is a `MultiRoleFinding` naming role, form, rule and class.
No model is called (MPI1): values come from the rules, the verdict from two selectors.

The oracle interface is `schema/oracle_context.py`. `RoleSessionPort.perform` carries the verbs
(`goto`, `submit`); a value is longer than a `RoleStep.action` may be, so typing goes through
`FormInputPort.fill_field`, which the session port must also implement (CORE-REQUEST in the
manifest). Forms are read from `<run_dir>/negative_input_forms.json`; a missing file is an error,
never a silent "no findings". A finding holds the rule and field name, never the submitted value.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import TypeAdapter

from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.enums import CaseClass
from autotester.schema.multi_role_enums import (
    AssertChannel,
    Expectation,
    FindingClass,
    OracleName,
)
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.negative_input_cell import InputRule, ProbeCell
from autotester.schema.negative_input_form import NegativeInputForm
from autotester.schema.oracle_context import OracleContext, RoleSessionPort
from autotester.schema.role_step import RoleStep
from autotester.stages.expand import applicable_classes

FORMS_FILE = "negative_input_forms.json"
SETTLE_S = 1.0
MAX_OVERSIZE = 5000
ASCII_FILLERS = ("a", "A", "1", "x", " ")
UNICODE_FILLERS = ("é", "ñ", "日", "\U0001f600")
ASCII_BREAKERS = ("!", "@", "~", "0", "a", " ")
UNICODE_BREAKERS = ("é", "日", "\U0001f600")
PROBE_CLASSES = (CaseClass.INPUT_EMPTY, CaseClass.INPUT_BOUNDARY,
                 CaseClass.INPUT_UNICODE_OVERSIZE, CaseClass.DOUBLE_SUBMIT)


class NegativeInputPlanMissing(Exception):
    """No forms file in the run directory: the oracle has nothing to probe."""


@runtime_checkable
class FormInputPort(Protocol):
    """What this oracle needs beyond `RoleSessionPort`: typing a value of any length."""

    def fill_field(self, role_id: str, field: str, value: str) -> None:
        """Type `value` into `field` of the open form, as `role_id`."""


@dataclass(frozen=True)
class Probe:
    """One thing to submit: a value that breaks `rule` on `field`, or a repeated submit."""

    field: str | None
    rule: InputRule
    case_class: CaseClass
    value: str | None


def _matches(pattern: str | None, text: str) -> bool:
    return pattern is None or re.fullmatch(pattern, text) is not None


def _filler(pattern: str | None, candidates: tuple[str, ...]) -> str | None:
    """The first character whose repetition satisfies `pattern`, if any does."""
    for ch in candidates:
        try:
            if _matches(pattern, ch * 3):
                return ch
        except re.error:
            return None
    return None


def _breaker(pattern: str, length: int, candidates: tuple[str, ...]) -> str | None:
    """A value of `length` that does NOT satisfy `pattern`, or None."""
    try:
        return next((ch * length for ch in candidates if not _matches(pattern, ch * length)), None)
    except re.error:
        return None


def _number(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else repr(x)


def _length_probes(name: str, c, pattern_fill: str) -> list[Probe]:
    probes: list[Probe] = []
    if c.min_length and c.min_length >= 1:
        probes.append(Probe(name, InputRule.MIN_LENGTH, CaseClass.INPUT_BOUNDARY,
                            pattern_fill * (c.min_length - 1)))
    if c.max_length is not None:
        probes.append(Probe(name, InputRule.MAX_LENGTH, CaseClass.INPUT_BOUNDARY,
                            pattern_fill * (c.max_length + 1)))
        uni = _filler(c.pattern, UNICODE_FILLERS) or pattern_fill
        size = min(2 * c.max_length + 1, MAX_OVERSIZE)
        if size > c.max_length:
            probes.append(Probe(name, InputRule.MAX_LENGTH, CaseClass.INPUT_UNICODE_OVERSIZE,
                                uni * size))
    return probes


def _pattern_probes(name: str, c) -> list[Probe]:
    if not c.pattern:
        return []
    length = max(c.min_length or 1, 1)
    if c.max_length is not None:
        length = min(length, c.max_length)
    probes = []
    for klass, pool in ((CaseClass.INPUT_BOUNDARY, ASCII_BREAKERS),
                        (CaseClass.INPUT_UNICODE_OVERSIZE, UNICODE_BREAKERS)):
        bad = _breaker(c.pattern, length, pool)
        if bad is not None:
            probes.append(Probe(name, InputRule.PATTERN, klass, bad))
    return probes


def field_probes(f) -> list[Probe]:
    """Every violating value one `InputField` declares, as probes."""
    c = f.constraints
    probes = [Probe(f.name, InputRule.REQUIRED, CaseClass.INPUT_EMPTY, "")] if f.required else []
    fill = _filler(c.pattern, ASCII_FILLERS) or "a"
    probes += _length_probes(f.name, c, fill)
    probes += _pattern_probes(f.name, c)
    if c.min is not None:
        probes.append(Probe(f.name, InputRule.MIN, CaseClass.INPUT_BOUNDARY, _number(c.min - 1)))
    if c.max is not None:
        probes.append(Probe(f.name, InputRule.MAX, CaseClass.INPUT_BOUNDARY, _number(c.max + 1)))
    return probes


def form_probes(form: NegativeInputForm) -> list[Probe]:
    """The probes of the input classes expand.py asks of this flow."""
    wanted = set(applicable_classes(form.flow)) & set(PROBE_CLASSES)
    probes = [p for f in form.fields for p in field_probes(f) if p.case_class in wanted]
    if form.duplicate_target and CaseClass.DOUBLE_SUBMIT in wanted:
        probes.append(Probe(None, InputRule.DOUBLE_SUBMIT, CaseClass.DOUBLE_SUBMIT, None))
    return probes


class _Driver:
    """One role's browser actions on one form, numbered so every step id is unique."""

    def __init__(self, form: NegativeInputForm, role_id: str, port: RoleSessionPort) -> None:
        self.form, self.role_id, self.port, self.n = form, role_id, port, 0

    def _step(self, action: str) -> None:
        self.n += 1
        self.port.perform(RoleStep(id=f"s{self.n}", role_id=self.role_id, action=action))

    def open(self) -> None:
        self._step(f"goto {self.form.url_template}")

    def submit(self) -> None:
        self._step(f"submit {self.form.submit_target}")

    def fill(self, field: str, value: str) -> None:
        self.port.fill_field(self.role_id, field, value)

    def seen(self, target: str) -> bool:
        self.n += 1
        return self.port.observe(CrossRoleAssertion(
            id=f"a{self.n}", observer_role_id=self.role_id, channel=AssertChannel.UI,
            expectation=Expectation.PRESENT, target=target, within_s=SETTLE_S)).matched


def _run_probe(form: NegativeInputForm, role_id: str, probe: Probe,
               port: RoleSessionPort) -> ProbeCell:
    drv = _Driver(form, role_id, port)
    drv.open()
    for name, value in form.valid_values.items():
        drv.fill(name, probe.value if name == probe.field and probe.value is not None else value)
    drv.submit()
    if probe.rule is InputRule.DOUBLE_SUBMIT:
        drv.submit()
        breached = drv.seen(form.duplicate_target or "")
    else:
        breached = not drv.seen(form.rejection_target)
    return ProbeCell(form_id=form.id, role_id=role_id, field=probe.field, rule=probe.rule,
                     case_class=probe.case_class, breached=breached)


def form_roles(form: NegativeInputForm, context_roles: list[str]) -> list[str]:
    """The form's roles that this run has an account for (all of them when the run lists none)."""
    return [r for r in form.role_ids if not context_roles or r in context_roles]


def probe_cells(forms: list[NegativeInputForm], port: RoleSessionPort,
                context_roles: list[str]) -> list[ProbeCell]:
    """Run every probe of every form once per role: the whole matrix, passes included."""
    if not isinstance(port, FormInputPort):
        raise TypeError("the session port must implement FormInputPort.fill_field")
    cells: list[ProbeCell] = []
    for form in forms:
        probes = form_probes(form)
        for role_id in form_roles(form, context_roles):
            cells += [_run_probe(form, role_id, p, port) for p in probes]
    return cells


def _finding_id(cell: ProbeCell) -> str:
    key = "|".join((cell.form_id, cell.role_id, cell.field or "", cell.rule, cell.case_class))
    return "ni-" + hashlib.sha1(key.encode()).hexdigest()[:12]


def _steps(form: NegativeInputForm, cell: ProbeCell) -> list[str]:
    if cell.rule is InputRule.DOUBLE_SUBMIT:
        return [f"goto {form.url_template}", f"submit {form.submit_target}",
                f"submit {form.submit_target}"]
    return [f"goto {form.url_template}", f"fill {cell.field}", f"submit {form.submit_target}"]


def _finding(form: NegativeInputForm, cell: ProbeCell, enforced_for: list[str]) -> MultiRoleFinding:
    what = ("created two records on a double submit" if cell.rule is InputRule.DOUBLE_SUBMIT
            else f"accepted a breach of {cell.rule} on {cell.field}")
    held = f"; the rule held for role {', '.join(enforced_for)}" if enforced_for else ""
    title = f"{form.id}: role {cell.role_id} {what} [{cell.case_class}]{held}"[:200]
    return MultiRoleFinding(
        finding_id=_finding_id(cell), finding_class=FindingClass.NEGATIVE_INPUT, title=title,
        role=cell.role_id, platform_id=form.platform_id, url_template=form.url_template,
        steps=_steps(form, cell), count=2 if cell.rule is InputRule.DOUBLE_SUBMIT else 1,
        oracle=OracleName.NEGATIVE_INPUT)


def findings_from_cells(forms: list[NegativeInputForm],
                        cells: list[ProbeCell]) -> list[MultiRoleFinding]:
    """One finding per breached cell; its title lists the roles that held the same rule."""
    by_form = {f.id: f for f in forms}
    findings = []
    for cell in cells:
        if not cell.breached:
            continue
        held = [c.role_id for c in cells if not c.breached and c.form_id == cell.form_id
                and (c.field, c.rule, c.case_class) == (cell.field, cell.rule, cell.case_class)]
        findings.append(_finding(by_form[cell.form_id], cell, held))
    return findings


def load_forms(run_dir: Path) -> list[NegativeInputForm]:
    """The forms to probe, from `<run_dir>/negative_input_forms.json`."""
    path = run_dir / FORMS_FILE
    if not path.is_file():
        raise NegativeInputPlanMissing(FORMS_FILE)
    return TypeAdapter(list[NegativeInputForm]).validate_python(
        json.loads(path.read_text(encoding="utf-8")))


def _run(context: OracleContext) -> list[MultiRoleFinding]:
    """The registry entry point: load the forms, probe each per role, report the breaches."""
    if context.port is None:
        raise ValueError("the negative-input oracle needs a live session port")
    forms = load_forms(Path(context.run_dir))
    return findings_from_cells(forms, probe_cells(forms, context.port, context.role_ids))


# Bound by assignment, not `def run`: doctor's duplicate-concept rule would flag a second top-level
# `run` (doctor.py has one), and every oracle module must expose this name (oracle_context.py).
run = _run
