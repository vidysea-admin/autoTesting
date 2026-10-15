"""Finite frame-bound and capability receipt schemas reject invalid inputs."""

import pytest
from pydantic import ValidationError

from autotester.schema.video_frames import (
    FrameCoverage,
    FrameEvidence,
    FrameLimits,
    VisionCapability,
)


@pytest.mark.parametrize("field,lower,upper", [
    ("max_frames", 1, 64), ("max_pixels", 1, 16_000_000),
    ("max_frame_bytes", 1, 20_000_000), ("max_total_bytes", 1, 64_000_000),
])
def test_frame_limits_are_finite_bounded(field, lower, upper):
    for value in (lower - 1, upper + 1, float("inf")):
        with pytest.raises(ValidationError):
            FrameLimits(**{field: value})


def test_frame_evidence_rejects_invalid_index_time_and_status():
    for data in ({"index": -1}, {"timestamp_s": -1}, {"timestamp_s": float("inf")},
                 {"status": "unknown"}):
        with pytest.raises(ValidationError):
            FrameEvidence(**({"index": 0, "timestamp_s": 0, "status": "included"} | data))


def test_coverage_rejects_invalid_duration():
    for duration in (-1, float("inf")):
        with pytest.raises(ValidationError):
            FrameCoverage(duration_s=duration)


def test_capability_requires_hashes_and_rejects_unknown_fields():
    valid = {"model": "model", "passed": True, "endpoint_sha256": "a" * 64,
             "fixture_sha256": "b" * 64, "output_sha256": "c" * 64}
    for field in ("endpoint_sha256", "fixture_sha256", "output_sha256"):
        with pytest.raises(ValidationError):
            VisionCapability(**(valid | {field: "invalid"}))
    for model in (FrameCoverage, FrameEvidence, FrameLimits, VisionCapability):
        values = {"unexpected": 1}
        if model is FrameEvidence:
            values |= {"index": 0, "timestamp_s": 0, "status": "included"}
        elif model is VisionCapability:
            values |= valid
        with pytest.raises(ValidationError):
            model(**values)
