"""Page-level evidence from bounded, local document extraction."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact


class DocumentPage(BaseModel):
    """One physical PDF page, including unreadable pages instead of omissions."""

    model_config = ConfigDict(extra="forbid")
    number: int = Field(ge=1)
    text: str = ""
    method: Literal["text", "ocr", "unreadable"]
    confidence: float | None = Field(default=None, ge=0, le=100)
    error: str | None = None


class DocumentReading(Artifact):
    """A local extraction receipt; errors mean the document is not fully learned."""

    source_id: str | None = None
    pages: list[DocumentPage] = Field(default_factory=list)
    error: str | None = None


class PdfLimits(BaseModel):
    """Resource limits shared by the extraction supervisor and its worker."""

    model_config = ConfigDict(extra="forbid")
    max_bytes: int = Field(default=50_000_000, ge=1, le=200_000_000)
    max_pages: int = Field(default=100, ge=1, le=1000)
    max_chars: int = Field(default=500_000, ge=1, le=2_000_000)
    timeout_s: float = Field(default=120, gt=0, le=600)
    page_timeout_s: float = Field(default=15, gt=0, le=60)
    image_side: int = Field(default=2000, ge=256, le=4000)
    min_confidence: float = Field(default=70, ge=0, le=100)
