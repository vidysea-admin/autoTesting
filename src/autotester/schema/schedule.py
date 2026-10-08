"""Typed project schedule configuration; execution belongs to the later scheduler unit."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from autotester.schema.team_enums import ScheduleMode


class ScheduleConfig(BaseModel):
    """Minimal persisted schedule seam, UTC and IST only (D-078)."""

    model_config = ConfigDict(extra="forbid")

    mode: ScheduleMode = ScheduleMode.MANUAL
    timezone: Literal["UTC", "IST"] = "UTC"
