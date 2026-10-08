"""Typed optional external tracker binding; this seam performs no external operation."""

from pydantic import BaseModel, ConfigDict


class TrackerBinding(BaseModel):
    """A supplied sheet location, awaiting the later mapping and confirmation unit."""

    model_config = ConfigDict(extra="forbid")

    sheet_url: str
