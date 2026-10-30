"""Registration for DRIVE sources: `register_drive` -> `Source` rows.

qa/contracts/source-adapters.md DRIVE phase-2 row + SA1-SA6. A folder-scoped
Google Drive listing: the folder itself becomes one DRIVE `Source` (the parent
the files cite), and every file in it becomes a content-addressed CHILD `Source`
of the right kind via the EXISTING adapters -- `register_document`/
`register_audio` (`sources/adapters.py`) and `register_source` (the VIDEO
adapter in `stages/ingest.py`) -- never a re-implementation of extraction (SA1).
Each child carries its Drive file id in `Source.url` and is linked to the folder
via `Source.provenance` (SA4), the `Artifact` envelope every source already
carries; no new parent/child field is invented, exactly as EMAIL did for
attachments. Dedupe is by sha256 of the FETCHED bytes (SA2): the same bytes
fetched twice is ONE Source. A file that cannot be fetched, or whose type no
adapter reads, is still registered -- carrying an `extraction_error` note, never
silently empty or dropped (SA5).

All Drive HTTP and OAuth work lives behind the `DriveClient` seam
(`sources/drive.py`); this module never sees a token (SA3). Split from
`drive.py` for the same reason EMAIL split parse from register: one file per
responsibility, each under the doctor's 300-line rule. A model may later
summarise fetched content for the human, but nothing here lets a model decide
which checks run or alter stored text (SA6).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

from autotester.providers.base import Provider
from autotester.schema.base import Provenance
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.sources.adapters import (
    _EXTRACTION_ERROR_PREFIX,
    Registration,
    register_audio,
    register_document,
)
from autotester.sources.audio import AUDIO_SUFFIXES
from autotester.sources.drive import DriveClient, DriveFile
from autotester.sources.extract import DOC_SUFFIXES
from autotester.stages.ingest import RECORDING_SUFFIXES, register_source
from autotester.store.filestore import exists_path
from autotester.store.project_store import ProjectStore
from autotester.store.run_store import local_blob, store_media

_PROVENANCE_STAGE = "sources.drive"


def register_drive(
    store: ProjectStore,
    folder_id: str,
    client: DriveClient,
    *,
    provider: Provider | None = None,
    secrets: Iterable[str] = (),
    label: str | None = None,
    recorded_on: str | None = None,
) -> list[Registration]:
    """List `folder_id` through `client` and register the folder plus every file
    in it. Returns the folder's `Registration` first, then one per file (SA1:
    all land in the same `sources.jsonl`). No credential is read here -- the
    `DriveClient` seam holds it, so the token never reaches this layer (SA3)."""
    folder = _register_folder(store, folder_id, label, recorded_on)
    results = [folder]
    for drive_file in client.list_folder(folder_id):
        results.append(
            _register_drive_file(store, folder.source, drive_file, client, provider, secrets)
        )
    return results


def _register_folder(
    store: ProjectStore, folder_id: str, label: str | None, recorded_on: str | None
) -> Registration:
    """The folder itself as one DRIVE `Source` (the parent children cite). It
    has no bytes, so its id is content-addressed on the folder id in
    `Source.url`; re-registering the same folder is idempotent on that id (SA2)."""
    source = Source(
        project=store.paths.slug,
        kind=SourceKind.DRIVE,
        url=folder_id,
        label=label,
        recorded_on=recorded_on,
    )
    created = source.id not in {s.id for s in store.list_sources()}
    return Registration(store.add_source(source), created=created)


def _register_drive_file(
    store: ProjectStore,
    parent: Source,
    drive_file: DriveFile,
    client: DriveClient,
    provider: Provider | None,
    secrets: Iterable[str],
) -> Registration:
    """Fetch one file's bytes and register it as a child `Source` of the right
    kind, linked to `parent` (SA4). A fetch failure or an unreadable type is
    registered honestly (SA5), never dropped. Dedupe (SA2 -- identical bytes are
    ONE Source) is the reused adapter's own single guard (`register_document`/
    `register_audio`/`register_source` each dedupe on sha256); this layer does
    not add a second, redundant one -- one concept, one place."""
    provenance = Provenance(produced_by=_PROVENANCE_STAGE, inputs=[parent.id])
    fetched = client.fetch_file(drive_file)
    if fetched.content is None:
        return _register_unfetchable(store, drive_file, provenance, fetched.error)
    written = _write_bytes(store, parent.id, drive_file, fetched.content)
    return _dispatch_by_suffix(store, written, drive_file, provenance, provider, secrets)


def _dispatch_by_suffix(
    store: ProjectStore,
    path: Path,
    drive_file: DriveFile,
    provenance: Provenance,
    provider: Provider | None,
    secrets: Iterable[str],
) -> Registration:
    """Route a fetched file to the EXISTING adapter for its suffix (SA1), Drive
    id carried in `Source.url`. A suffix no adapter reads gets the honest
    default (SA5)."""
    suffix = path.suffix.lower()
    if suffix in DOC_SUFFIXES:
        return register_document(
            store, path, label=drive_file.name, url=drive_file.id, provenance=provenance
        )
    if suffix in AUDIO_SUFFIXES:
        return register_audio(
            store, path, provider=provider, secrets=secrets,
            label=drive_file.name, url=drive_file.id, provenance=provenance,
        )
    if suffix in RECORDING_SUFFIXES:
        source = register_source(
            store, path, label=drive_file.name, url=drive_file.id, provenance=provenance
        )
        return Registration(source, created=True)
    return _register_unreadable_type(store, path, drive_file, provenance)


def _register_unfetchable(
    store: ProjectStore, drive_file: DriveFile, provenance: Provenance, error: str | None
) -> Registration:
    """A file the client could not fetch (SA5). Registered as a DOC-kind Source
    keyed on its Drive id (no bytes to sha256), carrying an `extraction_error`
    note -- never dropped, never silently empty."""
    source = Source(
        project=store.paths.slug,
        kind=SourceKind.DOC,
        url=drive_file.id,
        label=drive_file.name,
        notes=f"{_EXTRACTION_ERROR_PREFIX}: could not fetch from Drive -- {error}",
        provenance=provenance,
    )
    created = source.id not in {s.id for s in store.list_sources()}
    return Registration(store.add_source(source), created=created)


def _register_unreadable_type(
    store: ProjectStore, path: Path, drive_file: DriveFile, provenance: Provenance
) -> Registration:
    """A fetched file whose suffix no adapter reads -- an image, an archive
    (SA5). Registered as DOC with an `extraction_error` note, the same honest
    default EMAIL uses for an unrecognised attachment; the bytes ARE on disk, so
    dedupe is by their sha256 (SA2)."""
    source = Source(
        project=store.paths.slug,
        kind=SourceKind.DOC,
        path=str(path.resolve()),
        sha256=hashlib.sha256(local_blob(path).read_bytes()).hexdigest(),
        url=drive_file.id,
        label=drive_file.name,
        notes=(
            f"{_EXTRACTION_ERROR_PREFIX}: unsupported Drive file type "
            f"'{drive_file.mime_type or path.suffix}' -- no extraction path yet"
        ),
        provenance=provenance,
    )
    return Registration(store.add_source(source), created=True)


def _write_bytes(
    store: ProjectStore, parent_id: str, drive_file: DriveFile, content: bytes
) -> Path:
    """Persist a fetched file's bytes under the folder's source directory so the
    file-based adapters (which need a real `Path`) can read it -- content-
    addressed on a name collision, mirroring EMAIL's attachment writer."""
    safe_name = re.sub(r"[^\w.\-]", "_", drive_file.name) or "file"
    target_dir = store.paths.source_dir(parent_id) / "files"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    if exists_path(target) and target.read_bytes() != content:
        prefix = hashlib.sha256(content).hexdigest()[:8]
        target = target_dir / f"{prefix}_{safe_name}"
    return store_media(target, content)  # M51: GridFS when the blobs area is on mongo
