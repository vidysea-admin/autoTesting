"""T-220 (multi-role-platform.md MP33): a StateProbe is closed, value-free and self-consistent.

A probe that names no reader role, a counter without a delta, a status without an ExpectedState,
a mailbox channel, an id-bearing reader URL or personal-shaped text fails here, not in a run.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotester.schema.flowspec import ExpectedState
from autotester.schema.multi_role_enums import AssertChannel
from autotester.schema.role_step import RoleStep
from autotester.schema.state_probe import ReaderKind, StateProbe


def _probe(**over: object) -> StateProbe:
    fields: dict[str, object] = {
        "id": "inbox-count", "platform_id": "parent", "kind": ReaderKind.COUNTER,
        "reader_channel": AssertChannel.UI, "reader_target": "#unread", "reader_url": "/inbox",
        "action": RoleStep(id="send", role_id="teacher", action="click #send"),
        "reader_role_ids": ["teacher", "parent"], "expected_delta": 1}
    return StateProbe(**{**fields, **over})


def test_round_trip() -> None:
    probe = _probe()
    assert StateProbe.model_validate_json(probe.model_dump_json()) == probe


def test_a_status_probe_reuses_flowspec_expected_state() -> None:
    probe = _probe(kind=ReaderKind.STATUS, expected_delta=None,
                   expected_state=ExpectedState(visible_text=["Published"]))
    assert probe.expected_state is not None
    assert probe.expected_state.visible_text == ["Published"]


@pytest.mark.parametrize("over", [
    {"reader_role_ids": []},
    {"reader_role_ids": ["parent", "parent"]},
    {"reader_role_ids": ["Not A Role"]},
    {"expected_delta": None},
    {"expected_delta": 0},
    {"expected_state": ExpectedState(visible_text=["x"])},
    {"kind": ReaderKind.STATUS, "expected_delta": None},
    {"kind": ReaderKind.STATUS, "expected_delta": None, "expected_state": ExpectedState()},
    {"kind": ReaderKind.STATUS, "expected_delta": 1,
     "expected_state": ExpectedState(visible_text=["x"])},
    {"reader_channel": AssertChannel.MAILBOX},
    {"reader_url": "/inbox/12345"},
    {"reader_url": "/inbox?u=bob"},
    {"reader_target": "mail to bob@example.org"},
    {"id": "Bad Id"},
    {"platform_id": "Bad Platform"},
    {"extra": 1},
])
def test_invalid_probes_are_refused(over: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _probe(**over)


def test_a_placeholder_url_is_allowed() -> None:
    assert _probe(reader_url="/inbox/{id}").reader_url == "/inbox/{id}"
