"""LiteLLM fake-provider contracts and one guarded, mocked installed-SDK admission."""

from __future__ import annotations

import json
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

import pytest
from litellm_fake import install, reply
from litellm_fake import no_network as no_network
from pydantic import BaseModel, ConfigDict

from autotester.providers.base import ProviderError, Unsupported
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.project import ProviderProbeAnswer

pytestmark = pytest.mark.usefixtures("no_network")

GOOD = {"verdict": "pass", "score": 3, "inner": {"note": "ok"}}
SECRET = "hunter2-very-secret-value"
State = Enum("State", {"READY": "ready"})
class Inner(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str
class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: str
    score: int
    inner: Inner
    dated: date | None = None
    state: State | None = None
@pytest.fixture(autouse=True)
def _isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))  # no real .env in the guard
def _provider(model: str = "openai/gpt-4o", **options: Any) -> LiteLLMProvider:
    return LiteLLMProvider(model=model, **options)
def _with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_API_KEY", "k-for-test")
@pytest.mark.parametrize("strategy", ["schema", "tool", "json"])
@pytest.mark.parametrize("role", ["judge", "agent"])
def test_schema_strategy_sends_response_format_and_returns_the_typed_object(
        monkeypatch: pytest.MonkeyPatch, strategy: str, role: str) -> None:
    data = {**GOOD, "dated": "2026-10-08", "state": "ready"}
    response = reply(tool_args=data) if strategy == "tool" else reply(json.dumps(data))
    fake = install(monkeypatch, [response], response_schema=strategy == "schema",
                   function_calling=strategy == "tool")
    _with_key(monkeypatch)
    out = getattr(_provider(), "act" if role == "agent" else "judge")("grade this", Answer)
    assert out == Answer.model_validate(data)
    assert out.score == 3 and out.dated == date(2026, 10, 8) and out.state is State.READY
    assert len(fake.calls) == 1
    kw = fake.calls[0]
    if strategy == "schema":
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

@pytest.mark.parametrize("strategy", ["schema", "tool", "json"])
@pytest.mark.parametrize("role", ["judge", "agent"])
@pytest.mark.parametrize("data", [{"verdict": "pass"}, {**GOOD, "score": "3"},
                                 {**GOOD, "score": True}, {**GOOD, "MODEL-KEY-CANARY": 0},
                                 {**GOOD, "https://endpoint-CANARY.test/v1": 0}])
def test_schema_mismatch_is_an_error_not_a_coerced_answer(
        monkeypatch, strategy, role, data, no_network):
    response = reply(tool_args=data) if strategy == "tool" else reply(json.dumps(data))
    fake = install(monkeypatch, [response, response], response_schema=strategy == "schema",
                   function_calling=strategy == "tool")
    _with_key(monkeypatch)
    provider = _provider()
    with pytest.raises(ProviderError, match=role) as info:
        getattr(provider, "act" if role == "agent" else "judge")(
            "grade this nonsecret MODEL-KEY-CANARY", Answer)
    assert "openai/gpt-4o" in str(info.value)
    assert len(fake.calls) == provider.usage[0].calls == (2 if strategy == "json" else 1)
    assert "MODEL-KEY-CANARY" not in str(info.value)
    assert "https://endpoint-CANARY.test/v1" not in str(info.value)
    assert info.value.__suppress_context__ and not no_network
    if strategy == "json":
        assert fake.calls[-1]["messages"][-1]["content"].endswith(
            "Problem: schema validation failed")

def test_json_mode_that_stays_broken_after_the_repair_raises(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply("x"), reply("y")], response_schema=False,
                   function_calling=False)
    _with_key(monkeypatch)
    with pytest.raises(ProviderError, match="agent"):
        _provider("ollama/llama3.2").act("p", Answer)
    assert len(fake.calls) == 2

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
    assert row.provider == provider.label
    assert (row.role, row.calls, row.input_tokens, row.output_tokens) == ("judge", 1, 21, 5)
    assert spans[0]["provider"] == provider.label == "litellm:openai/gpt-4o"
    assert spans[0]["input_tokens"] == 21 and spans[0]["fed_id"] == "c1"

def test_judge_is_deterministic_and_act_is_not_forced_cold(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD)), reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    _provider().judge("g", Answer)
    _provider().act("a", Answer)
    assert fake.calls[0]["temperature"] == 0 and "temperature" not in fake.calls[1]

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

