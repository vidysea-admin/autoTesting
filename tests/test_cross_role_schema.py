"""T-211 (multi-role-platform.md MP13, MPI1): the cross-role shapes are closed and value-free.

Steps and assertions are the shapes the runner reads; a free-text field that looks like personal
data, an unknown field, a dangling role or step reference, or a non-positive window fails here,
not later in a run.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.cross_role_scenario import CrossRoleScenario
from autotester.schema.multi_role_enums import AssertChannel, Expectation
from autotester.schema.role_step import RoleStep


def _assertion(**over: object) -> CrossRoleAssertion:
    fields: dict[str, object] = {
        "id": "a1", "observer_role_id": "parent", "channel": AssertChannel.UI,
        "expectation": Expectation.PRESENT, "target": "#grades .row", "within_s": 5}
    return CrossRoleAssertion(**{**fields, **over})


def _scenario(**over: object) -> CrossRoleScenario:
    fields: dict[str, object] = {
        "id": "s1", "title": "t", "roles": ["teacher", "parent"],
        "steps": [RoleStep(id="act", role_id="teacher", action="click #publish")],
        "assertions": [_assertion()]}
    return CrossRoleScenario(**{**fields, **over})


def test_round_trip_and_default_poll_interval() -> None:
    scenario = _scenario()
    assert CrossRoleScenario.model_validate_json(scenario.model_dump_json()) == scenario
    assert scenario.assertions[0].poll_interval_s == 0.5


@pytest.mark.parametrize("channel", ["ui", "mailbox", "api"])
def test_channel_is_the_closed_set(channel: str) -> None:
    assert _assertion(channel=channel).channel is AssertChannel(channel)


@pytest.mark.parametrize("bad", [
    {"channel": "sms"}, {"expectation": "maybe"}, {"within_s": 0}, {"within_s": -1},
    {"within_s": 3601}, {"poll_interval_s": 0}, {"poll_interval_s": 61}, {"target": ""},
    {"target": "mail to jane.doe@example.com"}, {"observer_role_id": "Has Space"},
    {"surprise": 1}])
def test_assertion_rejects_bad_fields(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _assertion(**bad)


@pytest.mark.parametrize("action", ["", "dance #x", "click", "fill #p call +1 415 555 0100",
                                    "goto https://x.test/a?e=jane@x.test"])
def test_step_action_uses_the_repro_vocabulary_and_holds_no_personal_text(action: str) -> None:
    with pytest.raises(ValidationError):
        RoleStep(id="s", role_id="teacher", action=action)


def test_step_rejects_unknown_fields_and_bad_ids() -> None:
    with pytest.raises(ValidationError):
        RoleStep(id="s", role_id="teacher", action="click #x", extra_field=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        RoleStep(id="S 1", role_id="teacher", action="click #x")


def test_observation_is_closed() -> None:
    assert Observation(matched=True).detail == ""
    with pytest.raises(ValidationError):
        Observation(matched=True, extra=1)  # type: ignore[call-arg]


@pytest.mark.parametrize("over", [
    {"steps": [RoleStep(id="act", role_id="ghost", action="click #publish")]},
    {"assertions": [_assertion(observer_role_id="ghost")]},
    {"assertions": [_assertion(after_step="nope")]},
    {"steps": [RoleStep(id="act", role_id="teacher", action="click #a"),
               RoleStep(id="act", role_id="teacher", action="click #b")]},
    {"assertions": [_assertion(), _assertion()]},
    {"roles": ["teacher", "teacher", "parent"]},
    {"steps": []}, {"assertions": []}])
def test_scenario_rejects_dangling_references_duplicates_and_empties(
        over: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _scenario(**over)

