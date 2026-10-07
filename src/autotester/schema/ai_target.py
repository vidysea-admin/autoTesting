"""Typed evidence and bounded read scope for deterministic AI target discovery."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.approval import RunApproval
from autotester.schema.base import Artifact
from autotester.schema.project import Source


class AiSignalKind(StrEnum):
    """Observed lexical facts; never runtime claims or check selection."""

    SDK = "sdk"
    AGENT_FRAMEWORK = "agent_framework"
    RETRIEVAL = "retrieval"
    TOOL = "tool"
    ORCHESTRATION = "orchestration"
    PROMPT = "prompt"
    GROUND_TRUTH = "ground_truth"
    CONTEXT = "context"
    ENDPOINT = "endpoint"


class AiTargetKind(StrEnum):
    """The four positive target kinds specified by the approved T-151 plan."""

    CONVERSATIONAL = "conversational"
    AGENTIC = "agentic"
    ORCHESTRATION = "orchestration"
    HYBRID = "hybrid"


class Classification(BaseModel):
    """Strict naming response; evidence and checks are never model-controlled."""

    model_config = ConfigDict(extra="forbid")
    system_kind: AiTargetKind
    reason: str = Field(min_length=1, max_length=1000, pattern=r"\S", strict=True)
    confidence: float = Field(ge=0, le=1, strict=True, allow_inf_nan=False)


class AiTarget(Artifact):
    """Source evidence plus classification, or an explicit non-AI outcome."""

    root_path: str
    context_paths: list[str] = Field(default_factory=list)
    endpoint: str | None = None
    system_kind: AiTargetKind | None = None
    signals: list[Signal] = Field(default_factory=list)
    has_ground_truth: bool = False
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str
    not_ai_target: bool = False


class Signal(BaseModel):
    """One observed lexical fact, never a claim about runtime behavior."""

    model_config = ConfigDict(extra="forbid")
    kind: AiSignalKind
    evidence_path: str
    line: int = Field(ge=1)
    detail: str


class ScanLimits(BaseModel):
    """Explicit finite limits on scanning and metadata parsing."""

    model_config = ConfigDict(extra="forbid")
    max_files: int = Field(default=500, ge=1, le=10000)
    max_entries: int = Field(default=2000, ge=1, le=10000)
    max_file_bytes: int = Field(default=262144, ge=1, le=1048576)
    max_total_bytes: int = Field(default=4194304, ge=1, le=16777216)
    max_tree_depth: int = Field(default=12, ge=1, le=50)
    wall_clock_s: float = Field(default=10, gt=0, le=300)
    max_yaml_depth: int = Field(default=8, ge=1, le=20)
    max_yaml_nodes: int = Field(default=500, ge=1, le=2000)
    max_signals: int = Field(default=2000, ge=1, le=20000)


class ReadScope(BaseModel):
    """Caller-supplied project identity and approvals; no ambient credential loading."""

    model_config = ConfigDict(extra="forbid")
    project: str
    project_root: str
    approvals: list[RunApproval] = Field(default_factory=list)
    limits: ScanLimits = Field(default_factory=ScanLimits)


class ReadRefusal(BaseModel):
    """Why an input was not read, keeping incompleteness explicit."""

    model_config = ConfigDict(extra="forbid")
    evidence_path: str
    reason: str


class ContextDocument(BaseModel):
    """Markdown metadata and an unpersisted Source reference, never body text."""

    model_config = ConfigDict(extra="forbid")
    evidence_path: str
    frontmatter: dict[str, object] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    source: Source


class Discovery(Artifact):
    """Read-only discovery receipt; classification is a separate pending operation."""

    signals: list[Signal] = Field(default_factory=list)
    documents: list[ContextDocument] = Field(default_factory=list)
    refusals: list[ReadRefusal] = Field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.refusals
