"""Explicit input-only plans and receipts for isolated two-mode acceptance baselines."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from autotester.schema.base import Artifact


class BaselineInput(BaseModel):
    """An owner-approved input file; its bytes are bound before preparation."""

    model_config = ConfigDict(extra="forbid")
    path: str
    sha256: str
    kind: Literal["video", "doc"]
    approval_ref: str


class BaselinePlan(Artifact):
    """A declared build and frozen source configuration, with no credential values."""

    source_slug: str
    source_config_sha256: str
    baseline_slug: str
    target_build: str
    credential_keys: list[str]
    teaching_inputs: list[BaselineInput]


class BaselineReceipt(Artifact):
    """Local preparation evidence; build identity is declared, never remotely verified."""

    plan_sha256: str
    source_config_sha256: str
    target_build: str
    target_build_verified: Literal[False] = False
    teaching_slug: str
    url_only_slug: str
    teaching_source_ids: list[str]
    credential_keys: list[str]
    next_steps: list[str]
