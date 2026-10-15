"""Fake-clock logical completion checks preserve physical records and terminal deadlines."""
import traceback
from types import SimpleNamespace

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from pydantic import BaseModel, ConfigDict

from autotester.providers import attempts, litellm_provider
from autotester.providers.attempts import (
    AttemptBudgetExhausted,
    attempt_budget,
    check_deadline,
    reserve_attempt,
)
from autotester.providers.base import ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.model_chain import ModelChainProvider

pytestmark = pytest.mark.usefixtures("no_network")


class DeadlineAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool


@pytest.fixture
def clock(monkeypatch, tmp_path):
    now = [0.0]
    timer = SimpleNamespace(monotonic=lambda: now[0], perf_counter=lambda: now[0])
    monkeypatch.setattr(attempts, "time", timer)
    monkeypatch.setattr(litellm_provider, "time", timer)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return now


@pytest.mark.parametrize("elapsed,expired", [(4.999, False), (5.0, True)])
def test_absolute_deadline_edge(clock, elapsed, expired):
    clock[0] = elapsed
    if expired:
        with pytest.raises(AttemptBudgetExhausted, match="wall_clock_s"):
            check_deadline(5)
    else:
        check_deadline(5)


def test_normal_scope_exit_rejects_late_success(clock):
    with pytest.raises(AttemptBudgetExhausted, match="wall_clock_s"), attempt_budget(1, 5):
        reserve_attempt("fake", "judge", 10)
        clock[0] = 5


@pytest.mark.parametrize("error", [ProviderError("privacy refusal"),
                                  ValueError("validation refusal")])
def test_scope_exit_preserves_original_rejection(clock, error):
    with pytest.raises(type(error), match=str(error)), attempt_budget(1, 5):
        clock[0] = 6
        raise error


def test_live_inner_scope_cannot_hide_expired_outer(clock):
    with pytest.raises(AttemptBudgetExhausted), attempt_budget(2, 5), attempt_budget(2, 50):
        reserve_attempt("fake", "judge", 10)
        clock[0] = 5
        with pytest.raises(AttemptBudgetExhausted):
            check_deadline()


def completion(monkeypatch, clock, *, elapsed, failure=False):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")
    monkeypatch.delenv("AUTOTESTER_MODEL_ORDER", raising=False)

    def complete(**kwargs):
        fake.calls.append(kwargs)
        clock[0] = elapsed
        if failure:
            raise TimeoutError("synthetic service failure")
        return reply('{"ok":true}')

    fake.completion = complete
    return fake


def test_final_allowed_call_succeeds_before_deadline(monkeypatch, clock):
    fake = completion(monkeypatch, clock, elapsed=4)
    provider = LiteLLMProvider(model="ollama_chat/synthetic")
    with attempt_budget(1, 5) as budget:
        assert provider.act("Decide", DeadlineAnswer).ok
    assert len(fake.calls) == budget.used == 1
    assert budget.attempts[0].status == "succeeded"
    assert (provider.usage[0].input_tokens, provider.usage[0].output_tokens) == (11, 7)


@pytest.mark.parametrize("failure", [False, True])
def test_late_chain_response_preserves_usage_and_never_falls_back(monkeypatch, clock, failure):
    fake = completion(monkeypatch, clock, elapsed=5, failure=failure)
    provider = ModelChainProvider()
    with pytest.raises(AttemptBudgetExhausted), attempt_budget(3, 5) as budget:
        provider.act("Decide", DeadlineAnswer)
        pytest.fail("late logical success reached the consumer")
    assert len(fake.calls) == budget.used == 1
    assert provider.served is None and provider.fallback_reasons == ()
    assert budget.attempts[0].status == ("failed" if failure else "succeeded")
    assert budget.attempts[0].latency_s == 5
    assert provider.usage[0].calls == 1 and provider.usage[0].failed_calls == int(failure)
    assert provider.usage[0].input_tokens == (None if failure else 11)


def test_direct_transport_deadline_is_anchored_before_response(monkeypatch, clock):
    fake = completion(monkeypatch, clock, elapsed=120)
    provider = LiteLLMProvider(model="ollama_chat/synthetic")
    with pytest.raises(AttemptBudgetExhausted):
        provider.act("Decide", DeadlineAnswer)
    assert len(fake.calls) == 1 and provider.usage[0].input_tokens == 11


