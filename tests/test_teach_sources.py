"""Synthetic mixed material verifies aggregate dispatch, caches and provenance."""


import pytest
from teaching_helpers import (
    MixedTeacherFake,
    add_local,
    add_pdf_receipt,
    add_supplied_transcript,
    run_teaching,
)

from autotester.core.ids import content_id
from autotester.schema.base import Provenance
from autotester.schema.document import DocumentReading
from autotester.schema.enums import SourceKind
from autotester.schema.flowspec import FlowSpec, Review
from autotester.schema.project import Project, Source
from autotester.schema.teaching_run import TeachingOutcome
from autotester.stages.teach_sources import TeachingInputsChanged
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore


@pytest.fixture
def teaching_store(tmp_path):
    store = ProjectStore("demo", root=tmp_path)
    project = Project(slug="demo", name="Demo", base_url="https://example.test")
    store.save_project(project)
    return store


def test_every_registered_type_is_consumed_with_citations_and_resume_cache(teaching_store):
    store, provider = teaching_store, MixedTeacherFake()
    for sid, kind, text in [
        ("a", SourceKind.TEXT, "Typed"),
        ("b", SourceKind.DOC, "Document"),
        ("d", SourceKind.EMAIL, "Email body"),
    ]:
        store.add_source(Source(id=sid, project="demo", kind=kind, text=text))
    pdf = add_local(store, "c", SourceKind.DOC, "book.pdf")
    add_pdf_receipt(store, pdf)
    audio = add_local(store, "e", SourceKind.AUDIO, "voice.wav")
    add_supplied_transcript(store, audio.id, "Voice instruction", 5, 7)
    add_local(store, "f", SourceKind.VIDEO, "screen.mp4")
    add_supplied_transcript(store, "f", "Developer instruction")
    store.add_source(Source(id="g", project="demo", kind=SourceKind.DRIVE, url="folder-id"))
    store.add_source(
        Source(
            id="h",
            project="demo",
            kind=SourceKind.DOC,
            text="Drive file text",
            provenance=Provenance(produced_by="sources.drive", inputs=["g"]),
        )
    )
    store.add_source(Source(id="i", project="demo", kind=SourceKind.EVAL, text="Declared check"))
    result = run_teaching(store, provider)
    assert result.is_complete and len(result.outcomes) == 9
    assert result.outcomes[-1].status == "declared"
    assert len(provider.text_prompts) == 6 and len(provider.videos) == 1
    assert result.outcomes[6].status == "container"
    refs = [step.source_ref for flow in result.proposal.flows for step in flow.steps]
    assert any(ref.source_id == "c" and ref.locator == "page 1" for ref in refs)
    assert any(ref.source_id == "e" and ref.locator == "segment 1 (5-7s)" for ref in refs)
    assert any(ref.source_id == "f" and ref.t_start == 3 for ref in refs)
    assert all(ref.t_start is None for ref in refs if ref.source_id != "f")
    assert all(flow.kind for flow in result.proposal.flows)
    before = (store.paths.run_dir("mixed") / "teaching.json").read_bytes()
    resumed = run_teaching(store, provider)
    assert (store.paths.run_dir("mixed") / "teaching.json").read_bytes() == before
    assert resumed.proposal.fingerprint == result.proposal.fingerprint
    assert len(provider.text_prompts) == 6 and len(provider.videos) == 1


@pytest.mark.parametrize("reason", ["reading", "page", "note"])
def test_partial_pdf_keeps_readable_pages_and_reports_incomplete(teaching_store, reason):
    source = add_local(teaching_store, "pdf", SourceKind.DOC, "partial.pdf")
    add_pdf_receipt(teaching_store, source, partial=True)
    path = teaching_store.paths.sources_dir / source.id / "document.json"
    receipt = read_json(path, DocumentReading)
    if reason in {"reading", "note"}:
        receipt.pages = receipt.pages[:1]
    if reason in {"page", "note"}:
        receipt.error = None
    if reason == "note":
        teaching_store.paths.sources_index.write_text(
            source.model_copy(
                update={"notes": "extraction_error: known partial reading"}
            ).model_dump_json()
            + "\n"
        )
    write_json(path, receipt)
    result = run_teaching(teaching_store, MixedTeacherFake())
    assert not result.is_complete and result.outcomes[0].status == "partial"
    assert result.outcomes[0].problems and result.proposal.flows
    assert result.outcomes[0].document.pages[0].method == "text"
    assert result.outcomes[0].document.pages[0].confidence is None
    assert result.proposal.flows[0].steps[0].source_ref.locator == "page 1"


