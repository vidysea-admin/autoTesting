"""Atomic video registration, the per-project intake lock, staging and orphan sweep.

Contract: team-intake.md TI6 (R39, R65), TI4. Order is the whole mechanism: the file reaches its
final place FIRST (`os.replace`, with a copy-then-replace fallback across volumes), the source
row is appended SECOND, and a failure between them removes the file. So a row never exists
without its file and matching sha256. The one window a kill can leave open is a file without a
row; the next intake sweeps it (`sweep_orphans`) before doing anything else, which is also what
removes the staging a killed run left behind.

Only store verbs: an exclusive-create lock key (no `fcntl`, no `flock`), and local scratch verbs
for staging. Nothing here is POSIX-only, and nothing at import time touches the disk.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
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
from autotester.store.filestore import delete_path, exists_path, list_children, mtime_path
from autotester.store.filestore_paths import (
    create_exclusive_path,
    remove_empty_dir,
    remove_stray_temps,
    scratch_children,
    scratch_mkdir,
    scratch_rmtree,
    touch_path,
)
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
        stamp = mtime_path(path)
    except OSError:
        return False
    return stamp is not None and time.time() - stamp > stale_s


@contextmanager
def intake_lock(store: ProjectStore, *, timeout_s: float = LOCK_TIMEOUT_S,
                stale_s: float = LOCK_STALE_S, poll_s: float = 0.05
                ) -> Iterator[Callable[[], None]]:
    """One intake at a time per project. Yields a `beat()` that refreshes the lock's mtime so a
    long expansion is not mistaken for a crashed holder; a lock untouched for `stale_s` is taken
    over (a killed process never releases it)."""
    path = store.paths.dir / LOCK_NAME
    deadline = time.monotonic() + timeout_s
    while not create_exclusive_path(path, ""):  # one winner per project, on any backend (M19)
        if _lock_is_stale(path, stale_s):
            delete_path(path)
            continue
        if time.monotonic() > deadline:
            raise IntakeBusy("another intake into this project is still running")
        time.sleep(poll_s)
    try:
        yield lambda: touch_path(path)
    finally:
        delete_path(path)


def staging_root(store: ProjectStore) -> Path:
    """Under the repo's working area, one folder per project (not the repo tree or system temp)."""
    return work_dir(store.paths.root) / "intake" / store.paths.slug


def sweep_orphans(store: ProjectStore) -> int:
    """Remove what a killed intake left: staging folders, and `recording.*` / `.tmp-*` files in a
    source folder that has no row. Call it only while holding the intake lock. Derived data
    (media, transcripts) in a row-less folder is left alone. Returns the number removed."""
    removed = 0
    root = staging_root(store)
    base = store.paths.root
    for leftover in scratch_children(root, base=base):  # video bytes, never state (M25)
        scratch_rmtree(leftover, base=base)
        removed += 1
    known = {s.id for s in store.list_sources()}
    base = store.paths.sources_dir
    for folder in (base / name for name in list_children(base) if name not in known):
        for name in list_children(folder):
            if name.startswith(f"{RECORDING_STEM}."):
                delete_path(folder / name)
                removed += 1
        removed += remove_stray_temps(folder)  # atomic-write temps `list_children` does not list
        remove_empty_dir(folder)
    return removed


@contextmanager
def intake_session(store: ProjectStore, **lock_kwargs) -> Iterator[tuple[Path, Callable[[], None]]]:
    """Lock, sweep, then a fresh staging folder removed on every exit (normal or exception)."""
    with intake_lock(store, **lock_kwargs) as beat:
        sweep_orphans(store)
        staging = staging_root(store) / ulid()
        scratch_mkdir(staging, base=store.paths.root)
        try:
            yield staging, beat
        finally:
            scratch_rmtree(staging, base=store.paths.root)


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
    if exists_path(target):
        raise FileExistsError("a recording is already stored at that place")
    try:
        place_media(staged, target, digest)  # M51: GridFS when the blobs area is on mongo
        store.add_source(draft.model_copy(update={"path": str(target)}))
    except BaseException:
        delete_path(target)
        remove_empty_dir(target.parent)
        raise
    return draft.model_copy(update={"path": str(target)}), True
