"""Closed neutral answers and optional capability extensions remain strictly validated."""

import pytest
from pydantic import ValidationError

from autotester.schema.video_frames import VisionCapability
from autotester.schema.vision_probe import VisionProbeResult, VisualProbeAnswer, VisualProbeReading

READING = {"left_shape": "circle", "left_color": "red",
           "right_shape": "triangle", "right_color": "blue"}


@pytest.mark.parametrize("field", READING)
def test_neutral_answer_vocabulary_is_closed(field):
    with pytest.raises(ValidationError):
        VisualProbeReading(**(READING | {field: "private-content"}))


def test_exactly_two_images_and_no_extra_fields():
    for count in (0, 1, 3):
        with pytest.raises(ValidationError):
            VisualProbeAnswer(images=[READING] * count)
    with pytest.raises(ValidationError):
        VisualProbeReading(**(READING | {"unexpected": 1}))
    with pytest.raises(ValidationError):
        VisualProbeAnswer(images=[READING] * 2, unexpected=1)


def test_probe_status_is_explicit_and_capability_extension_is_backward_compatible():
    with pytest.raises(ValidationError):
        VisionProbeResult(model="model", endpoint_sha256="a" * 64, status="guess")
    old = {"model": "model", "endpoint_sha256": "a" * 64, "fixture_sha256": "b" * 64,
           "output_sha256": "c" * 64, "passed": True}
    assert VisionCapability(**old).prompt_sha256 is None
    assert VisionCapability(**old).probe_protocol is None
    for values in ({"probe_protocol": "unverified-tag"}, {"prompt_sha256": "invalid"}):
        with pytest.raises(ValidationError):
            VisionCapability(**(old | values))
