"""Offline pixel-reading transport proves the behavioral probe, never a real model."""

import base64
import hashlib
import io
import json
import traceback
from contextlib import contextmanager

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from PIL import Image

from autotester.core import image_privacy
from autotester.providers import vision_probe
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.availability import AvailabilityFailure
from autotester.providers.base import ProviderError, load_skill_prompt
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.image_privacy import ImageSanitation
from autotester.schema.vision_probe import VisionProbeResult

pytestmark = pytest.mark.usefixtures("no_network")
MODEL = "ollama_chat/glm-5.3-flash"
OCR = ("level\tpage_num\tblock_num\tpar_num\tline_num\tconf\tleft\ttop\twidth\theight\ttext\n"
       "5\t1\t1\t1\t1\t99\t95\t125\t60\t22\tSAFE\n")
COLORS = {(220, 30, 30): "red", (30, 65, 220): "blue",
          (20, 150, 50): "green", (240, 210, 20): "yellow"}


def read_pixels(kwargs):
    urls = [part["image_url"]["url"] for part in kwargs["messages"][0]["content"]
            if part["type"] == "image_url"]
    assert len(urls) == 2
    readings, data = [], []
    for url in urls:
        assert url.startswith("data:image/png;base64,")
        payload = base64.b64decode(url.split(",")[1])
        data.append(payload)
        image = Image.open(io.BytesIO(payload))
        assert image.getpixel((5, 130)) == (0, 0, 0)  # full sanitized band, originally white
        reading = {}
        for side, x in (("left", 30), ("right", 160)):
            color = image.getpixel((x+30, 65))
            shape = ("square" if image.getpixel((x+5, 40)) == color else
                     "circle" if image.getpixel((x+5, 65)) == color else "triangle")
            reading[f"{side}_shape"], reading[f"{side}_color"] = shape, COLORS[color]
        readings.append(reading)
    return {"images": readings}, data


