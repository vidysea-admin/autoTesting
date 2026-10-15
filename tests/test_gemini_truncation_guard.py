"""Truncated Gemini responses stay explicit rather than retrying malformed output."""
from types import SimpleNamespace

import pytest

from autotester.providers.base import ProviderError
from autotester.providers.gemini import GeminiProvider
from autotester.schema.observation import VideoObservation


def test_gemini_truncated_response_is_not_json_repair(monkeypatch):
    import google.genai as genai

    from autotester.providers.litellm_provider import LiteLLMProvider

    monkeypatch.setattr(LiteLLMProvider, "_secret_values", lambda self: self._extra_secrets)
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(parsed=None, text="{", candidates=[
            SimpleNamespace(finish_reason=SimpleNamespace(name="MAX_TOKENS"))])

    monkeypatch.setattr(genai, "Client", lambda **kw: SimpleNamespace(
        models=SimpleNamespace(generate_content=generate)))
    with pytest.raises(ProviderError, match=r"max_output_tokens.*truncated"):
        GeminiProvider(api_key="fake-test-key").act("safe", VideoObservation)
    assert len(calls) == 1
