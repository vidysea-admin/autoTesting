"""AT-780 / RC12: PII-shaped step values never reach the judge prompt (recording mock)."""

from __future__ import annotations

import pytest
from reconcile_fakes import dumped, judge_mock, judge_prompts, node, screen, step, video

from autotester.schema.flowspec import Flow
from autotester.stages.ingest import flow_id
from autotester.stages.reconcile import reconcile


def _prompt(target: str, value: str | None, *, narration: str | None = None,
            signals: tuple[str, ...] = ("Invoice table",)) -> str:
    s = step(1, "scr_1", value=value, narration=narration).model_copy(update={"target": target})
    f = Flow(id=flow_id("Fill", "src_a"), name="Fill", entry_screen="scr_1", exit_screen="scr_1",
             steps=[s])
    spec = video("src_a", [screen("scr_1", "Billing ledger", "/app", signals)], [f])
    provider = judge_mock()
    reconcile([spec], [node("/app", "Team chat", [("button", "Send message")])], provider)
    prompts = judge_prompts(provider)
    assert len(prompts) == 1
    return prompts[0]


@pytest.mark.parametrize("raw", ["jane.doe@example.com", "+91 98765 43210", "9876543210",
                                 "+44 20 7946 0958", "+1 (415) 555-2671"])
def test_pii_values_are_masked_in_the_exact_prompt(raw: str) -> None:
    prompt = _prompt("Contact box", raw)
    assert raw not in prompt and ("<email>" in prompt or "<phone>" in prompt)


@pytest.mark.parametrize("label", ["First name textbox", "Student name", "Parent", "Guardian"])
def test_name_field_value_is_masked(label: str) -> None:
    prompt = _prompt(label, "Rahul Sharma")
    assert "Rahul" not in prompt and "Sharma" not in prompt and "<name>" in prompt


def test_pii_in_narration_and_cues_is_masked_too() -> None:
    prompt = _prompt("Contact box", None, narration="mail a.b@x.org or 9876543210",
                     signals=("hello a.b@x.org",))
    assert "a.b@x.org" not in prompt and "9876543210" not in prompt


@pytest.mark.parametrize(("target", "value"), [
    ("Search box", "scholarships in Canada"), ("Year box", "2024"), ("Count box", "10"),
    ("Course name box", "Data Science"), ("Student ID box", "S1234")])
def test_non_pii_values_survive_in_the_prompt(target: str, value: str) -> None:
    prompt = _prompt(target, value)
    assert value in prompt and "<name>" not in prompt
    assert "<email>" not in prompt and "<phone>" not in prompt


def test_masking_is_deterministic_rc11() -> None:
    def run() -> bytes:
        s = step(1, "scr_1", value="jane@example.com").model_copy(update={"target": "Email"})
        f = Flow(id=flow_id("Fill", "src_a"), name="Fill", entry_screen="scr_1",
                 exit_screen="scr_1", steps=[s])
        spec = video("src_a", [screen("scr_1", "Billing ledger", "/app", ("Invoice table",))], [f])
        return dumped(*reconcile([spec], [node("/app", "Team chat", [("button", "Send")])],
                                 judge_mock()))
    assert run() == run()


# ---- AT-780 hardening (cycle 0) -----------------------------------------------------------

def _prompt_with_candidate(title: str, route: str, controls: list[tuple[str, str]]) -> str:
    s = step(1, "scr_1", value="x").model_copy(update={"target": "Search box"})
    f = Flow(id=flow_id("Fill", "src_a"), name="Fill", entry_screen="scr_1", exit_screen="scr_1",
             steps=[s])
    spec = video("src_a", [screen("scr_1", "Billing ledger", "/app", ("Invoice table",))], [f])
    provider = judge_mock()
    reconcile([spec], [node(route, title, controls)], provider)
    prompts = judge_prompts(provider)
    assert len(prompts) == 1
    return prompts[0]


def test_pii_in_the_candidate_title_route_and_controls_is_masked() -> None:
    prompt = _prompt_with_candidate(
        "Inbox of jane.doe@example.com", "/app?e=jane.doe@example.com&p=9876543210",
        [("button", "Call 98765 43210"), ("link", "Mail jane+x@example.com")])
    for leak in ("jane.doe", "jane+x", "9876543210", "98765 43210"):
        assert leak not in prompt
    assert '"title": "Inbox of <email>"' in prompt  # title verbatim; route is normalised


@pytest.mark.parametrize("raw", ["josé@exämple.com", "jane+promo@example.com", "0141-2345678",
                                 "011 2345 6789", "98765.43210", "9876 543 210", "(98765) 43210",
                                 "98765 43210"])
def test_hardened_pii_shapes_never_reach_the_prompt(raw: str) -> None:
    prompt = _prompt("Contact box", raw, narration=f"said {raw}", signals=(f"cue {raw}",))
    assert raw not in prompt and "jane+" not in prompt and "josé" not in prompt
    assert "<email>" in prompt or "<phone>" in prompt


def test_nested_strings_in_every_part_of_the_prompt_are_masked() -> None:
    prompt = _prompt("Contact box", None, narration="x@y.com",
                     signals=("a", "9876543210", "b@c.io"))
    assert "x@y.com" not in prompt and "9876543210" not in prompt and "b@c.io" not in prompt


@pytest.mark.parametrize("label", [
    "\u0928\u093e\u092e", "\u092a\u093f\u0924\u093e \u0915\u093e \u0928\u093e\u092e",
    "fname", "lname", "first_name", "Dad", "Mother", "Father", "guardian"])
def test_hardened_name_labels_are_masked_in_the_prompt(label: str) -> None:
    prompt = _prompt(label, "Rahul Sharma")
    assert "Rahul" not in prompt and "Sharma" not in prompt and "<name>" in prompt


@pytest.mark.parametrize("label", ["Bank name", "Business name", "Plan name", "Course name",
                                   "University name", "Student country", "Student course"])
def test_non_person_labels_keep_their_value_in_the_prompt(label: str) -> None:
    prompt = _prompt(label, "Data Science")
    assert "Data Science" in prompt and "<name>" not in prompt
