"""Structured Gemini audio transcription response; no product decisions."""

from pydantic import BaseModel, ConfigDict, Field


class GeminiSegment(BaseModel):
    """One utterance with source-relative seconds."""

    model_config = ConfigDict(extra="forbid")
    start: float
    end: float
    text: str


class GeminiTranscription(BaseModel):
    """Only verbatim audio segments, never product assertions."""

    model_config = ConfigDict(extra="forbid")
    segments: list[GeminiSegment] = Field(default_factory=list)


class AudioTransportCapability(BaseModel):
    """Transport safety earned by independently checked provider implementation."""

    model_config = ConfigDict(extra="forbid")
    shared_deadline: bool = False
    physical_attempt_accounting: bool = False
    audio_only: bool = False
