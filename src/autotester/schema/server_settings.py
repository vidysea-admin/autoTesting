"""Admin-set server limits (D-072 G6 and item 10): run concurrency and the upload size ceiling.

Strict on purpose: `"2"`, `2.5`, `True`, `0` and `2**63` are all refused, never coerced, so an
admin page or a hand-edited file cannot store a value the queue or the upload route would
misread. Contract: qa/contracts/hosting.md HO15.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MIB = 1024 * 1024
GIB = 1024 * MIB
DEFAULT_MAX_CONCURRENT_RUNS = 2
MAX_CONCURRENT_RUNS_CEILING = 64
DEFAULT_MAX_UPLOAD_BYTES = 2 * GIB
MIN_UPLOAD_BYTES = 1048576  # 1 MiB; a literal so the advice scanner can tell it is a number
MAX_UPLOAD_BYTES_CEILING = 68719476736  # 64 GiB


class ServerSettings(BaseModel):
    """What the admin chose; absent fields keep the documented defaults."""

    model_config = ConfigDict(extra="forbid", strict=True)

    max_concurrent_runs: int = Field(
        DEFAULT_MAX_CONCURRENT_RUNS, ge=1, le=MAX_CONCURRENT_RUNS_CEILING,
        description="browser runs executing at once, server-wide (one per project at a time)",
    )
    max_upload_bytes: int = Field(
        DEFAULT_MAX_UPLOAD_BYTES, ge=MIN_UPLOAD_BYTES, le=MAX_UPLOAD_BYTES_CEILING,
        description="largest recording the upload route accepts",
    )
