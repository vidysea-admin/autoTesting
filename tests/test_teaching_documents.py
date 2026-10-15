"""Run-local document receipts preserve lazy extraction evidence and bind corrupt inputs."""

import pytest
from teaching_helpers import MixedTeacherFake, add_local, run_teaching

from autotester.schema.document import DocumentPage, DocumentReading
from autotester.schema.enums import SourceKind
from autotester.schema.project import Project
from autotester.sources.extract import Extraction
from autotester.stages.teach_sources import TeachingInputsChanged
from autotester.store.project_store import ProjectStore


def test_lazy_pdf_retains_page_method_confidence_and_freezes_its_reading(tmp_path, monkeypatch):
    store = ProjectStore("demo", root=tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://example.test"))
    source = add_local(store, "pdf", SourceKind.DOC, "lazy.pdf")
    reading = DocumentReading(
        pages=[DocumentPage(number=1, text="OCR instruction", method="ocr", confidence=88.5)]
    )
    monkeypatch.setattr(
        "autotester.stages.source_material.extract_document_text",
        lambda path: Extraction("OCR instruction", None, reading),
    )
    provider = MixedTeacherFake()
    result = run_teaching(store, provider)
    document = result.outcomes[0].document
    assert result.is_complete and document.source_id == source.id
    assert document.pages[0].method == "ocr" and document.pages[0].confidence == 88.5
    run_teaching(store, provider)
    assert len(provider.text_prompts) == 1
    reading.pages[0].confidence = 70
    with pytest.raises(TeachingInputsChanged):
        run_teaching(store, provider)


def test_corrupt_receipt_edit_requires_new_run_without_a_provider(tmp_path):
    store = ProjectStore("demo", root=tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://example.test"))
    source = add_local(store, "pdf", SourceKind.DOC, "broken.pdf")
    path = store.paths.sources_dir / source.id / "document.json"
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")
    provider = MixedTeacherFake()
    result = run_teaching(store, provider)
    assert not result.is_complete and not provider.requested
    path.write_text("[{", encoding="utf-8")
    with pytest.raises(TeachingInputsChanged):
        run_teaching(store, provider)
    assert not provider.requested
