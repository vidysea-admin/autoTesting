"""The state-after oracle: did an action leave the promised change, and did it persist? (MP33)

One job: for each `StateProbe` in `<run_dir>/state_probes.json`, read the counter, list or status
as every reader role before the action, after it, and after reloading the page; a change that is
missing, the wrong size or gone after the reload is one `MultiRoleFinding` per reader role, citing
all three readings (`schema/oracle_context.py` "HOW TO WRITE AN ORACLE": `run(context)`).

What a reading is: a counter/list reader's observation detail is parsed to one integer; a status
reader is reduced to the declared `visible_text` tokens it shows (or `none`). The page text itself
is never copied (MPI1). The actor's own in-place "after" reading must show the change. A non-actor
reader's page may legitimately be stale until it reloads, so for that role the reload reading
decides and a late-but-correct page is clean (live-update latency is the cross-role runner's
timed assertion, not this oracle's). A reader that cannot be read is a finding, never a pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter

from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_enums import Expectation, FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext, RoleSessionPort
from autotester.schema.role_step import RoleStep
from autotester.schema.state_probe import ReaderKind, StateFault, StateProbe

PROBES_FILE = "state_probes.json"
_NUMBER = re.compile(r"-?\d[\d,]*")
_MAX_DIGITS = 9
_SHOW_MAX = 999_999
_PROBES = TypeAdapter(list[StateProbe])


@dataclass(frozen=True)
class Reading:
    """One look at a reader: `value` is an int (counter/list), a bool (status ok) or None."""

    value: int | bool | None
    label: str


def load_probes(run_dir: str) -> list[StateProbe]:
    """The probes declared for this run; no file means nothing to check."""
    path = Path(run_dir) / PROBES_FILE
    if not path.is_file():
        return []
    return _PROBES.validate_json(path.read_text(encoding="utf-8"))


def _parse_number(detail: str) -> int | None:
    match = _NUMBER.search(detail)
    digits = match.group().replace(",", "") if match else ""
    if not digits or len(digits.lstrip("-")) > _MAX_DIGITS:
        return None
    return int(digits)


def _reduce(probe: StateProbe, detail: str) -> Reading:
    if probe.kind is not ReaderKind.STATUS:
        number = _parse_number(detail)
        return Reading(number, "unreadable" if number is None else _show(number))
    state = probe.expected_state
    assert state is not None  # the schema guarantees it for a status probe
    shown = [t for t in state.visible_text if t in detail and not contains_personal_shape(t)]
    clean = all(t in detail for t in state.visible_text) and not any(
        t in detail for t in state.absent_text)
    return Reading(clean, "+".join(shown) or "none")


def _show(number: int) -> str:
    return str(number) if abs(number) <= _SHOW_MAX else f">{_SHOW_MAX}"


def _read(port: RoleSessionPort, probe: StateProbe, role: str, stage: str) -> Reading:
    assertion = CrossRoleAssertion(
        id=f"read-{stage}", observer_role_id=role, channel=probe.reader_channel,
        expectation=Expectation.PRESENT, target=probe.reader_target, within_s=1.0)
    try:
        seen = port.observe(assertion)
    except Exception:
        return Reading(None, "unreadable")
    return _reduce(probe, seen.detail) if seen.matched else Reading(None, "unreadable")


def _goto(port: RoleSessionPort, probe: StateProbe, role: str, stage: str) -> None:
    port.perform(RoleStep(id=f"{stage}-{probe.id}"[:64], role_id=role,
                          action=f"goto {probe.reader_url}"))


def _changed(probe: StateProbe, before: Reading, now: Reading) -> bool:
    """Did the reader show the promised change relative to `before`?"""
    if probe.kind is ReaderKind.STATUS:
        return now.value is True
    assert isinstance(before.value, int) and isinstance(now.value, int)
    return now.value - before.value == probe.expected_delta


def _fault(probe: StateProbe, is_actor: bool, b: Reading, a: Reading,
           r: Reading) -> tuple[StateFault, int] | None:
    """The first failing check for one reader role, with how far off the number was."""
    needed = (b, a, r) if is_actor else (b, r)
    if any(x.value is None for x in needed):
        return StateFault.UNREADABLE, 1
    if is_actor and not _changed(probe, b, a):
        return _wrong(probe, b, a)
    if not _changed(probe, b, r):
        if is_actor or _changed(probe, b, a):
            return StateFault.NOT_PERSISTED, _gap(probe, b, r)
        return _wrong(probe, b, r)
    return None


def _gap(probe: StateProbe, before: Reading, now: Reading) -> int:
    if probe.kind is ReaderKind.STATUS:
        return 1
    return max(1, abs(int(now.value) - int(before.value) - int(probe.expected_delta or 0)))


def _wrong(probe: StateProbe, before: Reading, now: Reading) -> tuple[StateFault, int]:
    if probe.kind is not ReaderKind.STATUS and now.value != before.value:
        return StateFault.WRONG_SIZE, _gap(probe, before, now)
    return StateFault.MISSING, _gap(probe, before, now)


def _finding(probe: StateProbe, role: str, fault: StateFault, count: int,
             readings: tuple[Reading, Reading, Reading]) -> MultiRoleFinding:
    b, a, r = readings
    want = (f"delta {probe.expected_delta:+d}" if probe.kind is not ReaderKind.STATUS
            else "expected status")
    title = (f"{fault.value}: {probe.kind.value} reader {probe.id} ({want}) "
             f"before={b.label} after={a.label} reload={r.label}")[:200]
    actor = probe.action.role_id
    steps = [f"login {actor}"] + ([f"login {role}"] if role != actor else [])
    steps += [f"goto {probe.reader_url}", probe.action.action, f"goto {probe.reader_url}"]
    return MultiRoleFinding(
        finding_id=f"state-{probe.id[:28]}-{role[:28]}",
        finding_class=FindingClass.STATE_NOT_PERSISTED,
        title=title, role=role, platform_id=probe.platform_id, url_template=probe.reader_url,
        steps=steps, count=count, oracle=OracleName.STATE_AFTER)


def _probe_findings(port: RoleSessionPort, probe: StateProbe) -> list[MultiRoleFinding]:
    roles = probe.reader_role_ids
    for role in roles:
        _goto(port, probe, role, "load")
    before = {role: _read(port, probe, role, "before") for role in roles}
    port.perform(probe.action)
    after = {role: _read(port, probe, role, "after") for role in roles}
    for role in roles:
        _goto(port, probe, role, "reload")
    found: list[MultiRoleFinding] = []
    for role in roles:
        reloaded = _read(port, probe, role, "reload")
        verdict = _fault(probe, role == probe.action.role_id, before[role], after[role], reloaded)
        if verdict is not None:
            found.append(_finding(probe, role, *verdict,
                                  (before[role], after[role], reloaded)))
    return found


def check_state_after(context: OracleContext) -> list[MultiRoleFinding]:
    """Check every declared probe; the port is required because the oracle drives the action."""
    if context.port is None:
        raise RuntimeError("the state-after oracle needs a role session port")
    probes = load_probes(context.run_dir)
    return [f for probe in probes for f in _probe_findings(context.port, probe)]


# The registry's contract is a module-level `run`. It is an alias, not a second `def run`, because
# `autotester doctor` rejects a function name defined in two modules and every G11 oracle (and
# `doctor.py`) would otherwise define one.
run = check_state_after
