"""Immutable teaching inputs, materialization and per-source resumable receipts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.core.ids import content_id
from autotester.schema.base import Artifact
from autotester.schema.document import DocumentReading
from autotester.schema.enums import SourceKind
from autotester.schema.flowspec import FlowSpec
from autotester.schema.media import Transcript
from autotester.schema.teaching import TeachingUnit


class TeachingInput(BaseModel):
    """One registered input's source and actual evidence identity, without raw content."""

    model_config = ConfigDict(extra="forbid")
    source_id: str
    kind: SourceKind
    fingerprint: str
    content_fingerprint: str


class TeachingMaterial(BaseModel):
    """Resolved content held in memory; snapshot persistence stores only its identity."""

    model_config = ConfigDict(extra="forbid")
    identity: TeachingInput
    units: list[TeachingUnit] = Field(default_factory=list)
    transcript: Transcript | None = None
    problems: list[str] = Field(default_factory=list)
    children: list[str] = Field(default_factory=list)
    unavailable: bool = False
    document: DocumentReading | None = None


class TeachingSnapshot(Artifact):
    """The fixed registered input set for exactly one teaching run."""

    project: str
    run_id: str
    inputs: list[TeachingInput]

    @property
    def fingerprint(self) -> str:
        return content_id("teachset", [item.model_dump(mode="json") for item in self.inputs])


class TeachingOutcome(Artifact):
    """One durable source outcome; running means the model may have been called."""

    source_id: str
    input_fingerprint: str
    status: Literal["running", "learned", "partial", "failed", "duplicate", "container", "declared"]
    proposal: FlowSpec | None = None
    problems: list[str] = Field(default_factory=list)
    duplicate_of: str | None = None
    document: DocumentReading | None = None


class TeachingResult(Artifact):
    """The aggregate proposal and explicit completeness of every registered input."""

    project: str
    run_id: str
    snapshot_fingerprint: str
    outcomes: list[TeachingOutcome]
    proposal: FlowSpec

    @property
    def is_complete(self) -> bool:
        return bool(self.outcomes) and all(
            item.status not in {"failed", "partial", "running"} and not item.problems
            for item in self.outcomes
        )
