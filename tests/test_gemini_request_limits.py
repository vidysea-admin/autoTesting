"""Provider-owned SDK request caps and timeout option rejection stay finite."""
import pytest

from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget, reserve_attempt
from autotester.providers.gemini import GeminiProvider
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.observation import VideoObservation


def test_gemini_provider_owned_cap_exists_without_outer_cap(monkeypatch):
    monkeypatch.setattr(LiteLLMProvider, "_secret_values", lambda self: self._extra_secrets)
    provider = GeminiProvider(api_key="fake-test-key")

    def reserve_requests(*args):
        for _ in range(33):
            reserve_attempt(provider.label, "vision", 120)
        pytest.fail("provider-owned physical cap did not stop request 33")

    monkeypatch.setattr(provider, "_bounded_call", reserve_requests)
    with attempt_budget(100) as budget, pytest.raises(AttemptBudgetExhausted):
        provider.act("safe", VideoObservation)
    assert budget.used == 32


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), 0, -1, 121])
def test_gemini_nonfinite_or_excessive_timeout_is_local_refusal(timeout, monkeypatch):
    from autotester.providers.base import ProviderError

    monkeypatch.setattr(LiteLLMProvider, "_secret_values", lambda self: self._extra_secrets)
    provider = GeminiProvider(api_key="fake-test-key", timeout_s=timeout)
    monkeypatch.setattr(provider, "_bounded_call", lambda *a: pytest.fail("invalid timeout sent"))
    with pytest.raises(ProviderError, match="timeout_s must be finite"):
        provider.act("safe", VideoObservation)
