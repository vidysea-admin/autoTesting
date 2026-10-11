"""The ONE accessor for the admin upload limit (`max_upload_bytes`), read at request time.

Contract: team-intake.md TI9, hosting.md HO15/HO30/HO33. The HTTP upload, the Drive fetch and zip
member inflation all call `read_max_upload_bytes`; there is no second copy of the limit, and the
value is re-read on every call so an admin change applies to the next request without a restart.

The value itself comes from `store.server_settings` (T-203's `ServerSettings`, re-read on every
call); this module only adds the human-facing note and `human_bytes`.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from autotester.schema.server_settings import DEFAULT_MAX_UPLOAD_BYTES
from autotester.store.server_settings import effective_max_upload_bytes, load_server_settings

SETTINGS_KEY = "max_upload_bytes"


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


def read_max_upload_bytes(root: Path | None = None) -> UploadLimit:
    """The admin's `max_upload_bytes`; a fallback to the default says why (HO15)."""
    value = effective_max_upload_bytes(root)
    saved, why = load_server_settings(root)
    if saved is not None:
        return UploadLimit(value, False, f"{SETTINGS_KEY} = {human_bytes(value)} (admin setting)")
    reason = why or "no setting saved yet"
    return UploadLimit(value, True, f"{SETTINGS_KEY}: {reason}; using "
                       f"{human_bytes(value)} (default {human_bytes(DEFAULT_MAX_UPLOAD_BYTES)})")
