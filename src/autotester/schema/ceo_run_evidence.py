"""The evidence one CEO-benchmark acceptance run leaves behind (MP31, build leg).

One job: the shape of the run record `stages/ceo_run_evidence.py` checks -- each role account's
login outcome on its platform, the platforms the project declares, the id of the signed
RunApproval the run ran under, whether the browser was headed, and the per-oracle table. It holds
ids and outcomes only: no credential value, username, page or finding.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.oracle_context import OracleStatus
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN


class RoleLogin(BaseModel):
    """One role account's login outcome on one platform."""

    model_config = ConfigDict(extra="forbid")

    role_account_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    outcome: Literal["ok", "failed", "skipped"]


class CeoRunEvidence(BaseModel):
    """What the run recorded. The check, not this model, decides whether it is complete."""

    model_config = ConfigDict(extra="forbid")

    project_slug: str = Field(min_length=1, max_length=64)
    started_at: datetime
    headed: bool
    run_approval_id: str = Field(min_length=1)
    declared_platform_ids: list[str]
    logins: list[RoleLogin]
    oracle_table: list[OracleStatus]

    @model_validator(mode="after")
    def _aware(self) -> CeoRunEvidence:
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must carry a timezone")
        return self
