"""Read and write the admin's server settings; resolve what is in force right now.

Precedence for every knob, re-read on each call so a change applies without a restart:
the saved settings file (what the admin chose), else the environment default
(`AUTOTESTER_MAX_CONCURRENT_RUNS`, `AUTOTESTER_MAX_UPLOAD_BYTES`), else the built-in default.
A missing file is normal; a corrupt one falls back to the defaults and says why.
Contract: qa/contracts/hosting.md HO15.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from autotester.core.paths import data_root
from autotester.schema.server_settings import (
    DEFAULT_MAX_CONCURRENT_RUNS,
    DEFAULT_MAX_UPLOAD_BYTES,
    MAX_CONCURRENT_RUNS_CEILING,
    MAX_UPLOAD_BYTES_CEILING,
    MIN_UPLOAD_BYTES,
    ServerSettings,
)
from autotester.store.filestore import read_json, write_json

log = logging.getLogger(__name__)
CONCURRENCY_ENV = "AUTOTESTER_MAX_CONCURRENT_RUNS"
UPLOAD_ENV = "AUTOTESTER_MAX_UPLOAD_BYTES"
FILE_NAME = "server_settings.json"


def settings_path(root: Path | None = None) -> Path:
    return data_root(root) / ".work" / FILE_NAME


def load_server_settings(root: Path | None = None) -> tuple[ServerSettings | None, str | None]:
    """`(settings, None)`; `(None, None)` when never saved; `(None, why)` when unreadable."""
    try:
        return read_json(settings_path(root), ServerSettings), None
    except ValueError as exc:
        log.warning("server settings unreadable, using defaults: %s", exc)
        return None, "the saved server settings could not be read; defaults are in force"


def save_server_settings(settings: ServerSettings, root: Path | None = None) -> None:
    write_json(settings_path(root), settings)


def _env_int(name: str, default: int, low: int, high: int) -> int:
    """Unset or non-numeric -> `default`; out of range -> clamped (a typo never stops the site)."""
    raw = os.environ.get(name, "").strip()
    try:
        return min(high, max(low, int(raw))) if raw else default
    except ValueError:
        return default


def effective_max_concurrent_runs(root: Path | None = None) -> int:
    saved, _ = load_server_settings(root)
    if saved is not None:
        return saved.max_concurrent_runs
    return _env_int(CONCURRENCY_ENV, DEFAULT_MAX_CONCURRENT_RUNS, 1, MAX_CONCURRENT_RUNS_CEILING)


def effective_max_upload_bytes(root: Path | None = None) -> int:
    saved, _ = load_server_settings(root)
    if saved is not None:
        return saved.max_upload_bytes
    return _env_int(UPLOAD_ENV, DEFAULT_MAX_UPLOAD_BYTES, MIN_UPLOAD_BYTES,
                    MAX_UPLOAD_BYTES_CEILING)
