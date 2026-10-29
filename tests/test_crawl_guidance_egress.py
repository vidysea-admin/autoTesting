"""crawl-guidance G3, cycle 2 (checker B findings B1, B2): what a control's NAME may carry out.

`browser/enumerate.js` names an input by its `value` and a select by its option text, so a
prefilled email, password or select option reaches `ElementRef.name`. The payload must not send
that. These run the REAL `enumerate.js` in Chromium (skipped when no browser binary exists) and
read the prompt a fake model received.
"""

from __future__ import annotations

import random
from pathlib import Path

from crawl_guidance_support import FakeProvider, guide, make_rt, reverse, screen

from autotester.browser.observe import enumerate_elements
from autotester.schema.screen_graph import ElementRef
from autotester.stages import explore_guidance_payload as payload

VALUES = ["jane.doe@example.org", "Hunter2-prefill", "Atlantis-Secret", "Narnia-Secret",
          "OnlyOptionText-Secret", "typed-search-term", "no-label-value", "draft-body-secret",
          "editable-secret", "hidden-csrf-token-77", "Class10A-Secret", "nick-Secret",
          "query-Secret", "spin-Secret", "Autumn-Secret", "slider-Secret", "CBSE-Secret",
          "Menu-Secret"]
PAGE = """
<label for="em">Work email</label><input id="em" type="email" value="jane.doe@example.org">
<label>Password <input type="password" value="Hunter2-prefill"></label>
<select aria-label="Country"><option>Atlantis-Secret</option>
  <option selected>Narnia-Secret</option></select>
<select id="s2"><option>OnlyOptionText-Secret</option></select>
<input type="text" placeholder="Search students" value="typed-search-term">
<input type="text" value="no-label-value">
<textarea>draft-body-secret</textarea>
<div contenteditable="true" tabindex="0">editable-secret</div>
<input type="hidden" value="hidden-csrf-token-77">
<div role="combobox" tabindex="0">Class10A-Secret</div>
<div role="textbox" tabindex="0" aria-label="Nickname">nick-Secret</div>
<span id="lq">Find student</span>
<div role="searchbox" tabindex="0" aria-labelledby="lq">query-Secret</div>
<div role="spinbutton" tabindex="0">spin-Secret</div>
<div role="listbox" tabindex="0" aria-label="Term">
  <div role="option" tabindex="0">Autumn-Secret</div></div>
<div role="slider" tabindex="0">slider-Secret</div>
<span id="lb">Board</span>
<div id="cb" role="button" aria-haspopup="listbox" aria-labelledby="lb cb"
  tabindex="0">CBSE-Secret</div>
<div role="button" aria-haspopup="true" tabindex="0">Menu-Secret</div>
<button>Save changes</button><input type="submit" value="Send form"><a href="/reports">Reports</a>
"""


def _names(prompt: str) -> list[str]:
    import crawl_guidance_support as support
    return [c["name"] for c in support.payload_of(prompt)["controls"]]


def test_prefilled_values_and_option_text_never_leave_the_machine(
        page_factory: tuple, tmp_path: Path) -> None:
    page, _visit = page_factory
    page.set_content(PAGE)
    cands = enumerate_elements(page)
    assert any(v in c.name for c in cands for v in VALUES), "fixture really leaks via the name"
    model = FakeProvider(reverse)
    guide(model).order(make_rt(tmp_path), screen(), cands)
    assert model.calls == 1
    for value in VALUES:
        assert value not in model.prompts[0], value
    names = _names(model.prompts[0])
    for label in ("Work email", "Password", "Country", "Search students", "Save changes",
                  "Send form", "Reports", "Nickname", "Find student", "Term", "Board"):
        assert label in names, (label, names)
    assert {"<field:select>", "<field:text>", "<field:textarea>", "<field:div>",
            "<field:hidden>", "<field:combobox>", "<field:spinbutton>", "<field:slider>",
            "<field:option>"} <= set(names)


def test_a_field_without_a_label_source_is_neutral_even_for_an_old_stored_graph() -> None:
    """An ElementRef stored before the label field existed has `field_label` None: a form tag
    still never sends its name."""
    old = ElementRef(role="textbox", name="jane@example.org", selector="#e", tag="input",
                     type="email")
    sel = ElementRef(role="combobox", name="Option A Option B", selector="#s", tag="select")
    body = payload.build_payload(screen(), [old, sel], [], lambda t: t)
    assert [c["name"] for c in body["controls"]] == ["<field:email>", "<field:select>"]


def test_a_caption_button_input_keeps_its_name() -> None:
    sub = ElementRef(role="button", name="Send form", selector="#b", tag="input", type="submit")
    body = payload.build_payload(screen(), [sub], [], lambda t: t)
    assert body["controls"][0]["name"] == "Send form"


