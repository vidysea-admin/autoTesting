"""Registration for EMAIL sources: `register_email` -> `Source` rows.

qa/contracts/source-adapters.md EMAIL phase-2 row + SA1-SA6. Parsing
(`sources/email.py`) turns raw bytes into a body text + attachment bytes, or
an honest reason it could not; THIS module does the registering -- one EMAIL
`Source` per message (a `.mbox` with N messages is N Sources, never one
aggregated blob, so provenance stays per-message), each attachment delegated
to the EXISTING `sources.adapters.register_document`/`register_audio` --
never a re-implementation of extraction (SA1) -- and linked to its parent
message via `Source.provenance` (SA4), the envelope every `Artifact` already
carries; no second parent/child field was invented. Split out of
`sources/email.py` to keep both files under the doctor's 300-line rule, the
same reason `sources/audio.py` stays separate from `sources/adapters.py`.

No IMAP/SMTP fetch and no mailbox credentials are read anywhere in this
module (SA3) -- everything here operates on bytes already on local disk. A
`.mbox` with zero parseable messages, and an attachment type neither DOC nor
AUDIO recognises, get the same honest treatment as a corrupt message: always
a Source carrying an `extraction_error` note, never silently dropped (SA5).
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
    _existing_by_digest,
    register_audio,
    register_document,
)
from autotester.sources.audio import AUDIO_SUFFIXES
from autotester.sources.email import EMAIL_SUFFIXES, Attachment, iter_mbox_messages, parse_eml_bytes
from autotester.sources.extract import DOC_SUFFIXES
from autotester.store.filestore import exists_path
from autotester.store.project_store import ProjectStore
from autotester.store.run_store import store_media

_PROVENANCE_STAGE = "sources.email"


def register_email(
    store: ProjectStore,
    path: Path,
    *,
    provider: Provider | None = None,
    secrets: Iterable[str] = (),
    label: str | None = None,
    recorded_on: str | None = None,
) -> list[Registration]:
    """A `.eml` (one message) or `.mbox` (N messages) LOCAL file -> one EMAIL
    `Source` per message. No mailbox credentials are ever read here -- these
    are local files already on disk (SA3). Each message's own attachments
    become CHILD Sources via `register_document`/`register_audio`, linked to
    their parent via `Source.provenance` (SA4). A message -- or a whole
    `.mbox` -- that cannot be parsed at all is still registered, carrying an
    `extraction_error` note, never silently skipped (SA5).
    """
    if not path.exists():
        raise FileNotFoundError(f"no such email file: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"that is a folder, not an email file: {path}")
    if path.suffix.lower() not in EMAIL_SUFFIXES:
        raise ValueError(
            "that is not an email file — add a file ending in "
            + ", ".join(sorted(EMAIL_SUFFIXES))
        )
    if path.suffix.lower() == ".mbox":
        raw_messages = iter_mbox_messages(path)
        if not raw_messages:
            return [_register_unparseable_mbox(store, path, label, recorded_on)]
        return [
            _register_email_message(store, raw, provider, secrets, label, recorded_on)
            for raw in raw_messages
        ]
    raw = path.read_bytes()
    return [_register_email_message(store, raw, provider, secrets, label, recorded_on)]


def _register_email_message(
    store: ProjectStore,
    raw: bytes,
    provider: Provider | None,
    secrets: Iterable[str],
    label: str | None,
    recorded_on: str | None,
) -> Registration:
    """Dedupe + register ONE message's raw bytes (SA2: identical bytes twice
    is ONE Source, and its attachments are not re-registered either, since
    `register_document`/`register_audio` apply the same dedupe themselves)."""
    digest = hashlib.sha256(raw).hexdigest()
    existing = _existing_by_digest(store, digest)
    if existing is not None:
        return Registration(existing, created=False)
    parsed = parse_eml_bytes(raw)
    note = f"{_EXTRACTION_ERROR_PREFIX}: {parsed.error}" if parsed.error is not None else None
    source = store.add_source(
        Source(
            project=store.paths.slug,
            kind=SourceKind.EMAIL,
            text=parsed.body_text,
            sha256=digest,
            label=label,
            recorded_on=recorded_on,
            notes=note,
        )
    )
    for attachment in parsed.attachments:
        _register_email_attachment(store, source, attachment, provider, secrets)
    return Registration(source, created=True)


def _register_unparseable_mbox(
    store: ProjectStore, path: Path, label: str | None, recorded_on: str | None
) -> Registration:
    """A `.mbox` that opened but yielded zero messages (empty, or content
    that is not mbox-shaped at all) -- registered as one honest
    `extraction_error` Source, dedupe keyed on the whole file's bytes since
    no individual message could be identified (SA5, never silently empty)."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    existing = _existing_by_digest(store, digest)
    if existing is not None:
        return Registration(existing, created=False)
    source = store.add_source(
        Source(
            project=store.paths.slug,
            kind=SourceKind.EMAIL,
            path=str(path.resolve()),
            sha256=digest,
            label=label,
            recorded_on=recorded_on,
            notes=f"{_EXTRACTION_ERROR_PREFIX}: mbox contained no parseable messages",
        )
    )
    return Registration(source, created=True)


