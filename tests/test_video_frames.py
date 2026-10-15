"""Synthetic payload, privacy and finite-attempt checks; never real product media."""

import base64
import io
import math
from pathlib import Path

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from PIL import Image

from autotester.core import image_privacy
from autotester.providers import video_frames
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.model_chain import ModelChainProvider
from autotester.schema.observation import VideoObservation, VisionOptions
from autotester.schema.video_frames import FrameLimits, VisionCapability

pytestmark = pytest.mark.usefixtures("no_network")
MODEL = "ollama/glm-5.3-flash"
OCR = ("level\tpage_num\tblock_num\tpar_num\tline_num\tconf\tleft\ttop\twidth\theight\ttext\n"
       "5\t1\t1\t1\t1\t99\t1\t1\t20\t3\tPRIVATE\n")


def capability(provider):
    return VisionCapability(model=provider.options["model"], passed=True,
                            endpoint_sha256=video_frames.endpoint_fingerprint(provider),
                            fixture_sha256="a" * 64, output_sha256="b" * 64)


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setattr(video_frames, "probe", lambda path: (3.0, 40, 20))
    monkeypatch.setattr(image_privacy, "_local_ocr", lambda path: OCR)
    extracted = []

    def extract(path, timestamp, output):
        Image.new("RGB", (40, 20), "red").save(output, format="PNG")
        extracted.append((timestamp, output, output.read_bytes()))
        return True

    monkeypatch.setattr(video_frames, "extract_frame", extract)
    return extracted


def provider(monkeypatch, responses=None, **kwargs):
    fake = install(monkeypatch, responses or [reply("{}")])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-test-key")
    instance = LiteLLMProvider(model=MODEL, **kwargs)
    instance.options["vision_capability"] = capability(instance)
    return instance, fake


def test_real_sanitized_bytes_and_clip_relative_timestamp_payload(monkeypatch, setup):
    instance, fake = provider(monkeypatch, frame_limits=FrameLimits(max_frames=3))
    result = instance.see_video(Path("recording.mp4"), "Observe", VideoObservation)
    parts = fake.calls[0]["messages"][0]["content"]
    stamps = [p["text"] for p in parts if p["type"] == "text"][1:]
    assert stamps == [f"Frame {i}, clip-relative seconds {i:.6f}" for i in range(3)]
    images = [p["image_url"]["url"] for p in parts if p["type"] == "image_url"]
    assert len(images) == 3
    for url in images:
        assert url.startswith("data:image/png;base64,")
        data = base64.b64decode(url.split(",")[1])
        with Image.open(io.BytesIO(data)) as safe:
            assert safe.getpixel((2, 2)) == (0, 0, 0)
            assert safe.getpixel((2, 15)) == (255, 0, 0)
        assert data != setup[0][2]
    assert result.visual_coverage.text_unavailable
    assert result.visual_coverage.audio_unavailable
    assert result.visual_coverage.sampling_limited
    assert [f.timestamp_s for f in result.visual_coverage.frames] == [0, 1, 2]
    assert instance.usage[0].role == "vision"
    assert fake.calls[0]["seed"] == 7
    assert fake.calls[0]["max_tokens"] == 65536
    assert not any(path.exists() for _, path, _ in setup)


def test_partial_withholding_retains_original_index_and_time(monkeypatch, setup):
    instance, fake = provider(monkeypatch, frame_limits=FrameLimits(max_frames=3))
    calls = []

    def ocr(path):
        calls.append(path)
        if len(calls) == 2:
            raise ValueError("OCR failure containing private data")
        return OCR

    monkeypatch.setattr(image_privacy, "_local_ocr", ocr)
    result = instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    evidence = result.visual_coverage.frames
    assert [(f.index, f.timestamp_s, f.status) for f in evidence] == [
        (0, 0, "included"), (1, 1, "withheld"), (2, 2, "included")]
    parts = fake.calls[0]["messages"][0]["content"]
    assert [p["text"] for p in parts if p["type"] == "text"][1:] == [
        "Frame 0, clip-relative seconds 0.000000", "Frame 2, clip-relative seconds 2.000000"]
    assert not any(path.exists() for path in calls)
    assert "private data" not in str(evidence)


