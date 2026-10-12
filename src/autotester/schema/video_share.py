"""The shapes of the video portal (T-198b / G9, team-intake.md TP1-TP6).

One job: the records the share, request-access and comment flows store, and the limits that
bound them. A share link's token is never a field here: only its hash is stored, so a copy of
the store cannot open a video. Every model is `extra="forbid"`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.team_enums import AccessRequestStatus

TOKEN_BYTES = 32
"""Entropy of a share-link token from `secrets`: 256 bits, over the 128-bit floor (TP3)."""
MAX_TOKEN_CHARS = 128
"""A longer path value is not one of our tokens and is not even looked up (TP3: oversized)."""
MIN_COMMENT_CHARS, MAX_COMMENT_CHARS = 1, 2000
"""A comment is 1 to 2000 characters after trim (TP2)."""


class Share(BaseModel):
    """One person who may open one video (the video's `shared_with` entry)."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    video_id: str
    email: str
    granted_by: str
    granted_at: datetime


class ShareLink(BaseModel):
    """A video's share link. Opening it grants nothing by itself (TP3); the token is not here."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    video_id: str
    created_by: str
    created_at: datetime
    revoked_at: datetime | None = None


class AccessRequest(BaseModel):
    """A signed-in person without access asking for it (TP5). One pending per person+video."""

    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    video_id: str
    requester: str = Field(description="the requester's email, from the session")
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    created_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None


class VideoComment(BaseModel):
    """A comment at a second of the recording (TP2). `pointer_line` is set by TP6 promotion."""

    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    video_id: str
    author: str = Field(description="the author's email, from the session")
    at_s: float = Field(ge=0)
    text: str
    created_at: datetime
    edited_at: datetime | None = None
    pointer_line: str | None = Field(
        default=None, description="the pointer line this comment was promoted to (TP6), once")
