"""Resolve registered teaching content locally, retaining extraction failures and locators."""

from __future__ import annotations

from pathlib import Path

from autotester.core.ids import content_id, file_sha256
from autotester.schema.document import DocumentReading
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.schema.teaching import TeachingUnit
from autotester.schema.teaching_run import TeachingInput, TeachingMaterial
from autotester.sources.extract import extract_document_text
from autotester.stages.analyze_video import load_transcript
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore

DECLARED_KINDS = {SourceKind.EVAL, SourceKind.CONDITION, SourceKind.USE_CASE}


def _material_document(store: ProjectStore, source: Source):
    receipt = store.paths.sources_dir / source.id / "document.json"
    reading = read_json(receipt, DocumentReading)
    text = source.text
    problems = []
    if reading is None and text is None and source.path:
        extracted = extract_document_text(Path(source.path))
        reading, text = extracted.reading, extracted.text
        problems = ["document extraction incomplete"] if extracted.error else []
    if reading is not None:
        if reading.source_id is not None and reading.source_id != source.id:
            return [], ["document receipt source mismatch"], None
        problems += ["document extraction incomplete"] if reading.error else []
        problems += [f"page {p.number} unreadable" for p in reading.pages if p.error or not p.text]
        return (
            [
                TeachingUnit(locator=f"page {p.number}", text=p.text)
                for p in reading.pages
                if p.text.strip()
            ],
            sorted(set(problems)),
            reading,
        )
    return (
        [TeachingUnit(locator="document", text=text)] if text and text.strip() else [],
        problems,
        None,
    )


def _material_content(store: ProjectStore, source: Source, sources: list[Source]):
    units, problems, transcript, children, document = [], [], None, [], None
    if source.kind in {SourceKind.VIDEO, SourceKind.AUDIO}:
        transcript = load_transcript(store, source)
        if transcript is not None and transcript.source_id != source.id:
            raise ValueError("transcript source mismatch")
        if source.kind is SourceKind.VIDEO and (
            transcript is None or transcript.engine == "unreadable" or not transcript.segments
        ):
            problems.append("video supplied narration missing or unreadable")
        if source.kind is SourceKind.AUDIO:
            if transcript is None or transcript.engine == "unreadable" or not transcript.segments:
                problems.append(
                    "audio transcript missing or unreadable; transcription not requested"
                )
            else:
                units = [
                    TeachingUnit(locator=f"segment {i + 1} ({s.start:g}-{s.end:g}s)", text=s.text)
                    for i, s in enumerate(transcript.segments)
                    if s.text.strip()
                ]
    elif source.kind is SourceKind.DOC:
        units, problems, document = _material_document(store, source)
    elif source.kind in {SourceKind.TEXT, SourceKind.EMAIL, SourceKind.DRIVE}:
        if source.text and source.text.strip():
            units = [
                TeachingUnit(
                    locator="email body" if source.kind is SourceKind.EMAIL else "text",
                    text=source.text,
                )
            ]
        elif source.kind is SourceKind.DRIVE:
            children = sorted(
                s.id for s in sources if s.provenance and source.id in s.provenance.inputs
            )
            if not children:
                problems.append("Drive has no registered resolved content")
    elif source.kind not in DECLARED_KINDS:
        problems.append("unsupported teaching source; register resolved content")
    if source.notes and "extraction_error" in source.notes:
        problems.append("registered extraction error")
    return units, sorted(set(problems)), transcript, children, document


def _input_identity(source, content, receipt_digest, problems, children):
    """Bind registered metadata and the full extracted evidence without storing raw content."""
    identity = TeachingInput(
        source_id=source.id,
        kind=source.kind,
        fingerprint=content_id(
            "teachinput",
            {
                "source": source.model_dump(mode="json"),
                "content": content,
                "receipt": receipt_digest,
                "problems": problems,
                "children": children,
            },
        ),
        content_fingerprint=content_id("teachcontent", content),
    )
    return identity


def resolve_teaching_material(
    store: ProjectStore, source: Source, sources: list[Source]
) -> TeachingMaterial:
    """Fingerprint local evidence; errors contain categories, never source content."""
    units, problems, transcript, children, actual, receipt_digest = [], [], None, [], None, None
    unavailable, document = False, None
    try:
        if source.project != store.paths.slug:
            raise ValueError("wrong project")
        if source.path:
            actual = file_sha256(Path(source.path))
            if source.sha256 and actual != source.sha256:
                raise ValueError("registered source bytes changed")
        receipt = store.paths.sources_dir / source.id / "document.json"
        receipt_digest = file_sha256(receipt) if receipt.exists() else None
        units, problems, transcript, children, document = _material_content(store, source, sources)
        if document is not None:
            document = document.model_copy(update={"source_id": source.id})
    except Exception as exc:
        unavailable = True
        problems = [f"material unavailable ({type(exc).__name__}); re-register source"]
    content = {
        "kind": source.kind,
        "bytes": actual,
        "units": [u.model_dump() for u in units],
        "transcript": transcript.model_dump(mode="json") if transcript else None,
        "document": document.model_dump(
            mode="json", exclude={"created_at", "provenance", "source_id"}
        )
        if document
        else None,
    }
    identity = _input_identity(source, content, receipt_digest, problems, children)
    return TeachingMaterial(
        identity=identity,
        units=units,
        problems=problems,
        transcript=transcript,
        children=children,
        unavailable=unavailable,
        document=document,
    )
