"""Offline interaction of receipt-selected visual policy and physical deadlines."""
from types import SimpleNamespace

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401

from autotester.providers import attempts, video_frames
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.ollama_cloud import DEEPSEEK
from autotester.providers.vision_roles import VisionChainProvider
from autotester.schema.project import ProviderConfig

pytestmark = pytest.mark.usefixtures("no_network")


def test_receipt_selected_visual_role_refuses_overdue_success(tmp_path, monkeypatch):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    clock = SimpleNamespace(monotonic=lambda: now[0], perf_counter=lambda: now[0])
    now = [100.0]
    monkeypatch.setattr(attempts, "time", clock)
    monkeypatch.setattr("autotester.providers.litellm_provider.time", clock)
    monkeypatch.setattr(LiteLLMProvider, "available", lambda self: True)
    monkeypatch.setattr(LiteLLMProvider, "_endpoint", lambda self: {})
    chain = VisionChainProvider()
    cap = chain._tiers[0].options["vision_capability"]
    assert cap.passed and cap.model == DEEPSEEK
    # Isolate media/routing setup; actual receipt selection, transport and accounting run.
    monkeypatch.setattr(video_frames, "endpoint_fingerprint", lambda provider: cap.endpoint_sha256)
    monkeypatch.setattr(video_frames, "probe", lambda path: (1.0, 16, 16))
    monkeypatch.setattr(video_frames, "TemporaryDirectory",
                        lambda: __import__("contextlib").nullcontext(str(tmp_path)))
    monkeypatch.setattr(video_frames, "_parts", lambda *args: [
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}}])

    def complete(**kwargs):
        fake.calls.append(kwargs)
        now[0] += 6.0
        return reply(ProviderConfig().model_dump_json(), prompt_tokens=13, completion_tokens=5)

    monkeypatch.setattr(fake, "completion", complete)
    with (
        pytest.raises(AttemptBudgetExhausted, match="wall_clock_s"),
        attempt_budget(4, wall_clock_s=5) as budget,
    ):
        chain.see_video(tmp_path / "synthetic.mp4", "neutral fixture", ProviderConfig)
    assert len(fake.calls) == len(budget.attempts) == 1
    receipt = budget.attempts[0]
    assert receipt.provider == "litellm:" + DEEPSEEK and receipt.status == "succeeded"
    assert (receipt.input_tokens, receipt.output_tokens, receipt.latency_s) == (13, 5, 6.0)
    assert chain.served is None and chain.fallback_reasons == ()
    assert sum(u.calls for u in chain.usage) == 1
    assert sum(u.failed_calls for u in chain.usage) == 0
    assert sum(u.input_tokens for u in chain.usage) == 13
    assert sum(u.output_tokens for u in chain.usage) == 5