def _register_email_attachment(
    store: ProjectStore,
    parent: Source,
    attachment: Attachment,
    provider: Provider | None,
    secrets: Iterable[str],
) -> Registration:
    """One attachment -> a CHILD Source, reusing the EXISTING DOC/AUDIO
    adapters so extraction is never duplicated (SA1) -- linked to `parent`
    via `Source.provenance` (SA4). A type neither adapter recognises (an
    image, say) still becomes a Source, honestly marked `extraction_error`
    (SA5) rather than silently dropped."""
    digest = hashlib.sha256(attachment.content).hexdigest()
    existing = _existing_by_digest(store, digest)
    if existing is not None:
        return Registration(existing, created=False)
    written = _write_attachment_to_disk(store, parent.id, attachment)
    provenance = Provenance(produced_by=_PROVENANCE_STAGE, inputs=[parent.id])
    suffix = written.suffix.lower()
    if suffix in DOC_SUFFIXES:
        return register_document(store, written, label=attachment.filename, provenance=provenance)
    if suffix in AUDIO_SUFFIXES:
        return register_audio(
            store,
            written,
            provider=provider,
            secrets=secrets,
            label=attachment.filename,
            provenance=provenance,
        )
    return _register_unrecognised_attachment(store, written, digest, attachment, provenance)


def _register_unrecognised_attachment(
    store: ProjectStore,
    path: Path,
    digest: str,
    attachment: Attachment,
    provenance: Provenance,
) -> Registration:
    """The honest default (SA5) for an attachment neither DOC nor AUDIO
    claims -- an image or other binary. Registered, never dropped, carrying
    an `extraction_error` note the same shape `sources/extract.py` uses for
    an unsupported document suffix."""
    source = store.add_source(
        Source(
            project=store.paths.slug,
            kind=SourceKind.DOC,
            path=str(path.resolve()),
            sha256=digest,
            label=attachment.filename,
            notes=(
                f"{_EXTRACTION_ERROR_PREFIX}: unsupported attachment type "
                f"'{attachment.content_type}' -- no extraction path yet"
            ),
            provenance=provenance,
        )
    )
    return Registration(source, created=True)


def _write_attachment_to_disk(store: ProjectStore, parent_id: str, attachment: Attachment) -> Path:
    """Persist one attachment's bytes under the parent message's source
    directory so `register_document`/`register_audio` -- which need a real
    `Path` -- can read it. A same-named-but-different-content attachment
    (rare, but two messages could each carry a "notes.txt") is content-
    addressed onto disk rather than overwritten."""
    safe_name = re.sub(r"[^\w.\-]", "_", attachment.filename) or "attachment"
    target_dir = store.paths.source_dir(parent_id) / "attachments"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    if exists_path(target) and target.read_bytes() != attachment.content:
        prefix = hashlib.sha256(attachment.content).hexdigest()[:8]
        target = target_dir / f"{prefix}_{safe_name}"
    return store_media(target, attachment.content)  # M51: GridFS when the blobs area is on mongo
