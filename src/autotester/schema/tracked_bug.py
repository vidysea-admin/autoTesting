"""A tracked bug and the events that move it: the data shapes of T-199a (team-bug-loop TB1-TB6).

Its one job is the shapes. A `TrackedBug` is never stored: the only stored thing is the append-only
`BugEvent` log, and the bug is the fold of that log (`stages/bug_loop.py`). So history cannot be
rewritten, and a status can only ever come from an event the lifecycle table allowed (R44).

`bug_key` is stable by construction (TB1): `content_id("bug", {project, case_id, criterion_id})`
for a case failure, the `Issue.id` fingerprint for a video-found issue. A seed whose key does not
match its own parts is refused here, so no caller can slip a run id, time or path into a key.

`BugStatus` lives here, not in `schema/enums.py`, which sits at the 300-line cap.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.core.ids import content_id
from autotester.schema.enums import Severity

DEFAULT_CLOSE_PASSES = 2
"""N consecutive evidenced PASS verdicts that close a bug (the plan gate's assumption, TB2)."""

SYSTEM_ACTOR = "system:bug-loop"
"""The one actor that may move a status; every other actor is a named user (R44). The actor is an
unauthenticated string here: the T-204 route must set it from the session, never from a request."""

_ACTOR_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.:@/+-]{0,79}")
_VIDEO_KEY_RE = re.compile(r"iss_[0-9a-f]{12}")


class BugStatus(StrEnum):
    OPEN = "open"
    FIXED = "fixed"
    REOPENED = "reopened"
    STALE = "stale"


class EventKind(StrEnum):
    """What happened, in the loop's vocabulary. The first seven are verdict-derived; `case_changed`
    says the check the bug rests on is gone; `assign` is the one human-made event."""

    FAIL = "fail"
    PASS = "pass"
    PASS_UNEVIDENCED = "pass_unevidenced"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"
    NO_VERDICT = "no_verdict"
    CASE_CHANGED = "case_changed"
    ASSIGN = "assign"


def case_bug_key(project: str, case_id: str, criterion_id: str) -> str:
    """The key of a case-failure bug. A secret planted in case text cannot reach it: `case_id` is
    itself a content hash and `criterion_id` is a short rubric id."""
    return content_id("bug", {"project": project, "case_id": case_id, "criterion_id": criterion_id})


def _no_control(value: str, what: str) -> str:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{what} must not contain control characters")
    return value


class BugSeed(BaseModel):
    """What a bug is made of when its first FAIL opens it."""

    model_config = ConfigDict(extra="forbid")

    bug_key: str
    project: str = Field(min_length=1)
    case_id: str | None = Field(default=None, description="None for a video-found bug")
    criterion_id: str | None = None
    criterion_fp: str = Field(default="", description="fingerprint of the criterion at opening")
    title: str = Field(min_length=1, max_length=200)
    screen: str | None = None
    severity: Severity = Severity.S2

    @model_validator(mode="after")
    def _key_matches_parts(self) -> BugSeed:
        if self.case_id is not None:
            if not self.criterion_id:
                raise ValueError("a case-failure bug needs a criterion_id")
            if self.bug_key != case_bug_key(self.project, self.case_id, self.criterion_id):
                raise ValueError("bug_key must be case_bug_key(project, case_id, criterion_id)")
        elif not _VIDEO_KEY_RE.fullmatch(self.bug_key):
            raise ValueError("a video-found bug's key must be the Issue.id fingerprint")
        return self


class BugEvent(BaseModel):
    """One fact appended to the log. `ref` is the idempotency token: a verdict ref (`run/case`), an
    issue ref, or a caller-chosen request id. An event is identified by `(bug_key, ref)` alone, so
    the same ref applied twice, even as a different kind, is counted once."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    event_id: str = ""
    bug_key: str = Field(min_length=1)
    kind: EventKind
    ref: str = Field(min_length=1, max_length=200)
    at: datetime
    actor: str
    run_id: str | None = None
    seed: BugSeed | None = None
    assignee: str | None = Field(default=None, max_length=120)

    @field_validator("actor")
    @classmethod
    def _actor(cls, value: str) -> str:
        if not _ACTOR_RE.fullmatch(value):
            raise ValueError("actor must be 1-80 chars of letters, digits and _ . : @ / + - space")
        return value

    @field_validator("ref", "assignee")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        return None if value is None else _no_control(value, "ref/assignee")

    @field_validator("at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("an event time must carry a timezone")
        return value

    @model_validator(mode="after")
    def _shape(self) -> BugEvent:
        if self.seed is not None and (self.kind is not EventKind.FAIL
                                      or self.seed.bug_key != self.bug_key):
            raise ValueError("only a FAIL event carries a seed, and it must be for this bug_key")
        if self.assignee is not None and self.kind is not EventKind.ASSIGN:
            raise ValueError("only an ASSIGN event carries an assignee")
        if self.kind is EventKind.PASS and not self.run_id:
            raise ValueError("a PASS event must name the run that closes toward `fixed` (TB4)")
        derived = content_id("bev", {"bug_key": self.bug_key, "ref": self.ref})
        if self.event_id and self.event_id != derived:
            raise ValueError("event_id must be derived from (bug_key, ref)")
        self.event_id = derived
        return self


class TrackedBug(BaseModel):
    """One bug, as folded from its events. Never written to disk."""

    model_config = ConfigDict(extra="forbid")

    bug_key: str
    project: str
    case_id: str | None = None
    criterion_id: str | None = None
    criterion_fp: str = ""
    title: str
    screen: str | None = None
    severity: Severity = Severity.S2
    status: BugStatus = BugStatus.OPEN
    count: int = Field(default=1, ge=1, description="FAIL events seen")
    first_seen: datetime
    last_seen: datetime
    assignee: str | None = None
    evidence_run_id: str | None = Field(default=None, description="run of the latest FAIL")
    pass_streak: int = Field(default=0, ge=0, description="consecutive evidenced PASSes")
    streak_runs: list[str] = Field(default_factory=list)
    streak_refs: list[str] = Field(default_factory=list)
    closed_by_runs: list[str] = Field(default_factory=list)
    closed_by_verdicts: list[str] = Field(default_factory=list)
