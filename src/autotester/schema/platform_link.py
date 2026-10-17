"""A declared hop from one platform to another (MP1).

One job: `PlatformLink` -- which platform hands the user to which, how (`LinkKind`), what triggers
the hop, where it must land and whether the session survives it. That both ends name a declared
platform is checked by `Project`, which owns the platform list.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.multi_role_enums import LinkKind
from autotester.schema.platform import PLATFORM_ID_PATTERN

HOST_PATTERN = r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?(:\d{1,5})?$"


class PlatformLink(BaseModel):
    """`from_platform` -> `to_platform`, reached through `url_template` or `control_name`."""

    model_config = ConfigDict(extra="forbid")

    from_platform: str = Field(pattern=PLATFORM_ID_PATTERN)
    to_platform: str = Field(pattern=PLATFORM_ID_PATTERN)
    kind: LinkKind
    url_template: str | None = Field(default=None, min_length=1)
    control_name: str | None = Field(default=None, min_length=1)
    expected_landing_host: str = Field(
        pattern=HOST_PATTERN, description="bare host[:port]; a hop landing elsewhere is a finding")
    carries_session: bool = Field(default=False, strict=True)

    @field_validator("expected_landing_host")
    @classmethod
    def _lower_host(cls, host: str) -> str:
        return host.lower()

    @model_validator(mode="after")
    def _needs_a_trigger(self) -> PlatformLink:
        if self.url_template is None and self.control_name is None:
            raise ValueError("a link needs a trigger: url_template or control_name")
        return self