@pytest.mark.parametrize("kind", [SourceKind.AUDIO, SourceKind.DRIVE, SourceKind.URL])
def test_missing_audio_or_resolved_content_is_explicit_without_model(teaching_store, kind):
    teaching_store.add_source(Source(id="missing", project="demo", kind=kind, url="metadata"))
    provider = MixedTeacherFake()
    result = run_teaching(teaching_store, provider)
    assert not result.is_complete and result.outcomes[0].status == "failed"
    assert result.outcomes[0].problems and not provider.text_prompts and not provider.videos
    assert not provider.requested


def test_duplicate_evidence_is_one_model_call_and_conflicts_remain_visible(teaching_store):
    store, provider = teaching_store, MixedTeacherFake()
    for sid, text in [("a", "Home|/same"), ("b", "Home|/same"), ("c", "Dashboard|/same")]:
        store.add_source(
            Source(
                id=sid,
                project="demo",
                kind=SourceKind.TEXT,
                text=text,
                notes="extraction_error: partial" if sid == "b" else None,
            )
        )
    result = run_teaching(store, provider)
    assert len(provider.text_prompts) == 2
    assert result.outcomes[1].problems and not result.is_complete
    assert result.outcomes[1].status == "duplicate" and result.outcomes[1].duplicate_of == "a"
    assert result.proposal.conflicts and result.proposal.conflicts[0].source_refs


def test_failed_provider_is_redacted_and_cached_without_repeat(teaching_store):
    teaching_store.paths.env_file.write_text("PASSWORD=sensitive-fixture\n", encoding="utf-8")
    primary = teaching_store.add_source(
        Source(
            id="a",
            project="demo",
            kind=SourceKind.TEXT,
            text="sensitive-fixture student@example.com",
        )
    )
    teaching_store.add_source(primary.model_copy(update={"id": "b"}))
    provider = MixedTeacherFake()
    provider.fail = True
    first = run_teaching(teaching_store, provider)
    second = run_teaching(teaching_store, provider)
    assert not first.is_complete and second.outcomes[0].status == "failed"
    assert second.outcomes[1].status == "duplicate" and second.outcomes[1].duplicate_of == "a"
    assert second.outcomes[1].problems
    assert len(provider.text_prompts) == 1
    assert "sensitive-fixture" not in provider.text_prompts[0]
    assert "sensitive-fixture" not in second.model_dump_json()
    assert "student@example.com" not in second.model_dump_json()


@pytest.mark.parametrize("defect", ["fingerprint", "proposal", "running"])
def test_invalid_or_interrupted_receipt_never_repeats_a_model_call(teaching_store, defect):
    source = teaching_store.add_source(Source(project="demo", kind=SourceKind.TEXT, text="Save"))
    provider = MixedTeacherFake()
    run_teaching(teaching_store, provider)
    path = (
        teaching_store.paths.run_dir("mixed") / "teaching" / f"{content_id('src', source.id)}.json"
    )
    receipt = read_json(path, TeachingOutcome)
    update = (
        {"input_fingerprint": "wrong"}
        if defect == "fingerprint"
        else {"proposal": None}
        if defect == "proposal"
        else {"status": "running"}
    )
    write_json(path, receipt.model_copy(update=update))
    if defect == "running":
        result = run_teaching(teaching_store, provider)
        assert not result.is_complete and "interrupted" in result.outcomes[0].problems[0]
    else:
        with pytest.raises(TeachingInputsChanged):
            run_teaching(teaching_store, provider)
    assert len(provider.text_prompts) == 1


def test_aggregate_never_rewrites_approved_canonical_bytes(teaching_store):
    store = teaching_store
    store.save_flowspec(FlowSpec(project="demo", review=Review(status="approved", by="human")))
    before = store.paths.flowspec.read_bytes()
    store.add_source(Source(project="demo", kind=SourceKind.TEXT, text="Save"))
    result = run_teaching(store, MixedTeacherFake())
    assert result.proposal.review.status.value == "draft"
    assert store.paths.flowspec.read_bytes() == before


def test_empty_registered_set_is_incomplete_without_model(teaching_store):
    provider = MixedTeacherFake()
    result = run_teaching(teaching_store, provider)
    assert not result.is_complete and not result.outcomes and not provider.requested


def test_teaching_artifacts_do_not_enter_case_results(teaching_store):
    store = teaching_store
    store.add_source(Source(id="text", project="demo", kind=SourceKind.TEXT, text="Instruction"))
    assert run_teaching(store, MixedTeacherFake()).is_complete
    assert store.load_results("mixed") == []
