"""Real content fingerprints guard source-set resume and local extraction provenance."""

import pytest
from teaching_helpers import MixedTeacherFake, add_local, add_pdf_receipt, run_teaching

from autotester.schema.document import DocumentReading
from autotester.schema.enums import SourceKind
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.project import Project, Source
from autotester.stages.teach_sources import TeachingInputsChanged
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore


@pytest.mark.parametrize("change", ["set", "text", "bytes", "transcript", "receipt"])
def test_changed_actual_input_requires_new_run_before_model(tmp_path, change):
    store = ProjectStore("demo", root=tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://example.test"))
    if change in {"bytes", "receipt"}:
        source = add_local(store, "input", SourceKind.DOC, "source.md")
        if change == "receipt":
            add_pdf_receipt(store, source)
    elif change == "transcript":
        source = add_local(store, "input", SourceKind.AUDIO, "source.wav")
        store.save_transcript(
            Transcript(
                source_id=source.id,
                engine="sidecar",
                segments=[TranscriptSegment(start=1, end=2, text="Save")],
            )
        )
    else:
        source = store.add_source(
            Source(id="input", project="demo", kind=SourceKind.TEXT, text="Original")
        )
    provider = MixedTeacherFake()
    run_teaching(store, provider)
    if change == "set":
        store.add_source(Source(id="added", project="demo", kind=SourceKind.TEXT, text="Added"))
    elif change == "text":
        store.paths.sources_index.write_text(
            source.model_copy(update={"text": "Changed"}).model_dump_json() + "\n"
        )
    elif change == "bytes":
        from pathlib import Path

        Path(source.path).write_bytes(b"changed actual local bytes")
    elif change == "transcript":
        store.save_transcript(
            Transcript(
                source_id=source.id,
                engine="sidecar",
                segments=[TranscriptSegment(start=1, end=2, text="Changed narration")],
            )
        )
    else:
        path = store.paths.sources_dir / source.id / "document.json"
        receipt = read_json(path, DocumentReading)
        receipt.pages[0].confidence = 80
        write_json(path, receipt)
    with pytest.raises(TeachingInputsChanged):
        run_teaching(store, provider)
    assert len(provider.text_prompts) == 1


@pytest.mark.parametrize(
    "defect", ["bytes", "video_bytes", "receipt_source", "transcript_source", "project"]
)
def test_stale_or_misattributed_content_never_reaches_provider(tmp_path, defect):
    store = ProjectStore("demo", root=tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://example.test"))
    kind = (
        SourceKind.AUDIO
        if defect == "transcript_source"
        else SourceKind.VIDEO
        if defect == "video_bytes"
        else SourceKind.DOC
    )
    source = add_local(store, "input", kind, "source.md")
    if defect in {"bytes", "video_bytes"}:
        from pathlib import Path

        Path(source.path).write_bytes(b"changed since registered")
    elif defect == "receipt_source":
        add_pdf_receipt(store, source)
        path = store.paths.sources_dir / source.id / "document.json"
        receipt = read_json(path, DocumentReading).model_copy(update={"source_id": "another"})
        write_json(path, receipt)
    elif defect == "transcript_source":
        store.save_transcript(
            Transcript(
                source_id=source.id,
                engine="sidecar",
                segments=[TranscriptSegment(start=1, end=2, text="Save")],
            )
        )
        path = store.paths.sources_dir / source.id / "transcript.json"
        transcript = read_json(path, Transcript).model_copy(update={"source_id": "another"})
        write_json(path, transcript)
    else:
        store.paths.sources_index.write_text(
            source.model_copy(update={"project": "other"}).model_dump_json() + "\n"
        )
    provider = MixedTeacherFake()
    result = run_teaching(store, provider)
    assert not result.is_complete and result.outcomes[0].status == "failed"
    assert not provider.text_prompts and not provider.videos and not provider.requested