def test_all_withheld_never_sends_text_only_success(monkeypatch, setup):
    instance, fake = provider(monkeypatch)
    monkeypatch.setattr(image_privacy, "_local_ocr", lambda path: "")
    with pytest.raises(video_frames.FrameVisionError, match="all_frames_withheld") as error:
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert all(frame.status == "withheld" for frame in error.value.coverage.frames)
    assert fake.calls == []


@pytest.mark.parametrize("fps", [0, -1, math.inf, math.nan, 11])
def test_invalid_sampling_fails_before_decode(monkeypatch, setup, fps):
    instance, fake = provider(monkeypatch)
    with pytest.raises(video_frames.FrameVisionError, match="invalid_fps"):
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation, VisionOptions(fps=fps))
    assert not setup and not fake.calls


@pytest.mark.parametrize("probe_result,reason", [
    ((0, 0, 0), "unsupported_or_audio_only_media"),
    ((3, 0, 0), "unsupported_or_audio_only_media"),
    ((math.inf, 40, 20), "unsupported_or_audio_only_media"),
    ((3, 5000, 5000), "source_pixel_limit"),
])
def test_decode_audio_and_source_pixel_limits(monkeypatch, setup, probe_result, reason):
    instance, fake = provider(monkeypatch)
    monkeypatch.setattr(video_frames, "probe", lambda path: probe_result)
    with pytest.raises(video_frames.FrameVisionError, match=reason):
        instance.see_video(Path("x.mp3"), "Observe", VideoObservation)
    assert not setup and not fake.calls


@pytest.mark.parametrize("change", ["missing", "failed", "model", "endpoint"])
def test_capability_requires_behavioral_receipt_bound_to_route(monkeypatch, setup, change):
    instance, fake = provider(monkeypatch)
    receipt = instance.options["vision_capability"]
    if change == "missing":
        instance.options.pop("vision_capability")
    elif change == "failed":
        receipt.passed = False
    elif change == "model":
        receipt.model = "another-model"
    else:
        monkeypatch.setenv("OLLAMA_BASE_URL", "https://alternate.invalid")
    with pytest.raises(video_frames.FrameVisionError, match="capability_unverified"):
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert not setup and not fake.calls


def test_repair_and_fallback_obey_shared_physical_budget(monkeypatch, setup):
    _, fake = provider(monkeypatch, [reply("bad"), reply("bad"), reply("{}")])
    chain = ModelChainProvider(model=f"{MODEL},ollama/deepseek-v4.1-flash")
    for tier in chain._tiers:
        tier.options["vision_capability"] = capability(tier)
    with attempt_budget(2) as budget, pytest.raises(AttemptBudgetExhausted):
        chain.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert budget.used == len(fake.calls) == 2
    assert chain.served is None
    assert all(attempt.role == "vision" for attempt in budget.attempts)


def test_fallback_serves_configured_model_only(monkeypatch, setup):
    _, fake = provider(monkeypatch, [RuntimeError("offline"), reply("{}")])
    chain = ModelChainProvider(model=f"{MODEL},ollama/deepseek-v4.1-flash")
    for tier in chain._tiers:
        tier.options["vision_capability"] = capability(tier)
    result = chain.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert result.visual_coverage.frames[0].status == "included"
    assert [call["model"] for call in fake.calls] == chain.order()
    assert chain.served.endswith("deepseek-v4.1-flash")


def test_prompt_secret_guard_precedes_media_processing(monkeypatch, setup):
    instance, fake = provider(monkeypatch, secrets=["private-passphrase"])
    with pytest.raises(video_frames.ProviderError, match="credential"):
        instance.see_video(Path("x.mp4"), "private-passphrase", VideoObservation)
    assert not setup and not fake.calls


