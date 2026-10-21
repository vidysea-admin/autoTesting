"""Typed, value-free evidence of image sanitation before external model delivery."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MASK_LIMIT = 0.75
"""Fraction of an image the cumulative text mask may cover before it is withheld (AT-1384)."""
CEILING_MASK_LIMIT = 0.9
"""No project may raise its limit past this: above it the guard stops withholding anything."""


class ImageSanitation(BaseModel):
    """A temporary sanitized batch; reasons never contain OCR text or filenames."""

    model_config = ConfigDict(extra="forbid")

    paths: list[Path] = Field(default_factory=list)
    requested: int = Field(ge=0)
    withheld: int = Field(default=0, ge=0)
    reasons: list[str] = Field(default_factory=list)
    text_unavailable: bool = True

    @property
    def incomplete(self) -> bool:
        return self.withheld > 0
