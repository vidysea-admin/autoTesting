"""Explicit dry-run plans and safe outcomes for exact legacy provider migration."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact
from autotester.schema.project import ProviderConfig


class ProviderMigrationEntry(BaseModel):
    """Only exact legacy candidates have a target; partial/custom entries remain untouched."""

    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    status: Literal["eligible", "custom", "partial", "invalid", "missing"]
    before_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    after_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    target: ProviderConfig | None = None


class ProviderMigrationPlan(Artifact):
    """Root-bound immutable snapshots; creating a plan performs no write."""

    root: str
    entries: list[ProviderMigrationEntry]


class ProviderMigrationOutcome(BaseModel):
    """Per-selected-project result; stale evidence cannot overwrite current configuration."""

    model_config = ConfigDict(extra="forbid")
    slug: str
    status: Literal["applied", "restored", "unchanged", "skipped", "stale"]
    reason: str