@pytest.fixture
def transport(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    fake = install(monkeypatch, [])
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-test-only")
    paths = []

    def ocr(path):
        paths.append(path)
        return OCR

    monkeypatch.setattr(image_privacy, "_local_ocr", ocr)
    captured = []

    def completion(**kwargs):
        fake.calls.append(kwargs)
        answer, data = read_pixels(kwargs)
        captured.append((answer, data))
        return reply(json.dumps(answer))

    fake.completion = completion
    return LiteLLMProvider(model=MODEL), fake, captured, paths


def test_probe_bootstraps_from_actual_sanitized_pixels_and_binds_receipt(transport):
    provider, fake, captured, paths = transport
    with attempt_budget(10) as outer:
        result = vision_probe.probe_vision(provider)
    assert result.status == "verified" and result.reason == "matched"
    assert "vision_capability" not in provider.options  # no prior receipt
    receipt = result.capability
    assert receipt.model == MODEL and receipt.passed
    route = json.dumps({"api_base": "https://ollama.com"}, sort_keys=True)
    assert receipt.endpoint_sha256 == hashlib.sha256(route.encode()).hexdigest()
    digest = hashlib.sha256()
    for data in captured[0][1]:
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    assert receipt.fixture_sha256 == digest.hexdigest()
    assert receipt.output_sha256 == hashlib.sha256(
        json.dumps(captured[0][0], separators=(",", ":")).encode()).hexdigest()
    assert receipt.probe_protocol == "sanitized-layout-pair-v1"
    assert receipt.prompt_sha256 == hashlib.sha256(
        load_skill_prompt("vision-probe").encode()).hexdigest()
    assert result.expected == result.observed
    assert VisionProbeResult.model_validate_json(result.model_dump_json()) == result
    assert len(fake.calls) == outer.used == len(result.attempts) == 1
    assert 0 < fake.calls[0]["timeout"] <= 45
    assert fake.calls[0]["num_retries"] == 0 and fake.calls[0]["temperature"] == 0
    assert not any(path.exists() for path in paths)
    outer.attempts[0].status = "failed"
    assert result.attempts[0].status == "succeeded"


def test_random_draws_are_independent_and_answers_are_not_in_prompt(monkeypatch, transport):
    provider, fake, captured, _ = transport
    calls = []

    class Draws:
        def sample(self, population, size):
            calls.append((population, size))
            return list(population)[:size] if len(calls) <= 2 else list(population)[-size:]

    monkeypatch.setattr(vision_probe.random, "SystemRandom", Draws)
    result = vision_probe.probe_vision(provider)
    assert result.status == "verified" and len(calls) == 4
    assert captured[0][1][0] != captured[0][1][1]
    assert result.expected.images[0] != result.expected.images[1]
    prompt = fake.calls[0]["messages"][0]["content"][0]["text"]
    assert result.expected.model_dump_json() not in prompt
    assert "neutral-0" not in prompt and "neutral-1" not in prompt


def test_visual_mismatch_is_inconclusive_never_a_capability(transport):
    provider, fake, _, _ = transport

    def wrong(**kwargs):
        fake.calls.append(kwargs)
        answer, _ = read_pixels(kwargs)
        answer["images"][0]["left_color"] = (
            "red" if answer["images"][0]["left_color"] != "red" else "blue")
        return reply(json.dumps(answer))

    fake.completion = wrong
    result = vision_probe.probe_vision(provider)
    assert result.status == "inconclusive" and result.reason == "visual_answer_mismatch"
    assert result.capability is None and len(result.attempts) == 1


@pytest.mark.parametrize("recovers", [True, False])
def test_one_json_repair_shares_the_probe_physical_budget(transport, recovers):
    provider, fake, _, _ = transport
    original = fake.completion

    def repaired(**kwargs):
        if len(fake.calls) == 1 and recovers:
            return original(**kwargs)
        fake.calls.append(kwargs)
        return reply("not JSON")

    fake.completion = repaired
    result = vision_probe.probe_vision(provider)
    assert len(fake.calls) == len(result.attempts) == 2
    assert (result.status == "verified") is recovers
    assert (result.capability is not None) is recovers


def test_sanitation_failure_withholds_every_request(monkeypatch, transport):
    provider, fake, _, _ = transport
    monkeypatch.setattr(image_privacy, "_local_ocr", lambda path: "")
    result = vision_probe.probe_vision(provider)
    assert result.reason == "image_preparation_or_sanitation_failed"
    assert result.status == "inconclusive" and result.capability is None
    assert fake.calls == [] and result.attempts == []


def test_enclosing_zero_budget_stops_before_transport(transport):
    provider, fake, _, _ = transport
    with attempt_budget(0), pytest.raises(AttemptBudgetExhausted) as error:
        vision_probe.probe_vision(provider)
    assert error.value.probe_result.reason == "budget_exhausted"
    assert error.value.probe_result.attempts == [] and fake.calls == []


def test_two_call_probe_cap_is_physical_and_raises_instead_of_falling_back(transport):
    provider, fake, _, _ = transport
    original = provider.judge

    def noisy(*args, **kwargs):
        for _ in range(3):
            answer = original(*args, **kwargs)
        return answer

    provider.judge = noisy
    with pytest.raises(AttemptBudgetExhausted) as error:
        vision_probe.probe_vision(provider)
    assert len(fake.calls) == len(error.value.probe_result.attempts) == 2
    assert error.value.probe_result.capability is None


def test_sdk_errors_are_safe_and_only_availability_is_unavailable(transport):
    provider, fake, _, _ = transport
    for exception, expected in [(ProviderError("private-user@example.test"), "inconclusive"),
                                (AvailabilityFailure("service"), "unavailable")]:
        def failed(*args, exc=exception, **kwargs):
            raise exc
        provider.judge = failed
        result = vision_probe.probe_vision(provider)
        assert result.status == expected and result.capability is None
        assert "private-user" not in result.model_dump_json()
    assert fake.calls == []


def test_receipt_requires_physical_success_and_stable_route(monkeypatch, transport):
    provider, fake, _captured, _ = transport
    original = fake.completion

    def rerouted(**kwargs):
        response = original(**kwargs)
        monkeypatch.setenv("OLLAMA_BASE_URL", "https://changed.invalid")
        return response

    fake.completion = rerouted
    result = vision_probe.probe_vision(provider)
    assert result.reason == "endpoint_or_model_changed" and result.capability is None
    fake.completion = original
    provider.judge = lambda *args, **kwargs: result.expected
    result = vision_probe.probe_vision(provider)
    assert result.reason == "physical_transport_unproven" and result.capability is None


def test_another_models_physical_attempt_cannot_certify_this_model(transport):
    provider, fake, _, _ = transport
    other = LiteLLMProvider(model="ollama_chat/another-model")
    provider.judge = other.judge
    result = vision_probe.probe_vision(provider)
    assert len(fake.calls) == 1 and fake.calls[0]["model"] == "ollama_chat/another-model"
    assert result.reason == "physical_transport_unproven" and result.capability is None
    assert result.attempts[0].provider == "litellm:ollama_chat/another-model"


def test_unavailable_or_non_explicit_provider_cannot_start_probe(transport):
    provider, fake, _, _ = transport
    provider.available = lambda: False
    result = vision_probe.probe_vision(provider)
    assert result.status == "unavailable" and result.expected is None
    assert fake.calls == []
    with pytest.raises(ProviderError, match="explicit LiteLLM"):
        vision_probe.probe_vision(object())


def test_secret_model_config_is_withheld_before_artifact_or_transport(transport):
    _, fake, _, _ = transport
    secret = "synthetic-secret-model-value"
    provider = LiteLLMProvider(model=secret, secrets=[secret])
    with pytest.raises(ProviderError, match="configuration withheld") as error:
        vision_probe.probe_vision(provider)
    assert secret not in "".join(traceback.format_exception(error.value))
    assert fake.calls == []


@pytest.mark.parametrize("kind", ["missing", "empty", "jpeg", "dimensions", "oversized"])
def test_invalid_sanitized_payload_cannot_become_filename_only_success(
        monkeypatch, transport, tmp_path, kind):
    provider, fake, _, _ = transport
    path = tmp_path / "invalid.png"
    if kind == "empty":
        path.write_bytes(b"")
    elif kind == "jpeg":
        Image.new("RGB", (256, 160)).save(path, format="JPEG")
    elif kind == "dimensions":
        Image.new("RGB", (257, 160)).save(path, format="PNG")
    elif kind == "oversized":
        Image.new("RGB", (256, 160)).save(path, format="PNG")
        path.write_bytes(path.read_bytes() + b"x" * 100_000)

    @contextmanager
    def invalid(paths, *, mask_limit=None):
        yield ImageSanitation(requested=1, paths=[path])

    monkeypatch.setattr(vision_probe, "sanitized_images", invalid)
    result = vision_probe.probe_vision(provider)
    assert result.status == "inconclusive" and result.capability is None
    assert result.reason == "image_preparation_or_sanitation_failed"
    assert fake.calls == []