@pytest.mark.parametrize("kind", ["missing", "empty", "jpeg", "oversized", "pixels"])
def test_invalid_extracted_payload_cannot_reach_transport(monkeypatch, setup, kind):
    instance, fake = provider(monkeypatch, frame_limits=FrameLimits(max_frames=1))

    def extract(path, timestamp, output):
        if kind == "empty":
            output.write_bytes(b"")
        elif kind == "jpeg":
            Image.new("RGB", (40, 20)).save(output, format="JPEG")
        elif kind == "oversized":
            Image.new("RGB", (40, 20)).save(output, format="PNG")
            instance.options["frame_limits"].max_frame_bytes = output.stat().st_size - 1
        elif kind == "pixels":
            Image.new("RGB", (41, 20)).save(output, format="PNG")
            instance.options["frame_limits"].max_pixels = 800
        return True

    monkeypatch.setattr(video_frames, "extract_frame", extract)
    with pytest.raises(video_frames.FrameVisionError, match="all_frames_withheld") as error:
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert error.value.coverage.frames[0].reason == "frame_validation_failed"
    assert fake.calls == []


def test_total_bytes_bound_preserves_partial_coverage(monkeypatch, setup):
    # Each sanitized image fits; the combined payload exceeds the independent batch cap.
    output = io.BytesIO()
    Image.new("RGB", (40, 20), "red").save(output, format="PNG")
    instance, fake = provider(monkeypatch, frame_limits=FrameLimits(
        max_frames=3, max_total_bytes=200))
    result = instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert [frame.status for frame in result.visual_coverage.frames] == [
        "included", "withheld", "withheld"]
    assert result.visual_coverage.frames[1].reason == "total_byte_limit"
    assert len([p for p in fake.calls[0]["messages"][0]["content"]
                if p["type"] == "image_url"]) == 1


def test_failed_frame_decode_is_explicitly_withheld(monkeypatch, setup):
    instance, fake = provider(monkeypatch, frame_limits=FrameLimits(max_frames=1))
    monkeypatch.setattr(video_frames, "extract_frame", lambda *args: False)
    with pytest.raises(video_frames.FrameVisionError) as error:
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert error.value.coverage.frames[0].reason == "frame_decode_failed"
    assert fake.calls == []


@pytest.mark.parametrize("values", [
    {"system_instruction": "custom"}, {"thinking_level": "low"},
    {"media_resolution": "low"}, {"max_output_tokens": 0}, {"temperature": float("inf")},
    {"max_output_tokens": 65537},
])
def test_unsupported_generation_controls_reject_explicitly(monkeypatch, setup, values):
    instance, fake = provider(monkeypatch)
    with pytest.raises(video_frames.FrameVisionError, match="unsupported_generation_options"):
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation, VisionOptions(**values))
    assert not setup and not fake.calls


def test_invalid_limit_shape_and_transport_failures_retain_evidence(monkeypatch, setup):
    instance, fake = provider(monkeypatch, [RuntimeError("offline")])
    instance.options["frame_limits"] = {}
    with pytest.raises(video_frames.FrameVisionError, match="invalid_frame_limits"):
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert not setup and not fake.calls
    instance.options["frame_limits"] = FrameLimits(max_frames=1)
    with pytest.raises(video_frames.ProviderError) as error:
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert error.value.coverage.frames[0].status == "included"
    assert error.value.coverage.text_unavailable


def test_chain_failure_retains_visual_shortfall(monkeypatch, setup):
    provider(monkeypatch)
    chain = ModelChainProvider(model=MODEL)
    with pytest.raises(video_frames.ProviderError) as error:
        chain.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert error.value.coverage.text_unavailable
    assert error.value.coverage.frames == []


def test_budget_refusal_preserves_inclusion_without_claiming_delivery(monkeypatch, setup):
    instance, fake = provider(monkeypatch, frame_limits=FrameLimits(max_frames=1))
    with attempt_budget(0) as budget, pytest.raises(AttemptBudgetExhausted) as error:
        instance.see_video(Path("x.mp4"), "Observe", VideoObservation)
    assert budget.used == 0 and fake.calls == []
    assert error.value.coverage.frames[0].status == "included"
    assert error.value.coverage.text_unavailable
