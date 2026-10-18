"""What a data-leak finding may remember about another tenant's data (MP9, MPI1).

One job: `LeakEvidence` -- a count of foreign rows, field names (headers, never values), at most
five HMAC-SHA256 hashed ids, a masked-screenshot path and a URL template with ids replaced by
placeholders. Nothing here can hold a name, email, phone or raw id: every free-text field is
checked for a personal shape and for id-like path segments, so a caller that passes a value by
mistake fails validation instead of reaching disk. The hashing and masking live in
`stages/leak_evidence.py`; this module only refuses the wrong shapes.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_HASHED_IDS = 5
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)")
ROUTE_WORDS = frozenset({
    "about", "account", "accounts", "admin", "api", "application", "applications",
    "assessment", "assessments", "auth", "career", "careers", "class", "classes",
    "counsellor", "counsellors", "course", "courses", "dashboard", "detail", "details",
    "document", "documents", "download", "edit", "forgot-password", "grade", "grades",
    "help", "home", "index", "list", "log-in", "login", "logout", "message", "messages",
    "new", "notification", "notifications", "order", "orders", "parent", "parents",
    "payment", "payments", "profile", "program", "programs", "register", "report",
    "reports", "reset-password", "result", "results", "school", "schools", "search",
    "settings", "sign-in", "sign-up", "signin", "signout", "signup", "student", "students",
    "task", "tasks", "teacher", "teachers", "test", "tests", "university", "universities",
    "upload", "uploads", "user", "users", "v1", "v2", "v3", "view",
    # ordinary route words other units use (fix6c-r4-routeword; AT-1033 tracks the per-project list)
    "cart", "fast", "inbox", "item", "items", "mail", "me", "quiz", "quizzes", "slow", "status",
})
_PLACEHOLDER = re.compile(r"^\{[a-z_]+\}$")
HashedId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def contains_personal_shape(text: str) -> bool:
    """True when `text` looks like an email address or a phone number."""
    return bool(_EMAIL.search(text) or _PHONE.search(text))


def segment_is_id_like(segment: str) -> bool:
    """True for every path segment that is not a `{placeholder}` or a closed-list route word.

    The closed `ROUTE_WORDS` list is the only way a literal segment survives, so digits, letters
    mixed with digits, 20+ character runs, `%`/`@` values and unknown words (nanoid, base62, cuid2,
    ULID, ObjectId, UUID, `cus_...`, name slugs) all become `{id}` in one predicate.
    """
    return bool(segment) and not _PLACEHOLDER.match(segment) and segment.lower() not in ROUTE_WORDS


def validate_url_template(url: str) -> str:
    """Accept only a URL whose ids and query values are placeholders; raise ValueError otherwise."""
    if len(url) > 500 or "#" in url or "@" in url or any(c.isspace() for c in url):
        raise ValueError("url_template must be a placeholder template without fragment or userinfo")
    parts = urlsplit(url)
    if parts.scheme not in ("", "http", "https"):
        raise ValueError("url_template scheme must be http, https or none")
    if any(segment_is_id_like(seg) for seg in parts.path.split("/")):
        raise ValueError("url_template path holds an id-like segment; use {id}")
    for pair in filter(None, parts.query.split("&")):
        _, has_value, value = pair.partition("=")
        if has_value and not _PLACEHOLDER.match(value):
            raise ValueError("url_template query values must be {placeholders}")
    if contains_personal_shape(url):
        raise ValueError("url_template looks like personal data")
    return url


class LeakEvidence(BaseModel):
    """Counts, headers, keyed hashes and a template: enough to reproduce, nothing to identify."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    foreign_row_count: int = Field(ge=0, strict=True)
    field_names: list[Annotated[str, StringConstraints(min_length=1, max_length=64)]] = Field(
        max_length=100, description="column headers of the leaked rows, never cell values")
    hashed_ids: list[HashedId] = Field(
        default_factory=list, max_length=MAX_HASHED_IDS,
        description="HMAC-SHA256 under a per-project key; at most five")
    ids_withheld_reason: Literal["key_missing"] | None = None
    screenshot_path: str | None = Field(
        default=None, pattern=r"^[A-Za-z0-9_][A-Za-z0-9_./-]*\.png$",
        description="masked screenshot, relative to the run directory")
    screenshot_withheld_reason: str | None = Field(default=None, pattern=r"^[a-z_]{1,64}$")
    url_template: str

    @model_validator(mode="after")
    def _no_value_shaped_text(self) -> LeakEvidence:
        for name in self.field_names:
            if contains_personal_shape(name) or "\n" in name:
                raise ValueError("a field name looks like personal data; store headers only")
        validate_url_template(self.url_template)
        if self.screenshot_path and ".." in self.screenshot_path:
            raise ValueError("screenshot_path must stay inside the run directory")
        if self.hashed_ids and self.ids_withheld_reason:
            raise ValueError("ids are either hashed or withheld, not both")
        if self.screenshot_path and self.screenshot_withheld_reason:
            raise ValueError("a screenshot is either stored or withheld, not both")
        return self
