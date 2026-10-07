"""The one legitimate WRITE path to the repo-root `.env` (every other module
only reads it via `SecretStore`/`parse_env`). Sets one key's value without
ever returning, logging, or echoing the value itself — the caller passes it
straight through to disk.
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from autotester.browser.secrets import parse_env

_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


class InvalidEnvValue(ValueError):
    """Refused a key or value that could corrupt or inject a `.env` line."""


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
    """
    for quote in ('"', "'"):
        if quote not in value:
            candidate = f"{quote}{value}{quote}"
            if parse_env("K=" + candidate + chr(10)).get("K") == value:
                return candidate
    raise InvalidEnvValue(
        "this value cannot be stored safely because it contains both a single and a "
        "double quote. Change the credential, or set it directly in the .env file."
    )


def _validated_updates(values: dict[str, str]) -> dict[str, str]:
    """Render a whole batch before any write, so one bad row changes nothing."""
    rendered: dict[str, str] = {}
    for key, value in values.items():
        if not _KEY_RE.fullmatch(key):
            raise InvalidEnvValue("credential key must use UPPER_SNAKE_CASE")
        if "\n" in value or "\r" in value:
            raise InvalidEnvValue("credential value must not contain a newline")
        rendered[key] = _render_value(value)
    return rendered


def validate_env_values(values: dict[str, str]) -> None:
    """Public validation-only gate used before a multi-artifact intake writes."""
    _validated_updates(values)


@contextlib.contextmanager
def _env_lock(env_path: Path, timeout_s: float = 5.0) -> Iterator[None]:
    """Stable advisory sidecar lock; all cooperative writers share this inode."""
    import math

    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("env lock timeout must be positive and finite")
    env_path = env_path.resolve()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(env_path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError("env writer lock timed out") from exc
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
