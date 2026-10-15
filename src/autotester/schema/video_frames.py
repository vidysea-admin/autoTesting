"""Bounded frame sampling and value-free visual coverage for provider transport."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FrameLimits(BaseModel):
    """Finite host decode and outbound-payload limits, independent of model tags."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    max_frames: int = Field(default=16, ge=1, le=64)
    max_pixels: int = Field(default=4_000_000, ge=1, le=16_000_000)
    max_frame_bytes: int = Field(default=2_000_000, ge=1, le=20_000_000)
    max_total_bytes: int = Field(default=16_000_000, ge=1, le=64_000_000)


class FrameEvidence(BaseModel):
    """Payload inclusion, not delivery/understanding; retains original index/time."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    index: int = Field(ge=0)
    timestamp_s: float = Field(ge=0)
    status: Literal["included", "withheld"]
    reason: str | None = None


class FrameCoverage(BaseModel):
    """Sparse layout-only evidence cannot establish readable text or narration."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    duration_s: float = Field(default=0, ge=0)
    sampling_limited: bool = False
    text_unavailable: bool = True
    audio_unavailable: bool = True
    frames: list[FrameEvidence] = Field(default_factory=list)


class VisionCapability(BaseModel):
    """Model-bound behavioral probe receipt; model metadata is never evidence."""

    model_config = ConfigDict(extra="forbid")
    model: str
    endpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    passed: bool
