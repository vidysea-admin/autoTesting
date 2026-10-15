"""Text teaching uses guarded Provider.act and validates locator provenance."""

import pytest

from autotester.core.redact import Redactor
from autotester.providers.base import Provider
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.schema.teaching import TeachingUnit, TextObservation
from autotester.stages.teach_text import InvalidTextTeaching, teach_text


class TextTeacherFake(Provider):
    """Capture the real stage boundary without invoking a vendor."""

    def __init__(self, response):
        super().__init__()
        self.response = response
        self.prompts = []

    def available(self):
        return True

    def act(self, prompt, schema=None, **kwargs):
        self.prompts.append(prompt)
        assert schema is TextObservation
        assert kwargs["prompt_file"] == "teach_text_v1.md"
        return self.response


def text_reading_fixture():
    return {
        "screens": [{"name": "Home", "locator": "page 2"}],
        "flows": [{"name": "Save", "entry_screen": "Home", "steps": [
            {"order": 1, "action": "click", "target": "Save", "screen": "Home",
             "locator": "page 2", "expected": {"visible_text": ["Saved"]}}]}],
    }


def _teach(provider, **kwargs):
    return teach_text(Source(project="demo", kind=SourceKind.DOC, text="Click Save"),
                      "demo", provider, units=[TeachingUnit(locator="page 2", text="Click Save")],
                      redactor=Redactor({}), **kwargs)


def test_text_proposal_retains_locator_expectation_and_stays_unreconciled():
    provider = TextTeacherFake(text_reading_fixture())
    spec = _teach(provider)
    step = spec.flows[0].steps[0]
    assert step.source_ref.locator == "page 2"
    assert step.source_ref.source_id == spec.source_ids[0]
    assert step.source_ref.t_start is None and step.source_ref.t_end is None
    assert step.expected.visible_text == ["Saved"]
    assert spec.flows[0].kind is None and spec.review.status.value == "draft"
    assert spec.fingerprint == _teach(provider).fingerprint


@pytest.mark.parametrize("change", ["locator", "screen", "orders", "duplicates"])
def test_invalid_model_references_are_refused(change):
    response = text_reading_fixture()
    step = response["flows"][0]["steps"][0]
    if change == "locator":
        step["locator"] = "invented section"
    elif change == "screen":
        step["screen"] = "Unknown"
    elif change == "orders":
        response["flows"][0]["steps"].append(dict(step))
    else:
        response["screens"].append(dict(response["screens"][0]))
    with pytest.raises(InvalidTextTeaching):
        _teach(TextTeacherFake(response))


@pytest.mark.parametrize("side", ["input", "output" ])
def test_input_and_model_output_secrets_and_pii_are_scrubbed(side):
    response = text_reading_fixture()
    response["flows"][0]["steps"][0]["value"] = (
        "sensitive-fixture student@example.com" if side == "output" else "Save")
    provider = TextTeacherFake(response)
    spec = teach_text(Source(project="demo", kind=SourceKind.TEXT, text="unused"), "demo",
                      provider, units=[TeachingUnit(locator="page 2", text=(
                          "sensitive-fixture student@example.com" if side == "input" else "Save"))],
                      redactor=Redactor({"PASSWORD": "sensitive-fixture"}))
    assert "sensitive-fixture" not in provider.prompts[0]
    assert "sensitive-fixture" not in spec.model_dump_json()
    assert "student@example.com" not in spec.model_dump_json()


@pytest.mark.parametrize("invalid", ["empty", "duplicate", "project", "video"])
def test_invalid_input_never_calls_provider(invalid):
    provider = TextTeacherFake(text_reading_fixture())
    source = Source(project="other" if invalid == "project" else "demo",
                    kind=SourceKind.VIDEO if invalid == "video" else SourceKind.TEXT)
    units = [TeachingUnit(locator="page 2", text="Click Save")]
    units = [] if invalid == "empty" else units * (2 if invalid == "duplicate" else 1)
    with pytest.raises(InvalidTextTeaching):
        teach_text(source, "demo", provider, units=units, redactor=Redactor({}))
    assert not provider.prompts

