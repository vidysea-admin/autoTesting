"""E2.4 (AT-1414): the judge schema REQUIRES a non-null `defect_observed`.

The schema embedded for json-mode/Ollama and sent to schema/tool strategies marks the field
required and boolean-only; a model-chain reply that omits it or sends null takes the one repair
retry and then a `ProviderError` that grades INCONCLUSIVE; `Judgment` itself stays tolerant to
construct and `_defect_decision` keeps its None fallback. Fake `litellm`, no network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from test_run_case_pipeline import _case, _project, _session

from autotester.providers.base import ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.litellm_schema import json_mode_instruction, request_options
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Judgment, Rubric
from autotester.stages.grade import grade
from autotester.stages.run_case_pipeline import run_and_grade_case_resilient
from autotester.store.project_store import ProjectStore

pytestmark = pytest.mark.usefixtures("no_network")

MODEL = "ollama_chat/glm-5.3-flash"
BASE = {"result": "PASS", "scoreboard": "1/1", "criteria_met": 1, "criteria_total": 1,
        "failures": [], "note": "The dashboard heading was visible.", "defect_summary": None}


@pytest.fixture(autouse=True)
def _env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-key")


def _rubric() -> Rubric:
    return Rubric(id="rub_t", criteria=[Criterion(id="c1", text="x")])


def _raw() -> RawResult:
    return RawResult(case_id="case_t", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.DOM, path="url http://127.0.0.1/x.html", step_order=1)])


def _sent_schema(fake: Any) -> dict[str, Any]:
    text = fake.calls[0]["messages"][0]["content"]
    text = text if isinstance(text, str) else text[0]["text"]
    return json.loads(text[text.index("JSON Schema:\n") + len("JSON Schema:\n"):])


def _assert_required_boolean(schema: dict[str, Any]) -> None:
    assert "defect_observed" in schema["required"]
    prop = schema["properties"]["defect_observed"]
    assert prop["type"] == "boolean" and "anyOf" not in prop and "default" not in prop
    assert prop["type"] != "null"


def test_a_the_json_mode_schema_requires_a_non_null_boolean() -> None:
    _assert_required_boolean(json.loads(json_mode_instruction(Judgment).split("Schema:\n")[1]))


def test_a_the_schema_and_tool_strategies_send_the_same_tightened_schema() -> None:
    schema_opts = request_options("schema", "openai/gpt-4o", Judgment)
    _assert_required_boolean(schema_opts["response_format"]["json_schema"]["schema"])
    tool_opts = request_options("tool", "openai/gpt-4o", Judgment)
    _assert_required_boolean(tool_opts["tools"][0]["function"]["parameters"])


def test_a_the_ollama_judge_call_carries_the_required_schema(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps({**BASE, "defect_observed": False}))])
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-key")
    LiteLLMProvider(model=MODEL).judge("grade", Judgment)
    _assert_required_boolean(_sent_schema(fake))


@pytest.mark.parametrize("missing", ["omitted", "null"])
def test_b_a_missing_or_null_answer_gets_one_repair_prompt_then_provider_error(
        monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    body = dict(BASE) if missing == "omitted" else {**BASE, "defect_observed": None}
    fake = install(monkeypatch, [reply(json.dumps(body)), reply(json.dumps(body))])
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-key")
    with pytest.raises(ProviderError, match="defect_observed"):
        LiteLLMProvider(model=MODEL).judge("grade", Judgment)
    assert len(fake.calls) == 2  # the first answer plus exactly one repair
    repair = fake.calls[1]["messages"][-1]["content"]
    assert "not valid" in repair and "defect_observed" in repair


def test_b_a_repair_that_supplies_the_field_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(BASE)),
                                 reply(json.dumps({**BASE, "defect_observed": False}))])
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-key")
    judged = LiteLLMProvider(model=MODEL).judge("grade", Judgment)
    assert judged.defect_observed is False and len(fake.calls) == 2


def test_b_the_unanswered_field_grades_inconclusive_with_the_reason_in_the_note(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [reply(json.dumps(BASE)), reply(json.dumps(BASE))])
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-key")
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project())
    _, verdict = run_and_grade_case_resilient(
        _case(), _session(tmp_path), LiteLLMProvider(model=MODEL), "run_1", store)
    assert verdict.result is Result.INCONCLUSIVE
    assert "ProviderError" in (verdict.note or "") and "defect_observed" in (verdict.note or "")


def test_c_defect_observed_false_parses_and_grades_as_before(
        monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [reply(json.dumps({**BASE, "defect_observed": False}))])
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-key")
    verdict = grade(_rubric(), _raw(), "run_1", LiteLLMProvider(model=MODEL))
    assert verdict.result is Result.PASS


def test_c_defect_observed_true_still_downgrades_a_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [reply(json.dumps(
        {**BASE, "defect_observed": True, "defect_summary": "heading missing"}))])
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-key")
    verdict = grade(_rubric(), _raw(), "run_1", LiteLLMProvider(model=MODEL))
    assert verdict.result is Result.INCONCLUSIVE


def test_d_judgment_without_the_field_still_constructs_and_keeps_the_none_fallback() -> None:
    judged = Judgment(result=Result.PASS, scoreboard="1/1", criteria_met=1, criteria_total=1)
    assert judged.defect_observed is None
    assert Judgment.model_validate({"result": "PASS"}).defect_observed is None
