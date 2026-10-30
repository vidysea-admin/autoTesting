"""Atomic video registration, the per-project intake lock, staging and orphan sweep.

Contract: team-intake.md TI6 (R39, R65), TI4. Order is the whole mechanism: the file reaches its
final place FIRST (`os.replace`, with a copy-then-replace fallback across volumes), the source
row is appended SECOND, and a failure between them removes the file. So a row never exists
without its file and matching sha256. The one window a kill can leave open is a file without a
row; the next intake sweeps it (`sweep_orphans`) before doing anything else, which is also what
removes the staging a killed run left behind.

Only portable primitives: an `O_CREAT | O_EXCL` lock file (no `fcntl`, no `flock`),
`os.replace`, `pathlib`. Nothing here is POSIX-only, and nothing at import time touches the disk.
"""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from datetime import datetime
from pathlib import Path

from autotester.core.ids import ulid
from autotester.core.paths import work_dir
from autotester.schema.base import utc_now
from autotester.schema.enums import SourceKind
from autotester.schema.intake import SourceOrigin
from autotester.schema.project import Source
from autotester.sources.zip_names import ensure_inside
from autotester.stages.ingest import require_recording_suffix
from autotester.store.project_store import ProjectStore
from autotester.store.run_store import place_media

LOCK_NAME = ".intake.lock"
LOCK_TIMEOUT_S = 600.0
LOCK_STALE_S = 1800.0
RECORDING_STEM = "recording"


class IntakeBusy(RuntimeError):
    """Another intake into this project held the lock past the timeout."""


def _lock_is_stale(path: Path, stale_s: float) -> bool:
    try:
        return time.time() - path.stat().st_mtime > stale_s
    except OSError:
        return False


@contextmanager
def intake_lock(store: ProjectStore, *, timeout_s: float = LOCK_TIMEOUT_S,
                stale_s: float = LOCK_STALE_S, poll_s: float = 0.05
                ) -> Iterator[Callable[[], None]]:
    """One intake at a time per project. Yields a `beat()` that refreshes the lock's mtime so a
    long expansion is not mistaken for a crashed holder; a lock untouched for `stale_s` is taken
    over (a killed process never releases it)."""
    path = store.paths.dir / LOCK_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            if _lock_is_stale(path, stale_s):
                path.unlink(missing_ok=True)
                continue
            if time.monotonic() > deadline:
                raise IntakeBusy("another intake into this project is still running") from None
            time.sleep(poll_s)
    try:
        yield lambda: os.utime(path, None)
    finally:
        path.unlink(missing_ok=True)


def staging_root(store: ProjectStore) -> Path:
    """Under the repo's working area, one folder per project (not the repo tree or system temp)."""
    return work_dir(store.paths.root) / "intake" / store.paths.slug


def sweep_orphans(store: ProjectStore) -> int:
    """Remove what a killed intake left: staging folders, and `recording.*` / `.tmp-*` files in a
    source folder that has no row. Call it only while holding the intake lock. Derived data
    (media, transcripts) in a row-less folder is left alone. Returns the number removed."""
    removed = 0
    root = staging_root(store)
    for leftover in list(root.iterdir()) if root.is_dir() else []:
        shutil.rmtree(leftover, ignore_errors=True)
        removed += 1
    known = {s.id for s in store.list_sources()}
    base = store.paths.sources_dir
    for folder in list(base.iterdir()) if base.is_dir() else []:
        if not folder.is_dir() or folder.name in known:
            continue
        for stray in [*folder.glob(f"{RECORDING_STEM}.*"), *folder.glob(".tmp-*")]:
            stray.unlink(missing_ok=True)
            removed += 1
        with suppress(OSError):
            folder.rmdir()
    return removed


@contextmanager
def intake_session(store: ProjectStore, **lock_kwargs) -> Iterator[tuple[Path, Callable[[], None]]]:
    """Lock, sweep, then a fresh staging folder removed on every exit (normal or exception)."""
    with intake_lock(store, **lock_kwargs) as beat:
        sweep_orphans(store)
        staging = staging_root(store) / ulid()
        staging.mkdir(parents=True)
        try:
            yield staging, beat
        finally:
            shutil.rmtree(staging, ignore_errors=True)


def commit_video(store: ProjectStore, staged: Path, *, digest: str, suffix: str,
                 label: str | None, origin: SourceOrigin, uploaded_by: str | None,
                 uploaded_at: datetime | None = None, recorded_on: str | None = None
                 ) -> tuple[Source, bool]:
    """Register `staged` (already hashed to `digest`) as one VIDEO source: `(source, created)`.

    The caller holds the intake lock. Same bytes already registered -> `(existing, False)` and
    nothing is written. The stored path is `sources/<id>/recording<suffix>`, built from the
    content-derived id and the vetted suffix, never from a supplied name (TI4)."""
    for existing in store.list_sources():
        if existing.sha256 == digest:
            return existing, False
    require_recording_suffix(f"{RECORDING_STEM}{suffix}")
    draft = Source(project=store.paths.slug, kind=SourceKind.VIDEO, sha256=digest, label=label,
                   uploaded_by=uploaded_by, uploaded_at=uploaded_at or utc_now(), origin=origin,
                   recorded_on=recorded_on)
    target = ensure_inside(store.paths.source_dir(draft.id) / f"{RECORDING_STEM}{suffix}",
                           store.paths.sources_dir)
    if target.exists():
        raise FileExistsError("a recording is already stored at that place")
    try:
        place_media(staged, target, digest)  # M51: GridFS when the blobs area is on mongo
        store.add_source(draft.model_copy(update={"path": str(target)}))
    except BaseException:
        target.unlink(missing_ok=True)
        with suppress(OSError):
            target.parent.rmdir()
        raise
    return draft.model_copy(update={"path": str(target)}), True
