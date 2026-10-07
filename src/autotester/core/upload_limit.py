"""The ONE accessor for the admin upload limit (`max_upload_bytes`), read at request time.

Contract: team-intake.md TI9, hosting.md HO15/HO30/HO33. The HTTP upload, the Drive fetch and zip
member inflation all call `read_max_upload_bytes`; there is no second copy of the limit, and the
value is re-read on every call so an admin change applies to the next request without a restart.

T-203 owns the admin page and the `ServerSettings` model. Until it lands this reads the same key,
`max_upload_bytes`, from a small JSON file named by `AUTOTESTER_SERVER_SETTINGS` (default
`server_settings.json` at the repo root); T-203 swaps the file source for its model and keeps
this function's signature, so no caller changes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import NamedTuple

from autotester.core.paths import repo_root
from autotester.schema.intake import DEFAULT_MAX_UPLOAD_BYTES

SETTINGS_ENV = "AUTOTESTER_SERVER_SETTINGS"
SETTINGS_KEY = "max_upload_bytes"
MIN_UPLOAD_BYTES = 1024**2
MAX_UPLOAD_BYTES = 64 * 1024**3
"""HO15 bounds: an integer between 1 MiB and 64 GiB; anything else is not a limit."""


class UploadLimit(NamedTuple):
    """The limit and where it came from; a fallback says why (HO15: 'and say so')."""

    bytes: int
    from_default: bool
    note: str


def human_bytes(count: int) -> str:
    """`5 MiB`, `2 GiB`, `1.5 KiB`: the form a refusal message names the limit in."""
    value = float(count)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:g} {unit}" if unit == "B" else f"{round(value, 2):g} {unit}"
        value /= 1024
    return f"{count} B"  # pragma: no cover - the loop always returns at GiB


def _default(why: str) -> UploadLimit:
    shown = human_bytes(DEFAULT_MAX_UPLOAD_BYTES)
    return UploadLimit(DEFAULT_MAX_UPLOAD_BYTES, True,
                       f"{SETTINGS_KEY}: {why}; using the default {shown}")


def _settings_path(settings_file: Path | None) -> Path:
    if settings_file is not None:
        return settings_file
    named = os.environ.get(SETTINGS_ENV)
    return Path(named) if named else repo_root() / "server_settings.json"


def read_max_upload_bytes(settings_file: Path | None = None) -> UploadLimit:
    """The admin's `max_upload_bytes`, or the 2 GiB default with the reason it fell back."""
    path = _settings_path(settings_file)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _default("no setting saved yet")
    except (OSError, ValueError):
        return _default("settings file unreadable or corrupt")
    value = payload.get(SETTINGS_KEY) if isinstance(payload, dict) else None
    if isinstance(value, bool) or not isinstance(value, int):
        return _default("setting is not a whole number")
    if not MIN_UPLOAD_BYTES <= value <= MAX_UPLOAD_BYTES:
        return _default("setting is outside 1 MiB to 64 GiB")
    return UploadLimit(value, False, f"{SETTINGS_KEY} = {human_bytes(value)} (admin setting)")