def test_overdue_malformed_response_never_triggers_repair(monkeypatch, clock):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")

    def overdue(**kwargs):
        fake.calls.append(kwargs)
        clock[0] = 120
        return reply("bad" if len(fake.calls) == 1 else '{"ok":true}')

    fake.completion = overdue
    provider = LiteLLMProvider(model="ollama_chat/synthetic")
    with pytest.raises(AttemptBudgetExhausted):
        provider.act("Decide", DeadlineAnswer)
    assert len(fake.calls) == provider.usage[0].calls == 1
    assert provider.usage[0].failed_calls == 0 and provider.usage[0].input_tokens == 11


def test_json_repair_never_restarts_enclosing_deadline(monkeypatch, clock):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")

    def repaired(**kwargs):
        fake.calls.append(kwargs)
        clock[0] = 3 if len(fake.calls) == 1 else 6
        return reply("bad" if len(fake.calls) == 1 else '{"ok":true}')

    fake.completion = repaired
    provider = LiteLLMProvider(model="ollama_chat/synthetic")
    with pytest.raises(AttemptBudgetExhausted), attempt_budget(2, 5) as budget:
        provider.act("Decide", DeadlineAnswer)
        pytest.fail("repair returned after the original deadline")
    assert budget.used == len(fake.calls) == provider.usage[0].calls == 2
    assert all(receipt.status == "succeeded" for receipt in budget.attempts)
    assert fake.calls[1]["timeout"] == 2


def test_expired_vendor_failure_suppresses_canary_traceback(monkeypatch, clock):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")
    monkeypatch.delenv("AUTOTESTER_MODEL_ORDER", raising=False)
    canary = "".join(chr(value) for value in [86, 69, 78, 68, 79, 82, 45, 67, 65, 78, 65, 82, 89])

    def late_failure(**kwargs):
        fake.calls.append(kwargs)
        clock[0] = 5
        raise TimeoutError(canary)

    fake.completion = late_failure
    provider = ModelChainProvider()
    with pytest.raises(AttemptBudgetExhausted) as error, attempt_budget(3, 5) as budget:
        provider.act("Decide", DeadlineAnswer)
    rendered = "".join(traceback.format_exception(error.value))
    if canary in rendered:
        pytest.fail("deadline error exposed vendor exception context", pytrace=False)
    assert error.value.__suppress_context__
    assert str(error.value) == "provider attempt budget exhausted: wall_clock_s"
    assert budget.used == len(fake.calls) == 1 and provider.usage[0].failed_calls == 1
    assert provider.fallback_reasons == ()


@pytest.mark.parametrize("repair", [False, True])
@pytest.mark.parametrize("outer", [False, True])
def test_slow_validation_checks_original_deadlines(monkeypatch, clock, repair, outer):
    replies = [reply("bad")] if repair else []
    fake = install(monkeypatch, [*replies, reply('{"ok":true}')])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")

    class SlowAnswer(DeadlineAnswer):
        @classmethod
        def model_validate_json(cls, value, **kwargs):
            result = super().model_validate_json(value, **kwargs)
            clock[0] = 5 if outer else 120
            return result

    provider = LiteLLMProvider(model="ollama_chat/synthetic")
    if outer:
        with pytest.raises(AttemptBudgetExhausted), attempt_budget(2, 5) as budget:
            provider.act("Decide", SlowAnswer)
            pytest.fail("overdue validated output reached the consumer")
        assert budget.used == len(fake.calls)
        assert all(receipt.status == "succeeded" for receipt in budget.attempts)
    else:
        with pytest.raises(AttemptBudgetExhausted):
            provider.act("Decide", SlowAnswer)
    assert len(fake.calls) == provider.usage[0].calls == (2 if repair else 1)
    assert provider.usage[0].failed_calls == 0


def test_direct_repair_keeps_its_own_physical_timeout_policy(monkeypatch, clock):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")

    def repaired(**kwargs):
        fake.calls.append(kwargs)
        clock[0] = 3
        return reply("bad" if len(fake.calls) == 1 else '{"ok":true}')

    class SlowRepair(DeadlineAnswer):
        @classmethod
        def model_validate_json(cls, value, **kwargs):
            result = super().model_validate_json(value, **kwargs)
            clock[0] = 121
            return result

    fake.completion = repaired
    provider = LiteLLMProvider(model="ollama_chat/synthetic")
    assert provider.act("Decide", SlowRepair).ok
    assert len(fake.calls) == 2 and all(call["timeout"] == 120 for call in fake.calls)
