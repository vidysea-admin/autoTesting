"""AT-650: the X10-b typing gate must see an input's real `type`, not guess from its name.

`browser/enumerate.js` mapped every text-like `<input>` to role "textbox" and dropped
the `type` it had just computed, so `typing_target_allowed` could only test a
"password"/"passwd" substring. A real `<input type="password">` called `#pin` was typed
into. Contract: qa/contracts/explore.md X10-b condition 4 (D-029, non-destructive).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotester.browser.observe import enumerate_elements
from autotester.schema.screen_graph import ElementRef
from autotester.stages.explore_safety import typing_target_allowed


@pytest.mark.parametrize(("name", "selector", "input_type"), [
    ("PIN", "#pin", "password"),
    ("Passcode", "#otp", "password"),
    ("Avatar", "#avatar", "file"),
    ("Display name", "#displayname", "PASSWORD"),
])
def test_a_password_or_file_input_is_refused_even_when_its_name_looks_harmless(
        name: str, selector: str, input_type: str) -> None:
    el = ElementRef(role="textbox", name=name, selector=selector, type=input_type)
    assert not typing_target_allowed(el)


def test_an_ordinary_text_input_and_a_legacy_element_without_type_stay_typeable() -> None:
    assert typing_target_allowed(ElementRef(role="textbox", name="PIN", selector="#pin",
                                            type="text"))
    assert typing_target_allowed(ElementRef(role="textbox", name="PIN", selector="#pin"))


def test_the_name_heuristic_still_widens_the_refusal_for_a_stored_graph_without_type() -> None:
    assert not typing_target_allowed(ElementRef(role="textbox", name="New password",
                                                selector="#np"))


def test_a_stored_element_without_type_still_loads_and_unknown_keys_are_still_refused() -> None:
    legacy = {"role": "textbox", "name": "Q", "selector": "#q", "tag": "input"}
    assert ElementRef.model_validate(legacy).type == ""
    with pytest.raises(ValidationError):
        ElementRef.model_validate({**legacy, "bogus": 1})


def test_enumerate_reports_the_real_type_of_a_password_input_named_pin(page_factory) -> None:
    page, _visit = page_factory
    page.set_content(
        '<input id="pin" type="password" aria-label="PIN">'
        '<input id="avatar" type="file" aria-label="Avatar">'
        '<input id="plain" aria-label="Plain">'
        '<input id="up" type="PassWord" aria-label="Upper">'
        '<button id="go">Go</button>')
    by_name = {el.name: el for el in enumerate_elements(page)}
    pin, avatar, plain, upper = (by_name[n] for n in ("PIN", "Avatar", "Plain", "Upper"))
    assert (pin.type, avatar.type, plain.type, upper.type) == (
        "password", "file", "text", "password")
    assert not typing_target_allowed(pin)
    assert not typing_target_allowed(avatar)
    assert not typing_target_allowed(upper)
    assert typing_target_allowed(plain)
