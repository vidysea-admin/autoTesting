"""PDF teaching consumes real pages, exposes unreadable input, and stays local."""

from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from autotester.schema.document import DocumentReading, PdfLimits
from autotester.sources.adapters import register_document
from autotester.sources.extract import extract_document_text
from autotester.sources.pdf_extract import extract_pdf_document
from autotester.sources.pdf_ocr import _pdf_tsv, ocr_pdf_page
from autotester.sources.pdf_worker import read_pdf_pages
from autotester.store.filestore import read_json
from autotester.store.project_store import ProjectStore


def _pdf(path: Path, text: str = "Choose Login", *, encrypted: bool = False) -> Path:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    if text:
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
            DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 14 Tf 20 100 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("fixture-password")
    writer.write(path)
    return path


def test_text_pdf_is_extracted_by_worker_and_registration_keeps_page_provenance(tmp_path):
    path = _pdf(tmp_path / "guide.pdf")
    result = extract_document_text(path)
    assert result.error is None
    assert result.text == "[page 1]\nChoose Login"
    assert result.reading.pages[0].method == "text"
    store = ProjectStore("demo", tmp_path)
    source = register_document(store, path).source
    receipt = read_json(store.paths.sources_dir / source.id / "document.json", DocumentReading)
    assert receipt.source_id == source.id
    assert receipt.pages[0].number == 1
    assert receipt.pages[0].text == "Choose Login"
    assert not register_document(store, path).created


def test_pdf_registration_scrubs_root_secrets_and_contact_details(tmp_path):
    store = ProjectStore("demo", tmp_path)
    store.paths.env_file.write_text("TOKEN=supersecret-value\n", encoding="utf-8")
    source = register_document(store, _pdf(tmp_path / "guide.pdf",
                               "supersecret-value member@example.com")).source
    receipt = (store.paths.sources_dir / source.id / "document.json").read_text()
    assert "supersecret-value" not in receipt + source.text
    assert "member@example.com" not in receipt + source.text
    assert "REDACTED" in receipt


