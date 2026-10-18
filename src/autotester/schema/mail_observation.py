"""What a read-only mailbox look returns, and the rule that keeps token values out of it (MP17).

One job: the shapes of one IMAP read -- `MailQuery` (the bounds: since-time, recipient, message cap,
timeout), `MailObservation` (one message as the oracle may remember it), `MailReadResult` (the read
or the honest reason it could not happen) -- plus `mask_credential_tokens`, the single place that
decides whether text holds a credential-shaped token (numeric code, mixed token, URL-embedded
token). A message is remembered by its scrubbed subject, its time and WHICH token kinds it held and
how many; a body is never a field here, and a token's value never leaves `mask_credential_tokens`
(it hands back the text with each value replaced by `TOKEN_MASK`). The reader is
`sources/imap_mailbox.py`; the oracle is `stages/oracle_mailbox.py`.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.mailbox_ref import SecretKey

MAX_MESSAGES_HARD = 50
RECIPIENT_PATTERN = r"^[^\s\"\\()<>\x00-\x1f]{3,254}$"
TOKEN_MASK = "[credential-token]"


class CredentialTokenKind(StrEnum):
    """The shapes of secret a mail body can carry (recorded as present, never as a value)."""

    NUMERIC_CODE = "numeric_code"
    MIXED_TOKEN = "mixed_token"
    URL_TOKEN = "url_token"


class MailReadState(StrEnum):
    """`unavailable` is never "no message arrived": an absence is evidence only after a read."""

    READ = "read"
    UNAVAILABLE = "unavailable"


class MailUnavailableReason(StrEnum):
    """Why a read did not happen. Closed, so no server text or host can ride along."""

    KEY_MISSING = "key_missing"
    KEY_UNDECLARED = "key_undeclared"
    UNREACHABLE = "unreachable"
    LOGIN_REFUSED = "login_refused"
    FOLDER_REFUSED = "folder_refused"
    PROTOCOL_ERROR = "protocol_error"


class MailQuery(BaseModel):
    """The bounds of one read (SA9): since-time, recipient, message cap, timeout."""

    model_config = ConfigDict(extra="forbid")

    since: datetime
    recipient: str = Field(pattern=RECIPIENT_PATTERN)
    max_messages: int = Field(default=20, ge=1, le=MAX_MESSAGES_HARD, strict=True)
    timeout_s: float = Field(default=10.0, ge=1.0, le=60.0)

    @field_validator("since")
    @classmethod
    def _aware(cls, since: datetime) -> datetime:
        if since.tzinfo is None:
            raise ValueError("since must carry a timezone")
        return since


class MailObservation(BaseModel):
    """One message: scrubbed subject, time, and which credential-shaped tokens it held."""

    model_config = ConfigDict(extra="forbid")

    uid: int = Field(ge=1)
    subject: str = Field(max_length=200)
    received_at: datetime | None = None
    readable: bool = True
    credential_token_kinds: list[CredentialTokenKind] = Field(default_factory=list)
    credential_token_count: int = Field(default=0, ge=0)


class MailReadResult(BaseModel):
    """A completed read, or `unavailable` with a closed reason (and key NAMES when missing)."""

    model_config = ConfigDict(extra="forbid")

    state: MailReadState
    reason: MailUnavailableReason | None = None
    missing_keys: list[SecretKey] = Field(default_factory=list)
    messages: list[MailObservation] = Field(default_factory=list)
    matched_on_server: int = Field(default=0, ge=0)
    capped: bool = False
    command_log: list[str] = Field(default_factory=list, description="verbs sent, in order")

    @model_validator(mode="after")
    def _state_agrees_with_content(self) -> MailReadResult:
        if self.state is MailReadState.READ and self.reason is not None:
            raise ValueError("a completed read has no unavailable reason")
        if self.state is MailReadState.UNAVAILABLE and (self.reason is None or self.messages):
            raise ValueError("an unavailable read needs a reason and carries no messages")
        return self


_CUE = r"(?:pass(?:word|code|phrase)?|pwd|token|secret|code|otp|pin|key)"
_CUE_NUMERIC = r"(?:code|otp|pin|passcode|password|verification|one[- ]time)"
_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
_URL_QUERY = re.compile(
    r"(?i)([?&](?:token|key|code|otp|reset|auth|sig|signature|pass(?:word)?|pwd|secret|session|"
    r"ticket)=)([^&\s#]{6,})")
_URL_PATH = re.compile(
    r"(?<=/)(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{20,}(?=[/?#\s]|$)")
_MIXED_CUED = re.compile(
    rf"(?i)\b{_CUE}\b(?:\s+(?:is|was|are))?\s*[:=]?\s+(?P<tok>[^\s\"'<>,;]{{6,64}})"
    rf"|\b{_CUE}\b\s*[:=]\s*(?P<tok2>[^\s\"'<>,;]{{6,64}})")
_MIXED_LONG = re.compile(r"\b(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{20,}\b")
_NUMERIC = re.compile(
    rf"(?i)\b{_CUE_NUMERIC}\b[^\n\d]{{0,40}}?(?<![\w.])(?P<num>\d{{4,10}})(?![\w@]|\.\d)")


def _classes(token: str) -> int:
    return sum(bool(re.search(p, token)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))


def _mask_url(match: re.Match[str], hits: list[int]) -> str:
    url = match.group(0)
    url, n_query = _URL_QUERY.subn(lambda m: m.group(1) + TOKEN_MASK, url)
    url, n_path = _URL_PATH.subn(TOKEN_MASK, url)
    hits.append(n_query + n_path)
    return url


def _mask_mixed(match: re.Match[str], hits: list[int]) -> str:
    tok = (match.group("tok") or match.group("tok2")).rstrip(".,;:!?)")
    if TOKEN_MASK in tok or tok.isdigit() or _classes(tok) < 2 or not re.search(r"[\d\W_]", tok):
        return match.group(0)            # digits alone are the numeric rule's business
    hits.append(1)
    return match.group(0).replace(tok, TOKEN_MASK)


def mask_credential_tokens(text: str) -> tuple[str, list[CredentialTokenKind], int]:
    """`text` with every credential-shaped token value replaced; the kinds seen; the count.

    Order matters: URLs first (a token inside a link is a URL token), then cued mixed tokens and
    long standalone ones, then cued numeric codes. The value is only ever in the argument and the
    local match; the return carries kinds and a count."""
    kinds: dict[CredentialTokenKind, int] = {}
    steps = (
        (CredentialTokenKind.URL_TOKEN, lambda t, h: _URL.sub(lambda m: _mask_url(m, h), t)),
        (CredentialTokenKind.MIXED_TOKEN,
         lambda t, h: _MIXED_CUED.sub(lambda m: _mask_mixed(m, h), t)),
        (CredentialTokenKind.MIXED_TOKEN, lambda t, h: _MIXED_LONG.sub(
            lambda m: (h.append(1), TOKEN_MASK)[1], t)),
        (CredentialTokenKind.NUMERIC_CODE, lambda t, h: _NUMERIC.sub(
            lambda m: (h.append(1), m.group(0).replace(m.group("num"), TOKEN_MASK))[1], t)),
    )
    for kind, step in steps:
        hits: list[int] = []
        text = step(text, hits)
        if sum(hits):
            kinds[kind] = kinds.get(kind, 0) + sum(hits)
    return text, sorted(kinds, key=lambda k: k.value), sum(kinds.values())
