"""What happened to one declared PlatformLink when a run tried to follow it (MP12).

One job: `LinkOutcome` -- the typed per-link result (followed, failed with a reason, or not
reached) plus the `MultiRoleFinding` a hop outside every declared platform becomes. Defined here,
not in `schema/multi_role_enums.py`, because that file is T-207's alone (MPI3): a later unit that
needs a new enum defines it in its own schema file. Holds hosts and reasons only: no URL with a
query, no credential, no page content.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.multi_role_enums import LinkKind
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.platform import PLATFORM_ID_PATTERN


class LinkStatus(StrEnum):
    """Every declared link ends in exactly one of these; none is silently dropped (MP12)."""

    FOLLOWED = "followed"
    FAILED = "failed"
    NOT_REACHED = "not_reached"


class LinkOutcome(BaseModel):
    """The report row for `Project.platform_links[link_index]`."""

    model_config = ConfigDict(extra="forbid")

    link_index: int = Field(ge=0, strict=True)
    from_platform: str = Field(pattern=PLATFORM_ID_PATTERN)
    to_platform: str = Field(pattern=PLATFORM_ID_PATTERN)
    kind: LinkKind
    status: LinkStatus
    reason: str | None = Field(default=None, max_length=300)
    account_id: str | None = Field(default=None, description="the role account that drove it")
    landed_host: str | None = Field(
        default=None, description="host[:port] the browser ended on, or the stray host it was "
                                  "stopped at; never a full URL")
    hops: list[str] = Field(default_factory=list, description="hosts visited, in order")
    finding: MultiRoleFinding | None = None

    @model_validator(mode="after")
    def _status_decides_the_rest(self) -> LinkOutcome:
        if self.status is LinkStatus.FOLLOWED:
            if self.reason or self.finding:
                raise ValueError("a followed link has no failure reason and no finding")
        elif not self.reason:
            raise ValueError("a link that was not followed must say why")
        if self.finding is not None and self.status is not LinkStatus.FAILED:
            raise ValueError("only a failed link carries a finding")
        return self
