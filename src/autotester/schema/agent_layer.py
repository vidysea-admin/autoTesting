"""The shapes the lead tester's tool surface speaks (T-179, D-042): which tools exist,
what a model may pass each, and how a refusal is named.

A model supplies IDS and bounds only (`CrawlArgs`, `RunCaseArgs`, ...). The project, the
browser session, the judge provider and the approvals are the trusted context
(`agents/context.py`) and have no field here, so a prompt cannot choose or widen them.
Every args model forbids unknown fields: an invented parameter fails before any action.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AgentToolName(StrEnum):
    """The stage tools in this slice. `report` and `capture_network` join with the rest of T-179."""

    CRAWL = "crawl"
    RUN_CASE = "run_case"
    GET_PERSONA = "get_persona"
    GET_CATALOG = "get_catalog"
    GRADE_CASE = "grade_case"


class ToolEffect(StrEnum):
    """What a tool can do to the outside world. T-180 allowlists subagents by this."""

    READ = "read"
    ACTING = "acting"
    GRADING = "grading"


class RefusalClass(StrEnum):
    """Why a tool call produced no action. A refusal is a result, never an exception the
    model can talk its way past (AL3)."""

    UNKNOWN_TOOL = "unknown_tool"
    BAD_ARGUMENTS = "bad_arguments"
    SECRET = "secret"
    APPROVAL = "approval"
    WRITE_POLICY = "write_policy"
    NOTHING_TO_DO = "nothing_to_do"


class ToolSpec(BaseModel):
    """One tool: its name, effect, and the existing function it wraps (C3)."""

    model_config = ConfigDict(extra="forbid")

    name: AgentToolName
    effect: ToolEffect
    wraps: str = Field(description="dotted path of the existing stage function the body calls")
    description: str


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CrawlArgs(_Args):
    """Bounds the model REQUESTS; the approval decides whether they are granted."""

    max_actions: int | None = Field(default=None, ge=1)
    wall_clock_s: float | None = Field(default=None, gt=0)
    incremental: bool = False


class RunCaseArgs(_Args):
    case_id: str = Field(min_length=1, max_length=200)


class GradeCaseArgs(_Args):
    case_id: str = Field(min_length=1, max_length=200)


class EmptyArgs(_Args):
    """Tools that take nothing (`get_persona`, `get_catalog`): everything is trusted context."""


class ToolOutcome(BaseModel):
    """What a tool call returns to the model. `summary` is scrubbed before it is built, and the
    whole outcome passes the secret gate again before it leaves the tool (AL6)."""

    model_config = ConfigDict(extra="forbid")

    tool: str
    ok: bool
    refusal: RefusalClass | None = None
    summary: str = ""
    artifact_ref: str | None = Field(
        default=None, description="typed id of what the stage produced, e.g. `result:<case_id>`"
    )
