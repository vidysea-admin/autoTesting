"""Offline availability-only text fallback, including refusal and budget boundaries."""
from pathlib import Path

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from pydantic import BaseModel, ConfigDict

from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.base import ProviderError, Unsupported
from autotester.providers.model_chain import DEFAULT_ORDER, TEXT_FALLBACK, ModelChainProvider

pytestmark = pytest.mark.usefixtures("no_network")


class TextAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool


class StatusFailure(Exception):
    def __init__(self, status):
        self.status_code = status


def setup_chain(monkeypatch, tmp_path, responses):
    fake = install(monkeypatch, responses)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setenv("OLLAMA_API_KEY", "fake-ollama-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.delenv("AUTOTESTER_MODEL_ORDER", raising=False)
    monkeypatch.delenv("AUTOTESTER_TEXT_FALLBACK_MODEL", raising=False)
    return fake, ModelChainProvider()


@pytest.mark.parametrize("failure", [StatusFailure(401), StatusFailure(503),
                                     ConnectionError("offline"), Unsupported("text")])
def test_allowlisted_failure_reaches_guarded_gemini(monkeypatch, tmp_path, failure):
    response = reply('{"ok":true}')
    response.usage = None
    fake, chain = setup_chain(monkeypatch, tmp_path, [failure, failure, response])
    with attempt_budget(3, wall_clock_s=4) as budget:
        assert chain.act("prompt", TextAnswer).ok
    assert [c["model"] for c in fake.calls] == [*DEFAULT_ORDER, TEXT_FALLBACK]
    assert chain.served == f"litellm:{TEXT_FALLBACK}"
    assert len(chain.fallback_reasons) == 2
    assert budget.used == 3 and budget.attempts[-1].status == "succeeded"
    assert chain.usage[-1].input_tokens is chain.usage[-1].output_tokens is None
    assert all(0 < c["timeout"] <= 4 and c["num_retries"] == 0 for c in fake.calls)


@pytest.mark.parametrize("failure", [StatusFailure(403), StatusFailure(400),
                                     ValueError("privacy refusal"),
                                     ProviderError("invalid domain/write authorization"),
                                     RuntimeError("unknown failure")])
def test_ambiguous_and_policy_failures_stop(monkeypatch, tmp_path, failure):
    fake, chain = setup_chain(monkeypatch, tmp_path, [failure, reply('{"ok":true}')])
    with pytest.raises(ProviderError):
        chain.act("prompt", TextAnswer)
    assert len(fake.calls) == 1 and not chain.fallback_reasons
    assert chain.served is None


def test_malformed_output_repairs_once_then_stops(monkeypatch, tmp_path):
    fake, chain = setup_chain(monkeypatch, tmp_path,
                              [reply('{"ok":"true"}'), reply('{"ok":"true"}')])
    with attempt_budget(6) as budget, pytest.raises(ProviderError, match="schema"):
        chain.act("prompt", TextAnswer)
    assert budget.used == len(fake.calls) == 2
    assert {c["model"] for c in fake.calls} == {DEFAULT_ORDER[0]}
    assert not chain.fallback_reasons


@pytest.mark.parametrize("limit,seconds", [(2, 30), (6, 0)])
def test_enclosing_budget_never_falls_through(monkeypatch, tmp_path, limit, seconds):
    fake, chain = setup_chain(monkeypatch, tmp_path,
                              [TimeoutError(), TimeoutError(), reply('{"ok":true}')])
    with (pytest.raises(AttemptBudgetExhausted),
          attempt_budget(limit, wall_clock_s=seconds) as budget):
        chain.act("prompt", TextAnswer)
    assert len(fake.calls) == budget.used == (2 if seconds else 0)
    assert all(c["model"] != TEXT_FALLBACK for c in fake.calls)


def test_implicit_gemini_excludes_images_and_explicit_order_wins(monkeypatch, tmp_path):
    fake, chain = setup_chain(monkeypatch, tmp_path, [TimeoutError(), TimeoutError()])
    with pytest.raises(ProviderError, match="every tier failed"):
        chain.judge("prompt", TextAnswer, images=[Path("unread.png")])
    assert [c["model"] for c in fake.calls] == list(DEFAULT_ORDER)
    assert ModelChainProvider(model=DEFAULT_ORDER[0]).order() == [DEFAULT_ORDER[0]]
    monkeypatch.setenv("AUTOTESTER_MODEL_ORDER", DEFAULT_ORDER[1])
    assert ModelChainProvider().order() == [DEFAULT_ORDER[1]]


def test_missing_ollama_keys_and_fallback_model_override(monkeypatch, tmp_path):
    fake, _ = setup_chain(monkeypatch, tmp_path, [reply('{"ok":true}')])
    monkeypatch.delenv("OLLAMA_API_KEY")
    fake.validate_environment = lambda model=None, **kw: {
        "keys_in_environment": model.startswith("gemini/"), "missing_keys": ["OLLAMA_API_KEY"]}
    monkeypatch.setenv("AUTOTESTER_TEXT_FALLBACK_MODEL", "gemini/configured-text")
    chain = ModelChainProvider()
    assert chain.act("prompt", TextAnswer).ok
    assert [c["model"] for c in fake.calls] == ["gemini/configured-text"]
    assert len(chain.fallback_reasons) == 2


def test_secret_never_reaches_any_tier(monkeypatch, tmp_path):
    fake, chain = setup_chain(monkeypatch, tmp_path, [])
    with pytest.raises(ProviderError, match="prompt withheld"):
        chain.act("fake-gemini-key", TextAnswer)
    assert fake.calls == [] and chain.served is None
