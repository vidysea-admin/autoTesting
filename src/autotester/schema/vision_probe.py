"""Closed-vocabulary behavioral vision answers and value-free verification receipts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact
from autotester.schema.provider_attempt import ProviderAttempt
from autotester.schema.video_frames import VisionCapability


class VisualProbeReading(BaseModel):
    """Only neutral geometry/colors can appear in a challenge answer."""

    model_config = ConfigDict(extra="forbid")
    left_shape: Literal["circle", "square", "triangle"]
    left_color: Literal["red", "blue", "green", "yellow"]
    right_shape: Literal["circle", "square", "triangle"]
    right_color: Literal["red", "blue", "green", "yellow"]


class VisualProbeAnswer(BaseModel):
    """Read both images in payload order; filenames and text contain no answers."""

    model_config = ConfigDict(extra="forbid")
    images: list[VisualProbeReading] = Field(min_length=2, max_length=2)


class VisionProbeResult(Artifact):
    """A probe result asserts only this sampled layout protocol, never general quality."""

    model: str
    endpoint_sha256: str
    status: Literal["verified", "unavailable", "inconclusive"] = "inconclusive"
    reason: str = "not_completed"
    expected: VisualProbeAnswer | None = None
    observed: VisualProbeAnswer | None = None
    capability: VisionCapability | None = None
    attempts: list[ProviderAttempt] = Field(default_factory=list)