@pytest.mark.parametrize("strategy", ["schema", "tool", "json"])
@pytest.mark.parametrize("role", ["judge", "agent"])
def test_probe_is_one_bounded_attempt_for_every_strategy_and_role(monkeypatch, strategy, role):
    response = reply(tool_args={"answer": 7}) if strategy == "tool" else reply('{"answer":7}')
    fake = install(monkeypatch, [response], response_schema=strategy == "schema",
                   function_calling=strategy == "tool")
    provider = _provider()
    result = provider.probe("synthetic", ProviderProbeAnswer, role=role, prompt_file="probe.md")
    assert result.answer == 7 and len(fake.calls) == 1
    kwargs = fake.calls[0]
    assert (kwargs["num_retries"], kwargs["timeout"], kwargs["max_tokens"]) == (0, 30, 64)
    assert "fallbacks" not in kwargs and "api_key" not in kwargs
    assert kwargs["messages"][0]["content"].startswith("synthetic")
    assert provider.usage[0].provider == provider.label and provider.usage[0].calls == 1

@pytest.mark.parametrize("content", [None, "", "broken", '{"answer":"7"}', '{"answer":true}',
                                     '{"answer":7,"raw":"canary"}',
                                     '{"answer":7,"MODEL-KEY-CANARY":0}'])
def test_json_probe_rejects_bad_answers_without_the_ordinary_repair(monkeypatch, content):
    fake = install(monkeypatch, [reply(content), reply('{"answer":7}')],
                   response_schema=False, function_calling=False)
    provider = _provider()
    with pytest.raises(ProviderError) as info:
        provider.probe("synthetic", ProviderProbeAnswer, role="judge")
    assert len(fake.calls) == 1 and provider.usage[0].calls == 1
    assert len(fake.responses) == 1
    assert "MODEL-KEY-CANARY" not in str(info.value) and info.value.__suppress_context__

@pytest.mark.parametrize("probe", [False, True])
def test_dispatched_transport_failure_is_counted_once_and_withholds_canaries(monkeypatch, probe):
    fake = install(monkeypatch, [RuntimeError("prompt-canary key-canary endpoint-canary")])
    monkeypatch.setenv("LITELLM_API_KEY", "key-canary")
    provider = _provider()
    with pytest.raises(ProviderError) as error:
        if probe:
            provider.probe("prompt-canary", ProviderProbeAnswer, role="judge")
        else:
            provider.judge("prompt-canary", Answer)
    assert len(fake.calls) == 1 and provider.usage[0].calls == 1
    assert provider.usage[0].input_tokens == provider.usage[0].output_tokens == 0
    assert all(canary not in str(error.value) for canary in
               ("prompt-canary", "key-canary", "endpoint-canary"))

def test_shared_probe_checks_semantics_and_legacy_refuses_before_dispatch(monkeypatch):
    from autotester.providers import probe_model

    fake = install(monkeypatch, [reply('{"answer":8}')])
    with pytest.raises(ProviderError, match="incorrect answer"):
        probe_model(spec="litellm:openai/gpt-4o")
    assert len(fake.calls) == 1
    with pytest.raises(Unsupported, match="single-attempt"):
        probe_model(spec="langchain-fallback")
    with pytest.raises(Unsupported, match="vision"):
        probe_model(spec="litellm:openai/gpt-4o", role="vision")
    assert len(fake.calls) == 1

def test_installed_sdk_probe_uses_mock_transport_without_outbound(monkeypatch, no_network):
    import inspect
    import socket
    import sys
    import threading
    from importlib.metadata import version

    import httpx

    monkeypatch.delitem(sys.modules, "litellm", raising=False)
    monkeypatch.setenv("LITELLM_MODE", "PRODUCTION")
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    monkeypatch.setenv("LITELLM_API_BASE", "http://sdk-admission.test/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-synthetic-admission-only")
    internal, blocked = [], socket.socket.connect

    def witness_connect(sock, address):
        frame = inspect.currentframe().f_back
        if (frame.f_code is socket._fallback_socketpair.__code__
                and frame.f_locals.get("csock") is sock
                and address == (frame.f_locals.get("addr"), frame.f_locals.get("port"))):
            internal.append((threading.get_ident(), sock.fileno(), address))
        return blocked(sock, address)

    monkeypatch.setattr(socket.socket, "connect", witness_connect)
    from autotester.providers.litellm_provider import _load_litellm

    sdk = _load_litellm()
    from litellm.llms.openai.openai import OpenAIChatCompletion

    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={"id": "synthetic", "object": "chat.completion",
            "created": 0, "model": "gpt-4o", "choices": [{"index": 0,
            "message": {"role": "assistant", "content": '{"answer":7}'},
            "finish_reason": "stop"}], "usage": {"prompt_tokens": 4,
            "completion_tokens": 3, "total_tokens": 7}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(OpenAIChatCompletion, "_get_sync_http_client",
                            staticmethod(lambda: client))
        provider = _provider()
        answer = provider.probe("sum 3 and 4", ProviderProbeAnswer, role="judge")
    assert version("litellm") == "1.104.0" and sdk.telemetry is False
    assert not (sdk.callbacks or sdk.success_callback or sdk.failure_callback)
    assert answer.answer == 7 and len(seen) == 1 and no_network == [p[2] for p in internal]
    body = json.loads(seen[0].content)
    assert body["max_tokens"] == 64 and provider.usage[0].calls == 1
