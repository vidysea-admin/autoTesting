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
