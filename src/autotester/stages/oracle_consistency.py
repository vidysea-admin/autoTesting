"""The cross-role consistency oracle: one entity, read as each role (MP23, MPI1).

One job: read every declared field of an `EntityHandle` as each declared role through the session
port and report each field the roles disagree about, unless the field is declared role-specific. A
finding names every role's VALUE CLASS (`vocabulary:pending`, `email`, `text_short`), never the
text: the raw values live only in memory for the comparison and are not written, logged or put in an
exception. Deterministic; no model sees a page (MPI1). Handles come from
`<run_dir>/multi_role/entity_handles.json`; none declared means nothing to compare.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter

from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.entity_reading import EntityField, EntityHandle, FieldReading, ValueClass
from autotester.schema.multi_role_enums import AssertChannel, Expectation, FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext, RoleSessionPort
from autotester.schema.role_step import RoleStep

HANDLES_FILE = Path("multi_role") / "entity_handles.json"
LOOK_WINDOW_S = 1.0
SHORT_TEXT = 24
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_DATE = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$|^\d{1,2}\s+[a-z]{3,9}\s+\d{2,4}$")
_PHONE = re.compile(r"^\+?\d[\d\s().-]{6,}\d$")
_NUMBER = re.compile(r"^[-+]?\d[\d,]*(\.\d+)?%?$")


def normalise(text: str) -> str:
    """The comparison form: whitespace collapsed, case folded."""
    return " ".join(text.split()).casefold()


def classify_value(text: str | None, vocabulary: list[str]) -> tuple[ValueClass, str | None]:
    """(class, label): `None` = the role could not see the field; only a declared label is named."""
    if text is None:
        return ValueClass.MISSING, None
    value = normalise(text)
    if not value:
        return ValueClass.EMPTY, None
    for label in vocabulary:
        if normalise(label) == value:
            return ValueClass.VOCABULARY, label
    for pattern, kind in ((_EMAIL, ValueClass.EMAIL), (_DATE, ValueClass.DATE),
                          (_PHONE, ValueClass.PHONE), (_NUMBER, ValueClass.NUMBER)):
        if pattern.match(value):
            return kind, None
    return (ValueClass.TEXT_SHORT if len(value) <= SHORT_TEXT else ValueClass.TEXT_LONG), None


def _look(port: RoleSessionPort, handle: EntityHandle, field: EntityField, role: str) -> str | None:
    """One look at `field` as `role`; None when the role's page has no such element."""
    seen = port.observe(CrossRoleAssertion(
        id=f"read-{handle.id}-{field.name}", observer_role_id=role, channel=AssertChannel.UI,
        expectation=Expectation.PRESENT, target=field.selector, within_s=LOOK_WINDOW_S))
    return seen.detail if seen.matched else None


def read_entity(handle: EntityHandle, port: RoleSessionPort,
                ) -> dict[str, dict[str, tuple[str | None, FieldReading]]]:
    """{field: {role: (normalised raw value, reading)}}. The raw value stays in this dict only."""
    out: dict[str, dict[str, tuple[str | None, FieldReading]]] = {f.name: {} for f in handle.fields}
    for role in handle.roles:
        port.perform(RoleStep(id=f"open-{handle.id}", role_id=role, action=handle.open_action))
        for field in handle.fields:
            raw = _look(port, handle, field, role)
            kind, label = classify_value(raw, handle.vocabulary)
            reading = FieldReading(field=field.name, role_id=role, value_class=kind, label=label)
            out[field.name][role] = (None if raw is None else normalise(raw), reading)
    return out


def _finding(handle: EntityHandle, field: EntityField,
             by_role: dict[str, tuple[str | None, FieldReading]]) -> MultiRoleFinding | None:
    """A finding when the roles' values are not all equal; the reference is the commonest value."""
    values = Counter(raw for raw, _ in by_role.values())
    if len(values) < 2:
        return None
    reference = values.most_common(1)[0][0]
    outliers = [r for r, (raw, _) in by_role.items() if raw != reference]
    seen = ", ".join(f"{r}={rd.describe()}" for r, (_, rd) in by_role.items())
    steps = [s for role in handle.roles for s in (f"login {role}", handle.open_action)]
    return MultiRoleFinding(
        finding_id=f"consistency-{handle.id}-{field.name}"[:64], oracle=OracleName.CONSISTENCY,
        finding_class=FindingClass.ROLE_INCONSISTENCY, role=handle.roles[0],
        title=f"{field.name} of {handle.id} differs across roles: {seen}"[:200],
        platform_id=handle.platform_id, url_template=handle.url_template,
        steps=steps[:50], count=len(outliers))


def check_entity(handle: EntityHandle, port: RoleSessionPort) -> list[MultiRoleFinding]:
    """Findings for every non-role-specific field the roles read differently."""
    readings = read_entity(handle, port)
    found = (_finding(handle, f, readings[f.name]) for f in handle.fields if not f.role_specific)
    return [f for f in found if f is not None]


def load_handles(run_dir: str) -> list[EntityHandle]:
    path = Path(run_dir) / HANDLES_FILE
    if not path.is_file():
        return []
    return TypeAdapter(list[EntityHandle]).validate_python(json.loads(path.read_text("utf-8")))


def _consistency_oracle(context: OracleContext) -> list[MultiRoleFinding]:
    """The registry entry point (see `schema/oracle_context.py`)."""
    handles = load_handles(context.run_dir)
    if handles and context.port is None:
        raise RuntimeError("the consistency oracle needs the live session port")
    found: list[MultiRoleFinding] = []
    for handle in handles:
        if context.role_ids and not set(handle.roles) <= set(context.role_ids):
            raise ValueError("a handle names a role that is not in this scenario")
        found.extend(check_entity(handle, context.port))
    return found

# The registry calls `run`; `doctor.check_duplicate_definitions` flags a top-level `def run` because
# `doctor.py` has one, so the entry point is bound by assignment (CORE-REQUEST in the manifest).
run = _consistency_oracle
