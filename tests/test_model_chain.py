"""Ollama-primary model chain: order, fallback on error, and the redaction gate.
Fake `litellm` only -- no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from pydantic import BaseModel, ConfigDict

from autotester import providers
from autotester.providers.base import ProviderError
from autotester.providers.model_chain import DEFAULT_ORDER, ModelChainProvider
from autotester.schema.project import ProviderConfig

pytestmark = pytest.mark.usefixtures("no_network")
OLLAMA_KEY = "ollama-key-value-9f3a"


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: str


def _r(verdict: str) -> object:
    return reply(json.dumps({"verdict": verdict}))


@pytest.fixture(autouse=True)
def _env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.delenv("AUTOTESTER_MODEL_ORDER", raising=False)
    monkeypatch.setenv("OLLAMA_API_KEY", OLLAMA_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-value-1b2c")


def test_default_order_is_glm_deepseek_gemini_and_schema_default_uses_it() -> None:
    assert DEFAULT_ORDER == ("ollama_chat/glm-5.3-flash", "ollama_chat/deepseek-v4.1-flash",
                             "gemini/gemini-3.6-flash")
    assert ProviderConfig().agent == ProviderConfig().judge == "model-chain"
    assert providers.for_role(None, "judge").order() == list(DEFAULT_ORDER)


def test_first_tier_answers_with_ollama_cloud_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [_r("ok")])
    monkeypatch.setenv("OLLAMA_API_KEY", OLLAMA_KEY)
    chain = ModelChainProvider()
    assert chain.judge("grade this", Answer).verdict == "ok"
    assert [c["model"] for c in fake.calls] == ["ollama_chat/glm-5.3-flash"]
    assert fake.calls[0]["api_base"] == "https://ollama.com"
    assert fake.calls[0]["api_key"] == OLLAMA_KEY
    assert chain.id == "litellm:ollama_chat/glm-5.3-flash"
    assert chain.usage[0].calls == 1


def test_falls_back_in_order_on_error_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [TimeoutError("slow"), RuntimeError("503"),
                                 _r("gem")])
    monkeypatch.setenv("OLLAMA_API_KEY", OLLAMA_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-value-1b2c")
    chain = ModelChainProvider()
    assert chain.act("do it", Answer).verdict == "gem"
    assert [c["model"] for c in fake.calls] == list(DEFAULT_ORDER)
    assert chain.id == "litellm:gemini/gemini-3.6-flash"


def test_all_tiers_failing_raises_one_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [RuntimeError("a"), RuntimeError("b"), RuntimeError("c")])
    monkeypatch.setenv("OLLAMA_API_KEY", OLLAMA_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-value-1b2c")
    with pytest.raises(ProviderError, match="every tier failed"):
        ModelChainProvider().act("x", Answer)


def test_unconfigured_tier_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [_r("g")])
    real = fake.validate_environment
    fake.validate_environment = lambda model=None, **kw: (
        {"keys_in_environment": False, "missing_keys": ["X"]}
        if kw.get("api_key") is None and model.startswith("ollama") else real(model, **kw))
    monkeypatch.delenv("OLLAMA_API_KEY")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-value-1b2c")
    chain = ModelChainProvider()
    assert chain.act("x", Answer).verdict == "g"
    assert [c["model"] for c in fake.calls] == ["gemini/gemini-3.6-flash"]


def test_order_is_configurable_by_spec_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    provider_id, options = providers.parse_spec(
        "model-chain:gemini/gemini-3.6-flash,ollama_chat/glm-5.3-flash")
    assert providers.get(provider_id, **options).order() == [
        "gemini/gemini-3.6-flash", "ollama_chat/glm-5.3-flash"]
    monkeypatch.setenv("AUTOTESTER_MODEL_ORDER", "ollama_chat/deepseek-v4.1-flash")
    assert ModelChainProvider().order() == ["ollama_chat/deepseek-v4.1-flash"]


def test_secret_in_prompt_is_refused_once_and_never_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [_r("x")])
    monkeypatch.setenv("OLLAMA_API_KEY", OLLAMA_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-value-1b2c")
    with pytest.raises(ProviderError, match="prompt withheld") as err:
        ModelChainProvider().judge(f"token {OLLAMA_KEY}", Answer)
    assert fake.calls == []
    assert OLLAMA_KEY not in str(err.value)