def test_corrupt_and_encrypted_pdf_are_explicit_failures(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.7 broken private document")
    broken = extract_pdf_document(path)
    encrypted = read_pdf_pages(_pdf(tmp_path / "locked.pdf", encrypted=True), PdfLimits())
    assert broken.error and not broken.pages
    assert encrypted.error.startswith("encrypted") and not encrypted.pages


def test_pdf_file_page_and_character_limits_refuse_incomplete_readings(tmp_path):
    path = _pdf(tmp_path / "guide.pdf")
    assert "file size" in extract_pdf_document(path, PdfLimits(max_bytes=1)).error
    limited = read_pdf_pages(path, PdfLimits(max_chars=1))
    assert "character" in limited.error
    assert limited.pages[0].number == 1 and limited.pages[0].error
    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    writer.add_blank_page(100, 100)
    writer.write(path)
    assert "page count" in read_pdf_pages(path, PdfLimits(max_pages=1)).error


def test_blank_page_runs_local_ocr_and_missing_engine_is_not_silence(tmp_path, monkeypatch):
    monkeypatch.setattr("autotester.sources.pdf_ocr.shutil.which", lambda _: None)
    result = read_pdf_pages(_pdf(tmp_path / "scanned.pdf", ""), PdfLimits())
    assert result.error and len(result.pages) == 1
    assert result.pages[0].method == "unreadable"
    assert "requires" in result.pages[0].error


def test_pdf_ocr_tsv_preserves_lines_and_confidence():
    tsv = ("page_num\tblock_num\tpar_num\tline_num\tconf\ttext\n"
           "1\t1\t1\t1\t90\tChoose\n1\t1\t1\t1\t80\tLogin\n"
           "1\t1\t1\t2\t100\tSubmit\n")
    assert _pdf_tsv(tsv) == ("Choose Login\nSubmit", 90.0)
    with pytest.raises(ValueError):
        _pdf_tsv(tsv.replace("90\tChoose", "190\tChoose"))


def test_pdf_worker_deadline_is_explicit_and_no_document_text_is_echoed(tmp_path, monkeypatch):
    import subprocess

    observed = []

    def hang(*args, **kwargs):
        observed.append(kwargs["timeout"])
        raise subprocess.TimeoutExpired("private command", 0.25)

    monkeypatch.setattr("autotester.sources.pdf_extract.subprocess.run", hang)
    result = extract_pdf_document(_pdf(tmp_path / "guide.pdf"), PdfLimits(timeout_s=0.25))
    assert "deadline" in result.error
    assert "private" not in result.error
    assert observed == [0.25]


def test_pdf_local_ocr_commands_are_bounded_and_fail_closed(tmp_path, monkeypatch):
    import subprocess

    monkeypatch.setattr("autotester.sources.pdf_ocr.shutil.which", lambda name: name)
    calls = []

    def failed(arguments, **kwargs):
        calls.append((arguments, kwargs))
        raise subprocess.TimeoutExpired("private OCR page", 1)

    monkeypatch.setattr("autotester.sources.pdf_ocr.subprocess.run", failed)
    result = ocr_pdf_page(tmp_path / "scan.pdf", 2, PdfLimits(page_timeout_s=1))
    assert result.error and result.method == "unreadable"
    args, options = calls[0]
    assert args[args.index("-f") + 1] == "2"
    assert args[args.index("-scale-to") + 1] == "2000"
    assert options["timeout"] == 1 and options["check"] is True
    assert options["env"]["OMP_THREAD_LIMIT"] == "1"


def test_scanned_pdf_real_local_ocr_keeps_page_and_method(tmp_path):
    import shutil

    from PIL import Image, ImageDraw, ImageFont

    if not all(shutil.which(tool) for tool in ("pdftoppm", "tesseract")):
        pytest.skip("real scanned-PDF acceptance requires local Poppler and Tesseract")
    path = tmp_path / "scan.pdf"
    image = Image.new("RGB", (1600, 600), "white")
    ImageDraw.Draw(image).text((90, 200), "Choose Login then Submit",
                              fill="black", font=ImageFont.load_default(size=64))
    image.save(path, "PDF", resolution=144)
    result = extract_pdf_document(path)
    assert result.error is None
    assert len(result.pages) == 1
    assert result.pages[0].number == 1 and result.pages[0].method == "ocr"
    assert result.pages[0].text == "Choose Login then Submit"
    assert result.pages[0].confidence >= 70
    writer = PdfWriter()
    writer.append(_pdf(tmp_path / "text.pdf"))
    writer.append(path)
    mixed_path = tmp_path / "mixed.pdf"
    writer.write(mixed_path)
    mixed = extract_pdf_document(mixed_path)
    assert mixed.error is None
    assert [page.method for page in mixed.pages] == ["text", "ocr"]
    assert [page.number for page in mixed.pages] == [1, 2]


def test_low_confidence_ocr_is_explicit_review_requirement(tmp_path, monkeypatch):
    monkeypatch.setattr("autotester.sources.pdf_ocr.shutil.which", lambda tool: tool)

    def fake_tool(arguments, timeout):
        if arguments[0] == "tesseract":
            Path(arguments[2]).with_suffix(".tsv").write_text(
                "page_num\tblock_num\tpar_num\tline_num\tconf\ttext\n"
                "1\t1\t1\t1\t30\tLogin\n", encoding="utf-8")

    monkeypatch.setattr("autotester.sources.pdf_ocr._pdf_tool", fake_tool)
    page = ocr_pdf_page(tmp_path / "scan.pdf", 1, PdfLimits())
    assert page.text == "Login" and page.confidence == 30
    assert "confidence" in page.error
    oversized = ocr_pdf_page(tmp_path / "scan.pdf", 1, PdfLimits(max_chars=1))
    assert oversized.method == "unreadable" and oversized.error


def test_invalid_pdf_limits_cannot_disable_resource_bounds():
    from pydantic import ValidationError

    for field, value in (("max_bytes", 0), ("max_pages", 0), ("max_chars", 0),
                         ("timeout_s", 0), ("page_timeout_s", 0), ("image_side", 1),
                         ("max_bytes", 200_000_001), ("max_pages", 1001),
                         ("max_chars", 2_000_001), ("timeout_s", 601),
                         ("page_timeout_s", 61), ("image_side", 4001),
                         ("min_confidence", -1), ("min_confidence", 101)):
        with pytest.raises(ValidationError):
            PdfLimits(**{field: value})


def test_pdf_supervisor_refuses_oversized_and_invalid_worker_output(tmp_path, monkeypatch):
    def output(arguments, **kwargs):
        Path(arguments[-2]).write_text(" " * 2000, encoding="utf-8")

    monkeypatch.setattr("autotester.sources.pdf_extract.subprocess.run", output)
    result = extract_pdf_document(_pdf(tmp_path / "guide.pdf"),
                                  PdfLimits(max_chars=1, max_pages=1))
    assert "output exceeds" in result.error


def test_pdf_registration_refuses_encoded_secret_before_persistence(tmp_path):
    import base64

    store = ProjectStore("demo", tmp_path)
    store.paths.env_file.write_text("TOKEN=supersecret-value\n", encoding="utf-8")
    encoded = base64.b64encode(b"supersecret-value").decode()
    with pytest.raises(ValueError, match="refusing"):
        register_document(store, _pdf(tmp_path / "guide.pdf", encoded))
    assert not store.list_sources()
