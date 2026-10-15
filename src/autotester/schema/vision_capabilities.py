"""Persisted actual neutral-probe results used by the visual-role policy."""
from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact
from autotester.schema.vision_probe import VisionProbeResult


class VisionCapabilityEvidence(BaseModel):
    """A verified result and the immutable actual execution receipt it came from."""

    model_config = ConfigDict(extra="forbid")
    source_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: VisionProbeResult


class VisionCapabilitySet(Artifact):
    """Exact live results; an offline tag or model name is not capability evidence."""

    model_config = ConfigDict(extra="forbid")
    records: list[VisionCapabilityEvidence] = Field(min_length=1, max_length=4)
