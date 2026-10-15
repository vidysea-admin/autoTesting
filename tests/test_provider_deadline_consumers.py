"""Late sparse vision, Gemini media and capability results never become logical success."""
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from test_gemini_media_guard import GuardAnswer, sdk_fake, wav_bytes
from test_video_frames import MODEL, capability

from autotester.providers import attempts, vision_probe
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget, reserve_attempt
from autotester.providers.gemini import GeminiProvider
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.observation import VideoObservation
from autotester.schema.video_frames import FrameLimits
from autotester.schema.vision_probe import VisionProbeResult, VisualProbeAnswer

pytestmark = pytest.mark.usefixtures("no_network")
pytest_plugins = ["test_video_frames", "test_vision_probe"]


@pytest.fixture
def clock(monkeypatch, tmp_path):
    now = [0.0]
    monkeypatch.setattr(attempts, "time", SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setattr(LiteLLMProvider, "_secret_values", lambda self: self._extra_secrets)
    return now


def test_late_frame_output_keeps_inclusion_and_billing(monkeypatch, clock, setup):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")
    provider = LiteLLMProvider(model=MODEL, frame_limits=FrameLimits(max_frames=1))
    provider.options["vision_capability"] = capability(provider)

    def late(**kwargs):
        fake.calls.append(kwargs)
        clock[0] = 5
        return reply("{}")

    fake.completion = late
    with pytest.raises(AttemptBudgetExhausted) as error, attempt_budget(1, 5) as budget:
        provider.see_video(Path("synthetic.mp4"), "Observe", VideoObservation)
        pytest.fail("late frame reading reached consumer")
    assert budget.used == len(fake.calls) == 1
    assert error.value.coverage.frames[0].status == "included"
    assert budget.attempts[0].status == "succeeded"
    assert provider.usage[0].input_tokens == 11 and provider.usage[0].failed_calls == 0


def test_gemini_validated_media_is_checked_before_return(monkeypatch, clock, tmp_path):
    calls = sdk_fake(monkeypatch, [{"count": 1}])
    path = tmp_path / "synthetic.wav"
    path.write_bytes(wav_bytes())

    class SlowAnswer(GuardAnswer):
        @classmethod
        def model_validate_json(cls, value, **kwargs):
            result = super().model_validate_json(value, **kwargs)
            clock[0] = 5
            return result

    provider = GeminiProvider(api_key="synthetic-api-key")
    with pytest.raises(AttemptBudgetExhausted), attempt_budget(1, 5) as budget:
        provider._bounded_call("Observe", SlowAnswer, "vision", path, None, None,
                               120, None, None)
        pytest.fail("late parsed SDK result escaped its completion boundary")
    assert len(calls) == budget.used == 1
    assert budget.attempts[0].status == "succeeded"
    assert provider.usage[0].failed_calls == 0 and provider.usage[0].input_tokens is None


@pytest.mark.parametrize("failure", [False, True])
def test_gemini_sdk_response_checks_enclosing_deadline(monkeypatch, clock, tmp_path, failure):
    calls = []

    def handle(request):
        calls.append(request)
        clock[0] = 5
        if failure:
            raise httpx.ReadTimeout("synthetic transport failure")
        return httpx.Response(200, json={"candidates": [{"content": {"role": "model",
            "parts": [{"text": json.dumps({"count": 1})}]}, "finishReason": "STOP"}]})

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kw: httpx.MockTransport(handle))
    path = tmp_path / "synthetic.wav"
    path.write_bytes(wav_bytes())

    class NeverParseAnswer(GuardAnswer):
        @classmethod
        def model_validate_json(cls, value, **kwargs):
            pytest.fail("overdue SDK output reached validation")

    provider = GeminiProvider(api_key="synthetic-api-key")
    with pytest.raises(AttemptBudgetExhausted), attempt_budget(1, 5) as budget:
        provider.see_video(path, "Observe", NeverParseAnswer)
    assert len(calls) == budget.used == 1
    assert budget.attempts[0].status == ("failed" if failure else "succeeded")
    assert provider.usage[0].failed_calls == int(failure)
    assert provider.usage[0].input_tokens is None


def test_probe_cannot_grant_capability_after_deadline(monkeypatch, clock):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-deadline-key")
    provider = LiteLLMProvider(model=MODEL)
    answer = VisualProbeAnswer(images=[dict(left_shape="circle", left_color="red",
        right_shape="square", right_color="blue")] * 2)
    result = VisionProbeResult(model=MODEL,
                               endpoint_sha256=vision_probe.endpoint_fingerprint(provider))
    with pytest.raises(AttemptBudgetExhausted), attempt_budget(1, 5) as budget:
        receipt, _ = reserve_attempt(provider.label, "judge", 10)
        receipt.status = "succeeded"
        clock[0] = 5
        vision_probe._evaluate(provider, result, answer, answer, "a" * 64, "b" * 64, budget)
        pytest.fail("late output was granted a capability")
    assert result.capability is None and result.status == "inconclusive" and fake.calls == []


def test_probe_completion_clears_capability_if_evaluation_runs_late(monkeypatch, clock, transport):
    provider, fake, _, _ = transport
    original = vision_probe._evaluate

    def delayed(*args):
        original(*args)
        clock[0] = 45

    monkeypatch.setattr(vision_probe, "_evaluate", delayed)
    with pytest.raises(AttemptBudgetExhausted) as error:
        vision_probe.probe_vision(provider)
    result = error.value.probe_result
    assert result.status == "inconclusive" and result.capability is None
    assert result.reason == "budget_exhausted"
    assert len(fake.calls) == len(result.attempts) == 1
    assert result.attempts[0].status == "succeeded"
