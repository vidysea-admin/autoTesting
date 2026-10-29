"""crawl-guidance G3, cycle 2 (checker B findings B1, B2): what a control's NAME may carry out.

`browser/enumerate.js` names an input by its `value` and a select by its option text, so a
prefilled email, password or select option reaches `ElementRef.name`. The payload must not send
that. These run the REAL `enumerate.js` in Chromium (skipped when no browser binary exists) and
read the prompt a fake model received.
"""

from __future__ import annotations

from pathlib import Path

from crawl_guidance_support import FakeProvider, guide, make_rt, reverse, screen

from autotester.browser.observe import enumerate_elements
from autotester.schema.screen_graph import ElementRef
from autotester.stages import explore_guidance_payload as payload

VALUES = ["jane.doe@example.org", "Hunter2-prefill", "Atlantis-Secret", "Narnia-Secret",
          "OnlyOptionText-Secret", "typed-search-term", "no-label-value", "draft-body-secret",
          "editable-secret", "hidden-csrf-token-77"]
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
                  "Send form", "Reports"):
        assert label in names, (label, names)
    assert {"<field:select>", "<field:text>", "<field:textarea>", "<field:div>",
            "<field:hidden>"} <= set(names)


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
