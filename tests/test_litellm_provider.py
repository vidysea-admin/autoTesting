"""T-202: the LiteLLM provider. Every test runs against an injected fake `litellm`
(`tests/litellm_fake.py`) -- no network, no paid call (D-070).

Criteria ids are the proposal's LP*; the checker's own contract supersedes them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from pydantic import BaseModel, ConfigDict

from autotester.providers.base import ProviderError, Unsupported
from autotester.providers.litellm_provider import LiteLLMProvider

pytestmark = pytest.mark.usefixtures("no_network")

GOOD = {"verdict": "pass", "score": 3, "inner": {"note": "ok"}}
SECRET = "hunter2-very-secret-value"


class Inner(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: str
    score: int
    inner: Inner


@pytest.fixture(autouse=True)
def _isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))  # no real .env in the guard


def _provider(model: str = "openai/gpt-4o", **options: Any) -> LiteLLMProvider:
    return LiteLLMProvider(model=model, **options)


def _with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_API_KEY", "k-for-test")


# -- LP3: the three structured-output strategies -----------------------------

def test_schema_strategy_sends_response_format_and_returns_the_typed_object(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    out = _provider().judge("grade this", Answer)
    assert out == Answer.model_validate(GOOD)
    kw = fake.calls[0]
    assert kw["response_format"]["type"] == "json_schema" and "tools" not in kw


def test_tool_strategy_forces_one_answer_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(tool_args=GOOD)], response_schema=False)
    _with_key(monkeypatch)
    out = _provider().act("decide", Answer)
    assert out == Answer.model_validate(GOOD)
    kw = fake.calls[0]
    assert kw["tools"][0]["function"]["name"] == "answer" and "response_format" not in kw
    assert kw["tool_choice"]["function"]["name"] == "answer"


def test_json_mode_repairs_once_and_counts_the_repair_as_a_physical_call(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fenced = "```json\n" + json.dumps(GOOD) + "\n```"
    fake = install(monkeypatch, [reply("not json at all"), reply(fenced)],
                   response_schema=False, function_calling=False)
    _with_key(monkeypatch)
    provider = _provider("ollama/llama3.2")
    assert provider.judge("grade", Answer) == Answer.model_validate(GOOD)
    assert len(fake.calls) == 2
    assert provider.usage[0].calls == 2  # LP5: the repair is a counted call


def test_unparsable_answer_raises_naming_model_and_role_never_a_partial_object(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply("{ nope")])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError, match=r"openai/gpt-4o.*judge|judge.*openai/gpt-4o"):
        _provider().judge("grade", Answer)
    assert len(fake.calls) == 1  # schema strategy: no silent retry


def test_schema_mismatch_is_an_error_not_a_coerced_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [reply(json.dumps({"verdict": "pass"}))])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError, match="judge"):
        _provider().judge("grade", Answer)


def test_json_mode_that_stays_broken_after_the_repair_raises(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply("x"), reply("y")], response_schema=False,
                   function_calling=False)
    _with_key(monkeypatch)
    with pytest.raises(ProviderError, match="agent"):
        _provider("ollama/llama3.2").act("p", Answer)
    assert len(fake.calls) == 2


# -- LP4 / LP5 / LP6 ---------------------------------------------------------

def test_see_video_is_unsupported() -> None:
    with pytest.raises(Unsupported):
        _provider().see_video(Path("x.mp4"), "p", Answer)


def test_one_physical_call_zero_retries_and_usage_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD), prompt_tokens=21, completion_tokens=5)])
    _with_key(monkeypatch)
    spans: list[dict[str, Any]] = []

    class _Trace:
        def record_llm(self, **kw: Any) -> None:
            spans.append(kw)

    provider = _provider()
    provider.trace = _Trace()  # type: ignore[assignment]
    provider.judge("grade", Answer, prompt_file="p.md", fed_id="c1")
    assert len(fake.calls) == 1 and fake.calls[0]["num_retries"] == 0
    row = provider.usage[0]
    assert (row.role, row.calls, row.input_tokens, row.output_tokens) == ("judge", 1, 21, 5)
    assert spans[0]["provider"] == provider.label == "litellm:openai/gpt-4o"
    assert spans[0]["input_tokens"] == 21 and spans[0]["fed_id"] == "c1"


def test_judge_is_deterministic_and_act_is_not_forced_cold(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD)), reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    _provider().judge("g", Answer)
    _provider().act("a", Answer)
    assert fake.calls[0]["temperature"] == 0 and "temperature" not in fake.calls[1]


# -- model routing -----------------------------------------------------------

def test_the_configured_model_string_is_what_litellm_receives(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    _provider("gemini/gemini-2.5-pro").judge("g", Answer)
    assert fake.calls[0]["model"] == "gemini/gemini-2.5-pro"


def test_model_falls_back_to_autotester_model_env_and_the_option_wins(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD)), reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    monkeypatch.setenv("AUTOTESTER_MODEL", "anthropic/claude-sonnet-5")
    LiteLLMProvider().judge("g", Answer)
    LiteLLMProvider(model="openai/gpt-4o").judge("g", Answer)
    assert [c["model"] for c in fake.calls] == ["anthropic/claude-sonnet-5", "openai/gpt-4o"]
    assert LiteLLMProvider().label == "litellm:anthropic/claude-sonnet-5"


# -- LP9: gemini dialect -----------------------------------------------------

def test_gemini_models_get_the_gemini_dialect_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key-xyz")
    _with_key(monkeypatch)
    _provider("gemini/gemini-2.5-pro").judge("g", Answer)
    sent = json.dumps(fake.calls[0]["response_format"])
    assert "additionalProperties" not in sent and "$defs" not in sent


def test_non_gemini_models_keep_the_plain_pydantic_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    _provider("openai/gpt-4o").judge("g", Answer)
    assert "additionalProperties" in json.dumps(fake.calls[0]["response_format"])


# -- images ------------------------------------------------------------------

def test_real_screenshots_travel_as_data_url_image_parts(tmp_path: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    shot = tmp_path / "s.png"
    shot.write_bytes(b"\x89PNG-bytes")
    fake = install(monkeypatch, [reply(json.dumps(GOOD)), reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    _provider().judge("see this", Answer, images=[shot, tmp_path / "missing.png"])
    _provider().judge("no images", Answer)
    parts = fake.calls[0]["messages"][0]["content"]
    assert parts[0] == {"type": "text", "text": "see this"}
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,") and len(parts) == 2
    assert fake.calls[1]["messages"][0]["content"] == "no images"
