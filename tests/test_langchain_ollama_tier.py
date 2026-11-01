"""E2.1-E2.3 (AT-1413): the legacy `langchain-fallback` chain reaches Ollama cloud on a key alone.

`OLLAMA_API_KEY` alone adds an `ollama` tier at the cloud URL, ahead of Gemini (the order
`autotester providers` reports), and a capped tier falls through to the next with the winner named.
Fakes only: no SDK import, no network, no real key value.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from pydantic import BaseModel

from autotester.providers import langchain_fallback as lcf
from autotester.providers import ollama_cloud
from autotester.providers.langchain_fallback import LangChainFallbackProvider

_ENV = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OLLAMA_API_KEY",
        "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OPENAI_API_KEY")


class Answer(BaseModel):
    result: str


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV:
        monkeypatch.delenv(key, raising=False)


def _names() -> list[str]:
    return [name for name, _ in lcf._default_chain()]


def test_e2_1_a_cloud_key_alone_adds_the_ollama_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "x")
    assert "ollama" in dict(lcf._default_chain())


def test_e2_1_nothing_configured_adds_no_ollama_tier() -> None:
    assert lcf._default_chain() == []


def test_e2_1_a_base_url_alone_still_adds_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    assert _names() == ["ollama"]


def test_e2_1_the_factory_is_not_invoked_while_building_the_chain(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "x")
    monkeypatch.setitem(sys.modules, "langchain_ollama", None)  # an import would raise
    assert _names() == ["ollama"]


def _fake_ollama(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    built: list[dict[str, Any]] = []

    class ChatOllama:
        def __init__(self, **kwargs: Any) -> None:
            built.append(kwargs)

    monkeypatch.setitem(sys.modules, "langchain_ollama",
                        types.SimpleNamespace(ChatOllama=ChatOllama))
    return built


def test_e2_1_the_cloud_tier_targets_the_cloud_url_with_a_bearer_header_and_glm(
        monkeypatch: pytest.MonkeyPatch) -> None:
    built = _fake_ollama(monkeypatch)
    monkeypatch.setenv("OLLAMA_API_KEY", "k-test")
    dict(lcf._default_chain())["ollama"]()
    kwargs = built[0]
    assert kwargs["base_url"] == ollama_cloud.OLLAMA_CLOUD_URL
    assert kwargs["model"] == ollama_cloud.GLM.split("/", 1)[1]
    assert kwargs["client_kwargs"]["headers"] == {"Authorization": "Bearer k-test"}
    assert kwargs["client_kwargs"]["timeout"] == lcf.JUDGE_TIMEOUT_S


def test_e2_1_ollama_model_overrides_the_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    built = _fake_ollama(monkeypatch)
    monkeypatch.setenv("OLLAMA_API_KEY", "k-test")
    monkeypatch.setenv("OLLAMA_MODEL", "other-model")
    dict(lcf._default_chain())["ollama"]()
    assert built[0]["model"] == "other-model"


def test_e2_1_a_local_daemon_keeps_its_url_default_model_and_sends_no_header(
        monkeypatch: pytest.MonkeyPatch) -> None:
    built = _fake_ollama(monkeypatch)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    dict(lcf._default_chain())["ollama"]()
    assert built[0]["base_url"] == "http://127.0.0.1:11434"
    assert built[0]["model"] == "llama3"
    assert "headers" not in built[0]["client_kwargs"]


def test_e2_2_the_order_is_anthropic_ollama_gemini_chatgpt(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("OLLAMA_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert _names() == ["anthropic", "ollama", "gemini", "chatgpt"]


def test_e2_2_ollama_precedes_gemini_without_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "x")
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    assert _names() == ["ollama", "gemini"]


class _Tier:
    def __init__(self, parsed: Any = None, error: Exception | None = None) -> None:
        self._parsed, self._error = parsed, error

    def with_structured_output(self, schema: Any, include_raw: bool = False) -> _Tier:
        return self

    def invoke(self, prompt: Any) -> dict[str, Any]:
        if self._error is not None:
            raise self._error
        return {"parsed": self._parsed, "raw": None}


def _chain(*tiers: tuple[str, _Tier]) -> list:
    return [(name, (lambda t=tier: t)) for name, tier in tiers]


def test_e2_3_a_capped_gemini_falls_through_to_ollama_and_ollama_is_named() -> None:
    capped = RuntimeError("429 RESOURCE_EXHAUSTED: spending cap")
    provider = LangChainFallbackProvider(chain=_chain(
        ("gemini", _Tier(error=capped)), ("ollama", _Tier(parsed=Answer(result="from ollama")))))
    assert provider.judge("p", Answer).result == "from ollama"
    assert provider.id == "ollama"


def test_e2_3_a_failing_ollama_first_falls_through_to_gemini() -> None:
    provider = LangChainFallbackProvider(chain=_chain(
        ("ollama", _Tier(error=RuntimeError("401"))),
        ("gemini", _Tier(parsed=Answer(result="from gemini")))))
    assert provider.judge("p", Answer).result == "from gemini"
    assert provider.id == "gemini"
