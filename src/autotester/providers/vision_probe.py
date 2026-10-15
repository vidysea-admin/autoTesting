"""Verify one explicit LiteLLM model using bounded neutral sanitized image challenges."""

from __future__ import annotations

import hashlib
import io
import random
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from autotester.core.image_privacy import sanitized_images
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.availability import AvailabilityFailure
from autotester.providers.base import ProviderError, load_skill_prompt
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.video_frames import endpoint_fingerprint
from autotester.schema.video_frames import VisionCapability
from autotester.schema.vision_probe import VisionProbeResult, VisualProbeAnswer, VisualProbeReading

PROTOCOL = "sanitized-layout-pair-v1"
_COLORS = {"red": (220, 30, 30), "blue": (30, 65, 220),
           "green": (20, 150, 50), "yellow": (240, 210, 20)}
_SHAPES = ("circle", "square", "triangle")
_SIZE = (256, 160)


def _draw_challenge(path: Path, reading: VisualProbeReading) -> None:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", _SIZE, "white")
    draw = ImageDraw.Draw(image)
    for side, left in (("left", 30), ("right", 160)):
        shape, color = getattr(reading, f"{side}_shape"), getattr(reading, f"{side}_color")
        box = (left, 35, left+60, 95)
        if shape == "triangle":
            draw.polygon([(left+30, 35), (left, 95), (left+60, 95)], fill=_COLORS[color])
        else:
            method = draw.ellipse if shape == "circle" else draw.rectangle
            method(box, fill=_COLORS[color])
    # A neutral OCR anchor below the shapes lets fail-closed sanitation mask text.
    draw.text((95, 125), "SAFE", font=ImageFont.load_default(size=22), fill="black")
    image.save(path, format="PNG")


def _new_challenges(directory: Path) -> tuple[list[Path], VisualProbeAnswer]:
    rng, readings, paths = random.SystemRandom(), [], []
    for index in range(2):
        shapes, colors = rng.sample(_SHAPES, 2), rng.sample(tuple(_COLORS), 2)
        reading = VisualProbeReading(left_shape=shapes[0], right_shape=shapes[1],
                                     left_color=colors[0], right_color=colors[1])
        path = directory / f"neutral-{index}.png"
        _draw_challenge(path, reading)
        paths.append(path)
        readings.append(reading)
    return paths, VisualProbeAnswer(images=readings)


def _validated_bytes(path: Path) -> bytes:
    from PIL import Image

    if not path.is_file() or not 0 < path.stat().st_size <= 100_000:
        raise ValueError("invalid_probe_image")
    data = path.read_bytes()
    with Image.open(io.BytesIO(data)) as image:
        if image.format != "PNG" or image.size != _SIZE:
            raise ValueError("invalid_probe_image")
        image.load()
    return data


def _safe_challenges(paths: list[Path], stack: ExitStack) -> tuple[list[Path], str]:
    safe_paths, digest = [], hashlib.sha256()
    for path in paths:
        batch = stack.enter_context(sanitized_images([path]))
        if len(batch.paths) != 1 or batch.withheld:
            raise ValueError("image_sanitation_withheld")
        data = _validated_bytes(batch.paths[0])
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
        safe_paths.append(batch.paths[0])
    return safe_paths, digest.hexdigest()


def _evaluate(provider, result, expected, observed, fixture_hash, prompt_hash, budget):
    result.observed = observed
    label = f"{provider.id}:{result.model}"
    if (provider._model != result.model
            or endpoint_fingerprint(provider) != result.endpoint_sha256):
        result.reason = "endpoint_or_model_changed"
    elif (not budget.attempts or budget.attempts[-1].status != "succeeded"
          or any(attempt.provider != label for attempt in budget.attempts)):
        result.reason = "physical_transport_unproven"
    elif observed != expected:
        result.reason = "visual_answer_mismatch"
    else:
        result.capability = VisionCapability(
            model=result.model, endpoint_sha256=result.endpoint_sha256,
            fixture_sha256=fixture_hash,
            output_sha256=hashlib.sha256(observed.model_dump_json().encode()).hexdigest(),
            passed=True, probe_protocol=PROTOCOL, prompt_sha256=prompt_hash)
        result.status, result.reason = "verified", "matched"


def _require_probe_provider(provider: LiteLLMProvider) -> None:
    if not isinstance(provider, LiteLLMProvider):
        raise ProviderError("vision probe requires one explicit LiteLLM provider")
    try:
        provider.guard_text(provider._model)
    except ProviderError:
        raise ProviderError("vision probe model configuration withheld") from None


def probe_vision(provider: LiteLLMProvider) -> VisionProbeResult:
    """No prior receipt needed: guarded judge bootstraps only the neutral-layout capability.

    One explicit model, two randomized images, at most two physical requests/45 seconds
    across JSON repair. Enclosing budgets remain authoritative. This function selects
    no fallback, records no raw provider errors, and never reads user media or audio.
    """
    _require_probe_provider(provider)
    result = VisionProbeResult(model=provider._model,
                               endpoint_sha256=endpoint_fingerprint(provider))
    if not provider.available():
        result.status, result.reason = "unavailable", "provider_unavailable"
        return result
    prompt = load_skill_prompt("vision-probe")
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    with attempt_budget(2, wall_clock_s=45) as budget:
        try:
            with TemporaryDirectory(prefix="autotester-vision-probe-") as temporary, \
                    ExitStack() as stack:
                paths, result.expected = _new_challenges(Path(temporary))
                safe, fixture_hash = _safe_challenges(paths, stack)
                observed = provider.judge(prompt, VisualProbeAnswer, images=safe,
                                          prompt_file="vision-probe", fed_id=PROTOCOL)
                _evaluate(provider, result, result.expected, observed,
                          fixture_hash, prompt_hash, budget)
        except AttemptBudgetExhausted as exc:
            result.reason = "budget_exhausted"
            exc.probe_result = result
            raise
        except AvailabilityFailure:
            result.status, result.reason = "unavailable", "provider_unavailable"
        except ProviderError:
            result.reason = "provider_error"
        except (OSError, ValueError):
            result.reason = "image_preparation_or_sanitation_failed"
        finally:
            result.attempts = [attempt.model_copy(deep=True) for attempt in budget.attempts]
    return result
