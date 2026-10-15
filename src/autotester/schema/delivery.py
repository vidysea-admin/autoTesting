"""Report-delivery shapes: preference, recipient, summary, rendered message, record, SMTP settings.

One job: the closed vocabularies and strict models for delivering a finished run's report
(qa/contracts/team-test-button.md TT7-TT9, hosting.md HO26-HO29). Nothing here holds a secret
value (core-invariants C5): `SmtpConfig` has no password field, the password is read at send time.
Every free-text field is single-line and free of paths, so a header cannot be injected and a
filesystem location cannot ride along in a message. `ReportLabel` is the stored vocabulary only;
the one function that computes it is not in this module.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.base import Artifact
from autotester.schema.run_queue import QueueStatus

SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
SAFE_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}")
_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]{1,64}@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)"
                      r"+[A-Za-z]{2,63}")
_PATH = re.compile(r"(?:^|[\s(\"'=])(?:[A-Za-z]:[\\/]|\\\\|/[A-Za-z0-9_.~-]+/)")
_URL = re.compile(r"(?:https?://[A-Za-z0-9.-]+(?::(\d{1,5}))?)?/(?!/)[A-Za-z0-9._~/-]*")
LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


class DeliveryChannel(StrEnum):
    INBOX = "inbox"
    EMAIL = "email"


class DeliveryStatus(StrEnum):
    SENT = "sent"
    OUTBOXED = "outboxed"  # dry-run adapter: written to the outbox, nothing sent
    FAILED = "failed"


class ReportLabel(StrEnum):
    """The stored report label. Computed once elsewhere (TT7); every reader takes it as given."""

    GREEN = "green"
    FAILED = "failed"
    BLOCKED = "blocked"
    INCONCLUSIVE = "inconclusive"
    LOW_COVERAGE = "low coverage"


def safe_id(value: str) -> str:
    """A run id or user id that is safe as a file-name part: no separator, no `..`, bounded."""
    if not SAFE_ID.fullmatch(value) or ".." in value:
        raise ValueError("not a safe identifier")
    return value


def single_line(value: str, *, limit: int = 200) -> str:
    """Printable, one line, no filesystem path: fit for a header or a body line."""
    if not value.strip() or len(value) > limit:
        raise ValueError("empty or too long")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("control characters (including line breaks) are not allowed")
    if _PATH.search(value):
        raise ValueError("a filesystem path may not appear in a message")
    return value


class NotificationPref(Artifact):
    """Per-user opt-in (HO26). Default OFF: no mail until the user ticks the box."""

    user_id: str
    email_run_reports: bool = False
    account_generation: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$", repr=False)

    check_user_id = field_validator("user_id")(safe_id)


class Recipient(BaseModel):
    """Who a message goes to. Built from the authenticated identity, never from a request body.
    The address is personal data: it is used to send and is never stored in a record."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    address: str

    check_user_id = field_validator("user_id")(safe_id)

    @field_validator("address")
    @classmethod
    def _address(cls, v: str) -> str:
        if len(v) > 254 or not _ADDRESS.fullmatch(v):
            raise ValueError("not a single plain e-mail address")
        return v


class RunCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    blocked: int = Field(ge=0)
    inconclusive: int = Field(ge=0)


class ReportSummary(BaseModel):
    """Exactly what HO28 lets a message carry: names, counts, one coverage line, a link."""

    model_config = ConfigDict(extra="forbid")

    project_name: str
    run_id: str
    finished_at: datetime
    counts: RunCounts
    coverage_line: str
    label: ReportLabel
    report_url: str = Field(description="absolute http(s) or site-relative; no query, no fragment")

    check_run_id = field_validator("run_id")(safe_id)
    check_lines = field_validator("project_name", "coverage_line")(single_line)

    @field_validator("finished_at")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("a timezone-aware time is required")
        return v

    @field_validator("report_url")
    @classmethod
    def _url(cls, v: str) -> str:
        match = _URL.fullmatch(v) if len(v) <= 2048 else None
        if match is None:   # `(?!/)` refuses `//host/...`, which a mail client resolves elsewhere
            raise ValueError("a plain link to the report (no query, fragment or credentials)")
        if match.group(1) is not None and not 1 <= int(match.group(1)) <= 65535:
            raise ValueError("the port is out of range")
        return v


class RenderedMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    body: str

    @field_validator("subject")
    @classmethod
    def _subject(cls, v: str) -> str:
        if not v.strip() or any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("a subject is one line")
        return v


class DeliveryRecord(Artifact):
    """One attempt's outcome (TT9). Stores the user id, a redacted error, never the address."""

    run_id: str
    channel: DeliveryChannel
    recipient_user_id: str
    status: DeliveryStatus
    error: str | None = Field(None, description="redacted; None unless status is failed")
    attempts: int = Field(ge=1)
    next_retry_at: datetime | None = None

    check_ids = field_validator("run_id", "recipient_user_id")(safe_id)


class InboxEntry(BaseModel):
    """One row of the website inbox (TT7): a request the viewer may read the report of.
    Built from the queue entry and the run's verdicts on every read; nothing is stored."""

    model_config = ConfigDict(extra="forbid")

    project: str
    run_id: str
    status: QueueStatus
    at: datetime
    started_by: str | None = Field(None, description="who pressed Test; None for a schedule")
    scheduled: bool = False
    label: ReportLabel | None = Field(None, description="None while queued or running")
    position: int = Field(0, ge=0, description="1-based place in the line while queued")
    link: str

    check_run_id = field_validator("run_id")(safe_id)


class SmtpConfig(BaseModel):
    """Transport settings from the environment. No password: that is read at send time (C5)."""

    model_config = ConfigDict(extra="forbid")

    host: str
    port: int = Field(ge=1, le=65535)
    user: str | None = Field(None, repr=False)
    sender_address: str
    sender_name: str | None = None
    tls: Literal["starttls", "ssl", "none"] = "starttls"

    @field_validator("host")
    @classmethod
    def _host(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9.:-]{1,253}", v):
            raise ValueError("not a host name")
        return v

    @field_validator("sender_address")
    @classmethod
    def _from(cls, v: str) -> str:
        if not _ADDRESS.fullmatch(v):
            raise ValueError("not a single plain e-mail address")
        return v

    @field_validator("sender_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return v if v is None else single_line(v, limit=100)

    @model_validator(mode="after")
    def _no_plaintext_credentials(self) -> SmtpConfig:
        if self.tls == "none" and self.user and self.host not in LOOPBACK:
            raise ValueError("credentials are never sent without TLS to a non-loopback host")
        return self
