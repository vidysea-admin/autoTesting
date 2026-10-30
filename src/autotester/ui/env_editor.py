"""The one legitimate WRITE path to the repo-root `.env` (every other module
only reads it via `SecretStore`/`parse_env`). Sets one key's value without
ever returning, logging, or echoing the value itself — the caller passes it
straight through to disk.

It is also the SECRET DOOR (mongo-store M31): with the credentials area on mongo, a project's
login values are plain documents in `secrets` (D-123: no encryption, no key), written only by
`_put_doc` below, and `save_credentials` sends a value to the store OR to `.env`, never both.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from autotester.browser.secrets import parse_env
from autotester.core.env import (
    MONGO_URI_ENV,
    credential_collection,
    is_server_key,
    read_dotenv,
)
from autotester.core.file_lock import file_lock

_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


class InvalidEnvValue(ValueError):
    """Refused a key or value that could corrupt or inject a `.env` line."""


class CredentialRefused(InvalidEnvValue):
    """The credential store refused a write: a deployment secret (M36), another project's key,
    or no store. Quotes the key name only, never a value."""


def _render_value(value: str) -> str:
    """The `.env` right-hand side that `parse_env` reads back as `value` exactly.

    AT-082: written bare, a value containing ` #`, leading/trailing whitespace,
    or wrapped in quotes came back MANGLED — `_clean_value` strips a trailing
    whitespace-`#` comment, rstrips, and unquotes — while the Credentials page
    still reported "Set". A password like `p@ss #1` was silently stored as
    `p@ss`, and the failure would surface much later as a wrong-password login.

    Quoting round-trips all three, because `_clean_value` returns everything
    between a leading quote and its next match. A value containing BOTH quote
    characters cannot round-trip through that parser, so it is refused rather
    than written wrong — saying no is better than lying about what was stored.

    AT-1368: TWO readers consume this file and they disagree on escapes: `parse_env`
    (SecretStore, no escapes) and `core.env.read_dotenv` (the loader: backslash-n decoded
    inside double quotes, a doubled backslash inside single ones). A candidate (double, single,
    bare) is accepted only if BOTH read it back byte-identical, so a literal backslash-n goes
    out single-quoted and a doubled backslash goes out bare. `read_dotenv` does not
    interpolate, so `${X}` is data.
    """
    for candidate in (f'"{value}"', f"'{value}'", value):
        if _reads_back(candidate, value):
            return candidate
    raise InvalidEnvValue(
        "this value cannot be stored safely: no quoting makes the settings reader and the "
        "loader agree on it (typically it starts with a quote character and holds the other "
        "kind, or ends in a backslash after whitespace). Change the credential, or set it "
        "directly in the .env file."
    )


def _reads_back(candidate: str, value: str) -> bool:
    """True when both `.env` readers return `value` for the line `K=<candidate>`."""
    line = f"K={candidate}" + chr(10)
    return (parse_env(line).get("K") == value
            and read_dotenv(io.StringIO(line)).get("K") == value)


def _check_pair(key: str, value: str) -> None:
    if not _KEY_RE.fullmatch(key):
        raise InvalidEnvValue("credential key must use UPPER_SNAKE_CASE")
    if "\n" in value or "\r" in value:
        raise InvalidEnvValue("credential value must not contain a newline")


def _validated_updates(values: dict[str, str]) -> dict[str, str]:
    """Render a whole batch before any write, so one bad row changes nothing."""
    rendered: dict[str, str] = {}
    for key, value in values.items():
        _check_pair(key, value)
        rendered[key] = _render_value(value)
    return rendered


def validate_env_values(values: dict[str, str]) -> None:
    """Public validation-only gate used before a multi-artifact intake writes. With the store on
    only key and newline are checked: `.env` quoting does not apply to a document."""
    if credential_collection() is None:
        _validated_updates(values)
        return
    for key, value in values.items():
        _check_pair(key, value)


@contextlib.contextmanager
def _env_lock(env_path: Path, timeout_s: float = 5.0) -> Iterator[None]:
    """Stable advisory sidecar lock; all cooperative writers share this inode."""
    with file_lock(env_path.resolve().with_name(env_path.name + ".lock"), timeout_s, what="env"):
        yield


def _write_env_lines(env_path: Path, lines: list[str], rendered: dict[str, str]) -> None:
    """Render normalized reader keys and atomically persist while holding the lock."""
    out: list[str] = []
    replaced: set[str] = set()
    for line in lines:
        parsed = parse_env(line)
        key = next(iter(parsed), None)
        if key in rendered:
            out.append(f"{key}={rendered[key]}")
            replaced.add(key)
        else:
            out.append(line)
    out.extend(f"{key}={value}" for key, value in rendered.items() if key not in replaced)
    fd, temp_name = tempfile.mkstemp(dir=env_path.parent, prefix=".env-", suffix=".tmp")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write("\n".join(out) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, env_path)
    except BaseException:
        if fd >= 0:
            with contextlib.suppress(OSError):
                os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise
    finally:
        with contextlib.suppress(OSError):
            os.chmod(env_path, 0o600)


def create_env_value_if_absent(
    env_path: Path, key: str, factory: Callable[[], str], *, timeout_s: float = 5.0,
) -> str:
    """Select a stored winner or invoke the validated factory inside one lock."""
    _validated_updates({key: ""})
    env_path = env_path.resolve()
    with _env_lock(env_path, timeout_s):
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        matches = [parse_env(line)[key] for line in lines if key in parse_env(line)]
        nonempty = {value for value in matches if value}
        if len(nonempty) > 1 or (nonempty and not matches[-1]):
            raise InvalidEnvValue("ambiguous stored approval key; refusing replacement")
        if nonempty:
            return next(iter(nonempty))
        selected = factory()
        if not selected:
            raise InvalidEnvValue("new env value must not be empty")
        _write_env_lines(env_path, lines, _validated_updates({key: selected}))
        return selected


def set_env_values(env_path: Path, values: dict[str, str]) -> None:
    """Atomically replace/add a validated batch while preserving other keys.

    Refuses a `key` that isn't `UPPER_SNAKE_CASE`, and a `value` containing a
    `\\n`/`\\r` — either one would let a caller inject an arbitrary extra
    `.env` line (a second key, an overridden earlier one) disguised as a
    single value, corrupting the file `SecretStore` parses line-by-line.

    Writes owner-only (0o600) since this file holds real credentials — a
    world/group-readable `.env` defeats the whole credential boundary before
    a value ever reaches `SecretStore`. `os.chmod` is a no-op for POSIX group/
    other bits on Windows (only the read-only flag applies there), so this is
    a real restriction on POSIX deployments and harmless on Windows dev boxes.
    """
    if not values:
        return
    rendered = _validated_updates(values)
    env_path = env_path.resolve()
    with _env_lock(env_path):
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        _write_env_lines(env_path, lines, rendered)


def set_env_value(env_path: Path, key: str, value: str) -> None:
    """Backward-compatible one-key entry point over the atomic batch writer."""
    set_env_values(env_path, {key: value})


# ---- the secret door (mongo-store M31-M37; D-123: plain documents, no key) ----------------------

def _rearm() -> None:
    """Drop the cached secret gate so the next store write rebuilds it with the new values (M34)."""
    from autotester.store.mongo_backend import reset_default_backend

    reset_default_backend()


def _put_doc(coll: Any, doc: dict[str, Any]) -> None:
    """The ONLY write of a credential document (M31(b)): by `_id`, replacing in place."""
    coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)


def put_credentials(slug: str, values: Mapping[str, str]) -> None:
    """Store `values` for project `slug` in `secrets`. The whole batch is checked first (M36: not
    the Mongo URI, `AUTOTESTER_*` or a provider key; another project's key is not overwritten).
    The store down raises `StoreUnavailable`: no fallback to `.env`, a temp file or a log (M32)."""
    coll = credential_collection()
    if coll is None or not slug:
        raise CredentialRefused("the credential store is not on, or no project was named")
    for key, value in values.items():
        if key == MONGO_URI_ENV or is_server_key(key):
            raise CredentialRefused(f"'{key}' is a deployment secret and is never stored")
        if not value:
            raise CredentialRefused(f"'{key}' has no value")
        held = coll.find_one({"_id": key})
        if held is not None and held.get("p") != slug:
            raise CredentialRefused(f"'{key}' belongs to another project")
    for key, value in values.items():
        _put_doc(coll, {"_id": key, "p": slug, "value": value, "updated_at": time.time()})
    _rearm()


def save_credentials(slug: str, env_path: Path, values: Mapping[str, str]) -> None:
    """Where a project's login values go (M35): the store with the credentials area on mongo, else
    `.env` exactly as before. Never both: no second copy on an ephemeral disk."""
    if credential_collection() is None:
        set_env_values(env_path, dict(values))
        return
    for key, value in values.items():
        _check_pair(key, value)
    put_credentials(slug, values)


def drop_credentials(slug: str, keys: Iterable[str] | None = None) -> int:
    """Delete `keys` of project `slug` (a removed SecretRef), or with `keys=None` everything it
    holds, sessions included (a removed project): each `delete_*` carries `p` (M37)."""
    coll = credential_collection()
    if coll is None:
        return 0
    if keys is None:
        from autotester.store.mongo_backend import default_store

        default_store().collection("browser_sessions").delete_many({"p": slug})
        gone = coll.delete_many({"p": slug})
    else:
        gone = sum(coll.delete_one({"_id": key, "p": slug}) for key in keys)
    _rearm()
    return int(gone)


def snapshot_credentials(keys: Iterable[str]) -> dict[str, dict[str, Any] | None]:
    """The stored documents for `keys` (`None` = absent), to put back after a failed commit
    (M37): the store twin of the `.env` byte snapshot. `{}` in file mode."""
    coll = credential_collection()
    return {} if coll is None else {key: coll.find_one({"_id": key}) for key in keys}


def restore_credentials(snapshot: Mapping[str, dict[str, Any] | None]) -> None:
    """Put `snapshot_credentials` back unchanged: a document returns as it was, a new one goes."""
    coll = credential_collection()
    if coll is None or not snapshot:
        return
    for key, doc in snapshot.items():
        if doc is None:
            coll.delete_one({"_id": key})
        else:
            _put_doc(coll, doc)
    _rearm()
