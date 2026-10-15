"""Text availability policy and sparse-frame transport retain their shared boundaries."""
from pathlib import Path

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from pydantic import BaseModel, ConfigDict
from test_video_frames import MODEL, capability

from autotester.core import image_privacy
from autotester.providers.attempts import attempt_budget
from autotester.providers.base import ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.model_chain import DEFAULT_ORDER, ModelChainProvider
from autotester.providers.video_frames import FrameVisionError
from autotester.schema.observation import VideoObservation, VisionOptions
from autotester.schema.video_frames import FrameLimits

pytestmark = pytest.mark.usefixtures("no_network")
pytest_plugins = ["test_video_frames"]
SECOND = "ollama/deepseek-v4.1-flash"


class CombinedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool


def frame_chain(monkeypatch, responses, *, models=None, verified=None):
    fake = install(monkeypatch, responses)
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-combined-key")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-gemini-key")
    monkeypatch.delenv("AUTOTESTER_MODEL_ORDER", raising=False)
    monkeypatch.delenv("AUTOTESTER_TEXT_FALLBACK_MODEL", raising=False)
    models = models or [MODEL, SECOND]
    verified = models if verified is None else verified
    receipts = {model: capability(LiteLLMProvider(model=model)) for model in verified}
    return fake, ModelChainProvider(model=",".join(models), vision_capabilities=receipts,
                                     frame_limits=FrameLimits(max_frames=2))


def test_tier_constructor_and_video_forwarding_preserve_limits_options(monkeypatch, setup):
    fake, chain = frame_chain(monkeypatch, [reply("{}")])
    result = chain.see_video(Path("synthetic.mp4"), "Observe", VideoObservation,
                             VisionOptions(fps=1, seed=19, max_output_tokens=123,
                                           temperature=0.2))
    assert len(result.visual_coverage.frames) == len(setup) == 2
    assert [frame.timestamp_s for frame in result.visual_coverage.frames] == [0, 1.5]
    assert len(fake.calls) == 1
    assert (fake.calls[0]["seed"], fake.calls[0]["max_tokens"],
            fake.calls[0]["temperature"]) == (19, 123, 0.2)
    assert chain.served == f"litellm:{MODEL}"


def test_explicit_verified_next_tier_serves_missing_capability(monkeypatch, setup):
    fake, chain = frame_chain(monkeypatch, [reply("{}")], verified=[SECOND])
    result = chain.see_video(Path("synthetic.mp4"), "Observe", VideoObservation)
    assert [call["model"] for call in fake.calls] == [SECOND]
    assert chain.served == f"litellm:{SECOND}"
    assert chain.fallback_reasons == (f"litellm:{MODEL}: capability",)
    assert result.visual_coverage.frames[0].status == "included"


@pytest.mark.parametrize("refusal", ["withheld", "options"])
def test_frame_privacy_and_invalid_options_stop_before_next_tier(monkeypatch, setup, refusal):
    fake, chain = frame_chain(monkeypatch, [reply("{}")])
    options = None
    if refusal == "withheld":
        monkeypatch.setattr(image_privacy, "_local_ocr", lambda path: "")
    else:
        options = VisionOptions(max_output_tokens=0)
    with pytest.raises(FrameVisionError) as error:
        chain.see_video(Path("synthetic.mp4"), "Observe", VideoObservation, options)
    assert fake.calls == [] and chain.fallback_reasons == ()
    assert chain.served is None
    assert error.value.coverage.text_unavailable and error.value.coverage.audio_unavailable
    assert len(setup) == (2 if refusal == "withheld" else 0)
    assert all(frame.status == "withheld" for frame in error.value.coverage.frames)


def test_default_video_never_reaches_implicit_gemini_and_keeps_coverage(monkeypatch, setup):
    fake = install(monkeypatch, [TimeoutError("private details"), TimeoutError("private details"),
                               reply("{}")])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-combined-key")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-gemini-key")
    monkeypatch.delenv("AUTOTESTER_MODEL_ORDER", raising=False)
    monkeypatch.delenv("AUTOTESTER_TEXT_FALLBACK_MODEL", raising=False)
    chain = ModelChainProvider(frame_limits=FrameLimits(max_frames=1))
    for tier in chain._tiers:
        tier.options["vision_capability"] = capability(tier)
    with attempt_budget(3) as budget, pytest.raises(ProviderError) as error:
        chain.see_video(Path("synthetic.mp4"), "Observe", VideoObservation)
    assert [call["model"] for call in fake.calls] == list(DEFAULT_ORDER)
    assert budget.used == 2 and chain.served is None
    assert chain.fallback_reasons == tuple(f"litellm:{model}: service" for model in DEFAULT_ORDER)
    assert error.value.coverage.frames[0].status == "included"
    assert error.value.coverage.text_unavailable and error.value.coverage.audio_unavailable
    assert all(usage.input_tokens is usage.output_tokens is None for usage in chain.usage)
    assert "private details" not in str(error.value)


def test_malformed_visual_output_is_terminal_with_coverage(monkeypatch, setup):
    fake, chain = frame_chain(monkeypatch, [reply("bad"), reply("bad"), reply("{}")])
    with attempt_budget(6) as budget, pytest.raises(ProviderError, match="schema") as error:
        chain.see_video(Path("synthetic.mp4"), "Observe", VideoObservation)
    assert budget.used == len(fake.calls) == 2
    assert {call["model"] for call in fake.calls} == {MODEL}
    assert chain.fallback_reasons == () and chain.served is None
    assert error.value.coverage.frames[0].status == "included"


def test_non_ollama_chain_output_keeps_strict_validation(monkeypatch, setup):
    fake, chain = frame_chain(monkeypatch, [reply('{"ok":"true"}')],
                               models=["gemini/synthetic-text"])
    with pytest.raises(ProviderError, match="schema"):
        chain.act("Decide", CombinedAnswer)
    assert len(fake.calls) == 1 and chain.served is None
