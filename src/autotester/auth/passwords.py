"""Password hashing: argon2id via argon2-cffi, behind one hash/verify pair (AU1).

The only module that imports the hashing library, so swapping it (for example to stdlib
`hashlib.scrypt`, the contract's accepted fallback) touches this file alone. Defaults
are argon2id m=64 MiB, t=3, p=4 with a per-hash random salt."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128  # AU6: the upper bound limits hashing cost

_HASHER = PasswordHasher()


class WeakPassword(ValueError):
    """The submitted password is outside the accepted length range."""


def check_password_policy(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise WeakPassword(
            f"a password needs {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters"
        )


def hash_password(password: str) -> str:
    check_password_policy(password)
    return _HASHER.hash(password)


# Hashed once at import, not on the first unknown-email login (which would answer slower).
_DUMMY_HASH = _HASHER.hash("timing-equaliser-not-a-password")


def verify_password(stored_hash: str | None, password: str) -> bool:
    """True only on a match. An unknown account still pays one verify, so the
    response time does not reveal which emails have accounts."""
    try:
        return _HASHER.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _HASHER.check_needs_rehash(stored_hash)
