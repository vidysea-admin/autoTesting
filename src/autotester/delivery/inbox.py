"""Delivery records on disk and the send-once procedure around a mail transport (TT9, HO29).

One job: remember what was attempted, never send one message twice, never let a mail failure
escape. Records and attempt markers are files created once and never rewritten (a temp file is
hard-linked into place, so a half-written record is never visible and a second writer loses).
The directory is passed in by the caller; nothing here knows where `.work/` is.

Crash rule (brief item 3, chosen here, not yet in the contract): an attempt is claimed with a
marker BEFORE the transport is called. A marker with no record means the process died between
"sent" and "recorded", or is still running; the message may have left, so it is never resent.
Once the marker is older than `STALE_AFTER` it is closed as one terminal `failed` record.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from autotester.delivery.email import MailTransport, TransportError
from autotester.schema.delivery import (
    SAFE_KEY,
    DeliveryChannel,
    DeliveryRecord,
    DeliveryStatus,
    Recipient,
    RenderedMessage,
    safe_id,
)
from autotester.store.filestore import exists_path, list_children, read_json
from autotester.store.filestore_paths import create_exclusive_path, read_text_path

RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1   # the first try plus one retry per delay
STALE_AFTER = timedelta(minutes=10)
ERROR_LIMIT = 300


def retry_delay(attempts_made: int) -> timedelta | None:
    """How long to wait after the Nth failed attempt; None once the bound is reached. Pure."""
    if attempts_made < 1:
        raise ValueError("attempts_made starts at 1")
    return RETRY_DELAYS[attempts_made - 1] if attempts_made <= len(RETRY_DELAYS) else None


def next_retry_at(now: datetime, attempts_made: int) -> datetime | None:
    delay = retry_delay(attempts_made)
    return None if delay is None else now + delay


def _encode_part(value: str) -> str:
    """Make an id unambiguous inside a key and safe on a case-insensitive file system.

    Lower-case letters, digits, `.` and `-` stand for themselves; an upper-case letter becomes
    `_` + its lower-case letter, a raw `_` becomes `_0`. So `_` is always followed by a letter or
    digit, the encoded part never contains `__` (the separator) and never ends with `_`, and two
    different ids never encode to the same text, even when file names ignore case.
    """
    return "".join("_0" if c == "_" else f"_{c.lower()}" if c.isupper() else c
                   for c in safe_id(value))


def delivery_key(run_id: str, channel: DeliveryChannel, user_id: str) -> str:
    """The idempotency key `<channel>__<run>__<user>`: one per run, channel and recipient.

    Injective: the parts are encoded so `__` occurs only as the separator, and the channel is a
    fixed lower-case word. Safe as a file-name part and starts with a letter.
    """
    key = f"{channel.value}__{_encode_part(run_id)}__{_encode_part(user_id)}"
    if not SAFE_KEY.fullmatch(key):
        raise ValueError("delivery key too long")
    return key


_PART = r"(?:[a-z0-9.-]|_[a-z0-9])+"
_CHANNELS = "|".join(re.escape(c.value) for c in DeliveryChannel)


class DeliveryLog:
    """Append-only records under `<root>/records` and attempt claims under `<root>/attempts`."""

    def __init__(self, root: Path) -> None:
        self.records_dir, self.attempts_dir = root / "records", root / "attempts"

    def append(self, key: str, record: DeliveryRecord) -> None:
        path = self.records_dir / f"{key}.{record.attempts:02d}.json"
        if not create_exclusive_path(path, record.model_dump_json()):
            raise FileExistsError("a record for this attempt already exists")

    def claim(self, key: str, attempt: int, now: datetime) -> bool:
        return create_exclusive_path(self.attempts_dir / f"{key}.{attempt:02d}.json",
                                     json.dumps({"started_at": now.isoformat()}))

    def claimed_at(self, key: str, attempt: int) -> datetime | None:
        path = self.attempts_dir / f"{key}.{attempt:02d}.json"
        try:
            return datetime.fromisoformat(json.loads(read_text_path(path) or "")["started_at"])
        except (OSError, ValueError, KeyError):
            return None

    def _load(self, name: re.Pattern[str]) -> list[DeliveryRecord]:
        """Records whose WHOLE file name matches `name` (never a prefix or a glob), by name."""
        if not exists_path(self.records_dir):
            return []
        records = (read_json(self.records_dir / n, DeliveryRecord)
                   for n in list_children(self.records_dir) if name.fullmatch(n))
        return [r for r in records if r is not None]

    def records_for_key(self, key: str) -> list[DeliveryRecord]:
        return self._load(re.compile(re.escape(key) + r"\.\d+\.json"))

    def records_for_run(self, run_id: str) -> list[DeliveryRecord]:
        """Every attempt for one run, in file-name order (channel, then user, then attempt):
        what the run page shows (TT9)."""
        return self._load(re.compile(
            "(?:" + _CHANNELS + ")__" + re.escape(_encode_part(run_id)) + "__" + _PART
            + r"\.\d+\.json"))

    def latest(self, key: str) -> DeliveryRecord | None:
        records = self.records_for_key(key)
        return records[-1] if records else None


def _failed(run_id: str, channel: DeliveryChannel, user_id: str, attempt: int, error: str,
            retry_at: datetime | None) -> DeliveryRecord:
    return DeliveryRecord(run_id=run_id, channel=channel, recipient_user_id=user_id,
                          status=DeliveryStatus.FAILED, error=error, attempts=attempt,
                          next_retry_at=retry_at)


def _settled(records: list[DeliveryRecord], now: datetime, max_attempts: int
             ) -> DeliveryRecord | None:
    """The record to return unchanged when nothing should be attempted now, else None."""
    for rec in records:
        if rec.status is not DeliveryStatus.FAILED:
            return rec                      # already sent or outboxed: done for good
    last = records[-1] if records else None
    if last and (last.attempts >= max_attempts or last.next_retry_at is None
                 or last.next_retry_at > now):
        return last                         # out of attempts, or not due yet
    return None


def deliver_once(log: DeliveryLog, transport: MailTransport, to: Recipient,
                 message: RenderedMessage, *, run_id: str, now: datetime,
                 scrub: Callable[[str], str], channel: DeliveryChannel = DeliveryChannel.EMAIL,
                 max_attempts: int = MAX_ATTEMPTS) -> DeliveryRecord | None:
    """Make at most one attempt for this (run, channel, recipient) if one is due.

    Returns the record describing the current state, or None when another worker holds the
    attempt. A transport failure of any kind becomes a `failed` record and never propagates
    (HO29). A failure to WRITE the record does propagate: the caller's hook contains it.
    """
    key = delivery_key(run_id, channel, to.user_id)
    records = log.records_for_key(key)
    if (settled := _settled(records, now, max_attempts)) is not None:
        return settled
    attempt = len(records) + 1
    if not log.claim(key, attempt, now):
        return _close_stale(log, key, run_id, channel, to.user_id, attempt, now)
    try:
        transport.send(to, message, key=key)
    except Exception as exc:
        text = str(exc) if isinstance(exc, TransportError) else type(exc).__name__
        error = scrub(text)[:ERROR_LIMIT]
        record = _failed(run_id, channel, to.user_id, attempt, error,
                         next_retry_at(now, attempt) if attempt < max_attempts else None)
    else:
        record = DeliveryRecord(run_id=run_id, channel=channel, recipient_user_id=to.user_id,
                                status=transport.outcome, attempts=attempt)
    try:
        log.append(key, record)
    except FileExistsError:
        # A second worker (skewed clock) closed this live attempt as "outcome unknown" while we
        # were sending. Records are never rewritten, so that record stands; it is truthful.
        return log.latest(key)
    return record


def _close_stale(log: DeliveryLog, key: str, run_id: str, channel: DeliveryChannel,
                 user_id: str, attempt: int, now: datetime) -> DeliveryRecord | None:
    started = log.claimed_at(key, attempt)
    if started is not None and now - started < STALE_AFTER:
        return None                         # still running elsewhere: wait for its record
    record = _failed(run_id, channel, user_id, attempt,
                     "outcome unknown: the attempt started but was never recorded, so the message "
                     "may or may not have been sent; not resent", None)
    try:
        log.append(key, record)
    except FileExistsError:
        return log.latest(key)              # the other worker finished while we looked
    return record
