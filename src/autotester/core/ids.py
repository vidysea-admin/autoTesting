"""Identifier generation. The ONLY place ids are minted.

Also the ONLY place a `RunApproval` is signed or verified (AT-110) — the HMAC
below is keyed from `AUTOTESTER_APPROVAL_KEY` in the repo-root `.env` and
shares its canonical-JSON encoding with `content_hash` rather than
re-deriving it, so there is exactly one definition of "how a payload is
turned into bytes" in this module.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_HASH_LEN = 12

APPROVAL_KEY_ENV = "AUTOTESTER_APPROVAL_KEY"
"""The repo-root `.env` key that signs/verifies a `RunApproval` (AT-110).
Read directly from `os.environ` — the same convention every other
system-level credential (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, ...) already
uses — after `core.env.load_repo_env()` has populated it. Never resolved
through `browser.secrets.SecretStore`: that class scopes a value to the
browser hosts a project declares, and this key is never typed into a page."""


class SigningKeyMissing(RuntimeError):
    """`AUTOTESTER_APPROVAL_KEY` is not set. Raised by `sign_payload` and
    `verify_payload` alike — signing and verifying fail CLOSED on a missing
    key, never silently succeeding and never silently accepting."""


def _canonical_json(payload: Any) -> str:
    """The one serialisation both `content_hash` and the HMAC sign over — key
    order normalised so logically identical payloads always encode the same
    way, whether they are being hashed or signed."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _signing_key() -> bytes:
    key = os.environ.get(APPROVAL_KEY_ENV)
    if not key:
        raise SigningKeyMissing(
            f"{APPROVAL_KEY_ENV} is not set — add a real value to the repo-root "
            ".env before granting or verifying a signed approval (see .env.example)"
        )
    return key.encode("utf-8")


def sign_payload(payload: Any) -> str:
    """HMAC-SHA256 hex digest of `payload`'s canonical JSON, keyed by
    `AUTOTESTER_APPROVAL_KEY`. Raises `SigningKeyMissing` if the key is not
    configured — there is no implicit/default key to fall back on."""
    return hmac.new(_signing_key(), _canonical_json(payload).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def verify_payload(payload: Any, signature: str) -> bool:
    """Constant-time check that `signature` is `payload`'s HMAC under the
    configured key. Raises `SigningKeyMissing` if the key is not configured —
    a caller must never read a missing key as "nothing to verify against, so
    accept". An empty `signature` simply fails (once a key is confirmed to
    exist), so a legacy/unsigned row reads as unverifiable, not as a
    configuration error."""
    expected = sign_payload(payload)
    if not signature:
        return False
    return hmac.compare_digest(expected, signature)


def content_hash(payload: Any) -> str:
    """Stable 12-char hash of any JSON-serialisable payload.

    Used for immutable, content-addressed objects (sources, cases, scripts).
    Key order is normalised so logically identical payloads hash identically.
    """
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return digest[:_HASH_LEN]


def file_sha256(path: str | os.PathLike[str]) -> str:
    """Full sha256 of a file's bytes, streamed (videos can be large)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_id(prefix: str, payload: Any) -> str:
    """`<prefix>_<12-char content hash>` — same input always yields the same id."""
    return f"{prefix}_{content_hash(payload)}"


def ulid() -> str:
    """Lexicographically sortable time-ordered id, for runs and results.

    26 chars: 10 of millisecond timestamp + 16 of randomness, Crockford base32.
    """
    timestamp = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(10), "big")
    value = (timestamp << 80) | randomness
    chars = []
    for _ in range(26):
        chars.append(_ULID_ALPHABET[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def run_id(prefix: str = "run") -> str:
    """`<prefix>_<ulid>` — sortable by creation time."""
    return f"{prefix}_{ulid()}"