def test_a_field_label_is_scrubbed_and_capped() -> None:
    el = ElementRef(role="textbox", name="x", selector="#e", tag="input", type="text",
                    field_label="L" * 54 + "S3cretPlant-91xyz")
    scrub = lambda text: (text or "").replace("S3cretPlant-91xyz", "[REDACTED]")  # noqa: E731
    name = payload.build_payload(screen(), [el], [], scrub)["controls"][0]["name"]
    assert "S3cret" not in name and len(name) <= payload.NAME_CHARS


def test_the_label_field_is_not_persisted_so_crawl_artifacts_stay_byte_identical() -> None:
    el = ElementRef(role="textbox", name="x", selector="#e", tag="input", field_label="Email")
    assert "field_label" not in el.model_dump(exclude_none=True)
    assert ElementRef.model_validate(el.model_dump()).field_label is None


# ---- residuals: checker-B residuals N1, N2, N3, N5 (qa/manifests/crawl-guidance-residuals.md) ----
# Every planted value is a random non-word string, so no placeholder text can false-match; a leak
# is the whole value or any 5-character slice of it reaching the captured prompt.
_RNG = random.Random(20261029)
_ALPHA = "bcdfghjklmnpqrstvwxz0123456789"
SHAPES = {
    "n1-base-select-button": ('<select style="appearance:base-select"><button><selectedcontent>'
                              '</selectedcontent></button><option selected>{V}</option>'
                              '<option>other</option></select>'),
    "n1-select-button": ('<select><button>{V}</button><option>zz</option></select>'),
    "n1-select-option-onclick": ('<select><option onclick="1">{V}</option></select>'),
    "n1-select-option-tabindex": ('<select><option tabindex="0">{V}</option></select>'),
    "n1-datalist-option-tabindex": ('<datalist id="dl"><option tabindex="0">{V}</option>'
                                    '</datalist><input list="dl">'),
    "n2-label-combobox": ('<label>Field <div role="combobox">{V}</div><input id="i1"></label>'),
    "n2-label-contenteditable": ('<label>Field <span contenteditable="true">{V}</span>'
                                 '<input id="i1"></label>'),
    "n2-label-listbox": ('<label>Field <div role="listbox"><div role="option">{V}</div></div>'
                         '<input id="i1"></label>'),
    "n3-target-select": ('<span id="t">Name <select><option>{V}</option></select></span>'
                         '<input aria-labelledby="t">'),
    "n3-target-listbox": ('<div id="t">Name <div role="listbox"><div role="option">{V}</div></div>'
                          '</div><input aria-labelledby="t">'),
    "n3-target-editable": ('<div id="t">Name <div contenteditable="true">{V}</div></div>'
                           '<input aria-labelledby="t">'),
    "n3-target-is-listbox": ('<div id="t" role="listbox">{V}</div><input aria-labelledby="t">'),
    "n5-fallback-combobox": ('<div role="foo combobox" tabindex="0">{V}</div>'),
    "n5-fallback-textbox": ('<div role="presentation textbox" tabindex="0">{V}</div>'),
    "n5-fallback-padded-upper": ('<div role="  generic  LISTBOX " tabindex="0">{V}</div>'),
}


def _leaks(prompt: str, value: str) -> bool:
    return value in prompt or any(value[i:i + 5] in prompt for i in range(len(value) - 4))


def test_residual_shapes_never_send_a_planted_value(page_factory: tuple, tmp_path: Path) -> None:
    """N1 (inside select/datalist), N2 (label text), N3 (aria-labelledby target), N5 (role
    fallback list): the REAL enumerate.js -> ElementRef -> Guidance -> captured prompt."""
    page, _visit = page_factory
    failures = []
    for shape, markup in SHAPES.items():
        value = "Q" + "".join(_RNG.choice(_ALPHA) for _ in range(11))
        page.set_content(markup.replace("{V}", value) + '<a href="/reports">Reports</a>')
        cands = enumerate_elements(page)
        model = FakeProvider(reverse)
        guide(model).order(make_rt(tmp_path), screen(), cands)
        assert model.calls == 1, shape  # a shape that sends nothing proves nothing
        if _leaks(model.prompts[0], value):
            failures.append(shape)
    assert failures == []


def test_a_role_fallback_list_is_read_token_by_token_for_an_old_stored_graph() -> None:
    """N5, Python half: an ElementRef stored with no field_label still finds the field role."""
    refs = [ElementRef(role=role, name="Zq91xv-secret", selector="#e", tag="div")
            for role in ("foo combobox", "presentation  TEXTBOX", "generic listbox")]
    body = payload.build_payload(screen(), refs, [], lambda t: t)
    assert [c["name"] for c in body["controls"]] == [
        "<field:combobox>", "<field:textbox>", "<field:listbox>"]
