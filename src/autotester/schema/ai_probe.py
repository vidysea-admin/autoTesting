"""Track C adversarial shapes: a file-defined probe set, the record of one pass, a refusal row.

Contract: qa/contracts/adversarial.md AD4-AD7 (D-017, D-018). Facts only: a `ProbeRun` holds what
was sent and what came back, never a verdict (C7), and a `ProbeRefusal` holds that a request was
refused and why, never what the request said (C5).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.ai_check import AiExchange
from autotester.schema.base import Artifact


class ProbeSet(BaseModel):
    """One probe file under `prompts/probes/`: a category name and its probe texts (AD4)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="the file stem, e.g. `instruction_override`")
    description: str = ""
    probes: list[str] = Field(default_factory=list)


class ProbeRecord(BaseModel):
    """One probe sent and what was observed of the answer, tagged with the set it came from."""

    model_config = ConfigDict(extra="forbid")

    probe_set: str
    exchange: AiExchange


class ProbeRun(Artifact):
    """A completed bounded pass against one endpoint: observation, never judgement (AD5)."""

    run_id: str
    project: str
    endpoint: str
    production: bool = Field(description="named explicitly by the caller, never inferred (AD3)")
    probe_sets: list[str] = Field(default_factory=list)
    approval_id: str
    planned_probes: int = Field(ge=0)
    approved_probes: int = Field(ge=0, description="the approval's own `max_probes`")
    ceiling: int = Field(gt=0, description="the code's absolute probe ceiling at run time (AD6)")
    cap_hit: bool = Field(
        default=False, description="a bound (the wall clock) stopped the run before every "
                                   "planned probe was sent")
    unsent_probes: int = Field(default=0, ge=0)
    records: list[ProbeRecord] = Field(default_factory=list)


class ProbeRefusal(BaseModel):
    """One line of `refusals.jsonl` (AD7). Carries no probe content, by construction."""

    model_config = ConfigDict(extra="forbid")

    target: str
    timestamp: str
    requested_probes: int = Field(ge=0)
    reason: str
