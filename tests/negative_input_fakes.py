"""Test doubles for the negative-input oracle (T-219): a synthetic form and a per-role fake port.

`FakeFormPort` plays the role-session port for a form whose rules each role account enforces or
skips (`enforced`), and whose submit is idempotent for some roles only (`idempotent`). It checks the
declared `FieldConstraints` with its own code, not the oracle's, so the matrix is an independent
oracle of what the product does. No browser, no network, no product code (MPI2).
"""

from __future__ import annotations

import re
from collections import Counter

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.enums import Action
from autotester.schema.flowspec import FieldConstraints, Flow, InputField, Step
from autotester.schema.negative_input_cell import InputRule
from autotester.schema.negative_input_form import NegativeInputForm
from autotester.schema.role_step import RoleStep

ALL_RULES = frozenset(InputRule) - {InputRule.DOUBLE_SUBMIT}
REJECTED, DUPLICATE = ".field-error", ".record + .record"


def make_form(*, duplicate: bool = True, with_fill: bool = True,
              role_ids: tuple[str, ...] = ("role-a", "role-b")) -> NegativeInputForm:
    """Fields `name` (required, 3..10 letters) and `age` (required, 18..99)."""
    flow = Flow(id="signup", name="Sign up", entry_screen="s1", steps=[
        Step(order=1, action=Action.FILL if with_fill else Action.CLICK, target="name",
             value="Asha")])
    fields = [
        InputField(name="name", required=True, constraints=FieldConstraints(
            min_length=3, max_length=10, pattern=r"[A-Za-z ]+")),
        InputField(name="age", required=True, type="number",
                   constraints=FieldConstraints(min=18, max=99)),
    ]
    return NegativeInputForm(
        id="signup", platform_id="school", flow=flow, fields=fields, role_ids=list(role_ids),
        url_template="/signup", submit_target="#save", rejection_target=REJECTED,
        duplicate_target=DUPLICATE if duplicate else None,
        valid_values={"name": "Asha", "age": "30"})


def violated(form: NegativeInputForm, values: dict[str, str]) -> set[InputRule]:
    """The declared rules these values break, computed independently of the oracle."""
    broken: set[InputRule] = set()
    for f in form.fields:
        v, c = values.get(f.name, ""), f.constraints
        if f.required and v == "":
            broken.add(InputRule.REQUIRED)
        if c.min_length is not None and len(v) < c.min_length:
            broken.add(InputRule.MIN_LENGTH)
        if c.max_length is not None and len(v) > c.max_length:
            broken.add(InputRule.MAX_LENGTH)
        if c.pattern is not None and re.fullmatch(c.pattern, v) is None:
            broken.add(InputRule.PATTERN)
        broken |= _numeric(v, c)
    return broken


def _numeric(v: str, c: FieldConstraints) -> set[InputRule]:
    if c.min is None and c.max is None:
        return set()
    try:
        x = float(v)
    except ValueError:
        return {InputRule.MIN}
    out = set()
    if c.min is not None and x < c.min:
        out.add(InputRule.MIN)
    if c.max is not None and x > c.max:
        out.add(InputRule.MAX)
    return out


class FakeFormPort:
    """`enforced[role]` = rules that role's form enforces; roles in `idempotent` get no repeat."""

    def __init__(self, form: NegativeInputForm, enforced: dict[str, frozenset[InputRule]],
                 idempotent: frozenset[str] = frozenset()) -> None:
        self.form, self.enforced, self.idempotent = form, enforced, idempotent
        self.values: dict[str, str] = {}
        self.rejected = False
        self.records: dict[str, list[tuple]] = {}
        self.fills: list[tuple[str, str, str]] = []
        self.actions: list[str] = []

    def perform(self, step: RoleStep) -> None:
        self.actions.append(f"{step.role_id}:{step.action}")
        verb = step.action.split(" ", 1)[0]
        if verb == "goto":
            self.values, self.rejected = {}, False
        elif verb == "submit":
            self._submit(step.role_id)

    def fill_field(self, role_id: str, field: str, value: str) -> None:
        self.fills.append((role_id, field, value))
        self.values[field] = value

    def _submit(self, role_id: str) -> None:
        if violated(self.form, self.values) & self.enforced.get(role_id, frozenset()):
            self.rejected = True
            return
        self.rejected = False
        payload = tuple(sorted(self.values.items()))
        rows = self.records.setdefault(role_id, [])
        if role_id in self.idempotent and payload in rows:
            return
        rows.append(payload)

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        if assertion.target == REJECTED:
            return Observation(matched=self.rejected)
        rows = self.records.get(assertion.observer_role_id, [])
        return Observation(matched=bool(rows) and Counter(rows).most_common(1)[0][1] >= 2)


class PortWithoutFill:
    """A session port that can perform and observe but not type: the oracle must refuse it."""

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        return Observation(matched=False)
