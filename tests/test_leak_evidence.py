"""T-209 (multi-role-platform.md MP9, MP10, MPI1): leak evidence stores no third-party data.

Synthetic tenants only (MPI2). The key is a synthetic value set through the monkeypatched
environment, never the real `.env`. The OCR engine is faked so masking is exercised without
Tesseract; with the engine missing the screenshot is withheld, never written raw.
"""

from __future__ import annotations

import hmac
import logging
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin
from pydantic import ValidationError

from autotester.core import image_privacy as privacy
from autotester.schema.leak_evidence import LeakEvidence
from autotester.schema.multi_role_enums import FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding, ReproVerb, parse_repro_step
from autotester.stages import leak_evidence as stage

KEY_ENV = stage.LEAK_KEY_ENV
NAME, EMAIL, PHONE = "Zorblax Quimby", "zorblax.quimby@canary.invalid", "+1 (555) 013-7788"
RAW_IDS = [f"STU-canary-{90210 + n}" for n in range(7)]
ROWS = [{"id": rid, "Student name": NAME if n == 0 else f"Pupil Canary{n}",
         "Email": EMAIL if n == 0 else f"p{n}@canary.invalid",
         "Phone": PHONE if n == 0 else f"+1 555 014 70{n:02d}"} for n, rid in enumerate(RAW_IDS)]
CANARIES = [NAME, EMAIL, PHONE, "zorblax", "013-7788", "Pupil Canary3", "p3@canary.invalid",
            *RAW_IDS]
HEADER = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
          "left\ttop\twidth\theight\tconf\ttext\n")
URL = "https://a.example.test/students/90210?page=2&q=Zorblax#top"


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEY_ENV, "synthetic-master-key-for-tests")


def _png(path: Path) -> bytes:
    info = PngImagePlugin.PngInfo()
    info.add_text("note", "CANARY-META " + NAME)
    Image.new("RGB", (100, 60), "white").save(path, pnginfo=info)
    return path.read_bytes()


def _fake_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    row = f"5\t1\t1\t1\t1\t1\t10\t10\t35\t10\t97\t{NAME.split()[0]}\n"
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: HEADER + row)


def _sweep(root: Path, extra_text: str = "") -> list[str]:
    """Every canary found in any byte of any file under `root` or in `extra_text`."""
    hits = []
    blobs = [p.read_bytes() for p in root.rglob("*") if p.is_file()]
    for canary in CANARIES:
        needles = (canary.encode("utf-8"), canary.encode("utf-16-le"))
        if any(n in b for b in blobs for n in needles) or canary in extra_text:
            hits.append(canary)
    return hits


def _evidence(tmp_path: Path, **over: object) -> LeakEvidence:
    fields: dict[str, object] = {
        "project_slug": "demo", "run_dir": tmp_path / "run", "finding_id": "leak-1",
        "rows": ROWS, "id_field": "id", "url": URL}
    return stage.collect_leak_evidence(**{**fields, **over})  # type: ignore[arg-type]


def _finding(ev: LeakEvidence) -> MultiRoleFinding:
    return MultiRoleFinding(
        finding_id="leak-1", finding_class=FindingClass.DATA_LEAK,
        title="Parent sees foreign rows", role="Parent", platform_id="parent",
        url_template=ev.url_template, count=ev.foreign_row_count,
        steps=["login as Parent", "goto /students/{id}", "click Next page"], leak_evidence=ev)


def test_evidence_is_count_headers_five_hashed_ids_and_a_template(tmp_path: Path) -> None:
    ev = _evidence(tmp_path)
    key = stage.project_key("demo")
    assert ev.foreign_row_count == 7
    assert ev.field_names == ["id", "Student name", "Email", "Phone"]  # headers, not values
    assert ev.hashed_ids == [hmac.new(key, r.encode(), sha256).hexdigest() for r in RAW_IDS[:5]]
    assert ev.url_template == "https://a.example.test/students/{id}?page={value}&q={value}"
    assert set(LeakEvidence.model_fields) == {
        "foreign_row_count", "field_names", "hashed_ids", "ids_withheld_reason", "screenshot_path",
        "screenshot_withheld_reason", "url_template"}


def test_ids_are_keyed_per_project_and_missing_key_withholds_them(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = _evidence(tmp_path, project_slug="other").hashed_ids
    assert other and other != _evidence(tmp_path).hashed_ids
    assert _evidence(tmp_path).hashed_ids == _evidence(tmp_path).hashed_ids
    monkeypatch.delenv(KEY_ENV)
    bare = _evidence(tmp_path)
    assert bare.hashed_ids == [] and bare.ids_withheld_reason == "key_missing"
    assert bare.foreign_row_count == 7  # the count survives; no raw id replaces the hashes


def test_model_refuses_more_than_five_ids_or_value_shaped_text() -> None:
    base: dict[str, object] = {"foreign_row_count": 1, "field_names": ["Name"],
                               "url_template": "/students/{id}"}
    with pytest.raises(ValidationError):
        LeakEvidence(**{**base, "hashed_ids": ["a" * 64] * 6})
    with pytest.raises(ValidationError):
        LeakEvidence(**{**base, "hashed_ids": ["STU-123"]})
    for bad in (EMAIL, PHONE, "Name: Zorblax <a@b.co>"):
        with pytest.raises(ValidationError):
            LeakEvidence(**{**base, "field_names": [bad]})
    for bad in ("/students/90210", "/p?email=a%40b.co", "/x/550e8400-e29b-41d4-a716-446655440000",
                "https://u:pw@a.example.test/x", "/students/{id}#frag"):
        with pytest.raises(ValidationError):
            LeakEvidence(**{**base, "url_template": bad})
    with pytest.raises(ValidationError):
        LeakEvidence(**{**base, "stray": 1})


def test_screenshot_is_masked_before_it_is_written(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_ocr(monkeypatch)
    raw = _png(tmp_path / "raw.png")
    ev = _evidence(tmp_path, screenshot_png=raw)
    stored = tmp_path / "run" / "leak" / "leak-1.png"
    assert ev.screenshot_path == "leak/leak-1.png" and stored.is_file()
    with Image.open(stored) as shown:
        assert shown.convert("RGB").getpixel((12, 14)) == (0, 0, 0)  # the text band is blacked out
        assert "note" not in getattr(shown, "text", {})  # metadata stripped
    assert stored.read_bytes() != raw
    assert not any(raw in p.read_bytes() for p in (tmp_path / "run").rglob("*") if p.is_file())


def test_unmaskable_screenshot_is_withheld_never_written_raw(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(privacy.shutil, "which", lambda name: None)
    ev = _evidence(tmp_path, screenshot_png=_png(tmp_path / "raw.png"))
    assert ev.screenshot_path is None and ev.screenshot_withheld_reason == "local_ocr_unavailable"
    assert not list((tmp_path / "run").rglob("*.png"))


def test_canary_sweep_over_run_dir_log_and_prompts(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    _fake_ocr(monkeypatch)
    run_dir = tmp_path / "run"
    ev = _evidence(tmp_path, screenshot_png=_png(tmp_path / "raw.png"))
    with caplog.at_level(logging.DEBUG):
        written = stage.write_finding(run_dir, _finding(ev))
    prompts = [f"Summarise for the report: {written.read_text(encoding='utf-8')}",
               f"Judge this: {_finding(ev).model_dump_json()}"]
    assert written.is_file() and caplog.text
    assert _sweep(run_dir, caplog.text + "\n".join(prompts)) == []


def test_the_sweep_is_not_vacuous(tmp_path: Path) -> None:
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / "leak.txt").write_text(f"row {NAME} {EMAIL}", encoding="utf-8")
    (tmp_path / "run" / "wide.bin").write_bytes(PHONE.encode("utf-16-le"))
    assert {NAME, EMAIL, PHONE, "zorblax"} <= set(_sweep(tmp_path / "run"))
    assert _sweep(tmp_path / "run", f"prompt {RAW_IDS[0]}") .count(RAW_IDS[0]) == 1


def test_finding_round_trips_through_disk_with_its_repro(tmp_path: Path) -> None:
    ev = _evidence(tmp_path)
    written = stage.write_finding(tmp_path / "run", _finding(ev))
    back = MultiRoleFinding.model_validate_json(written.read_text(encoding="utf-8"))
    assert (back.role, back.platform_id, back.url_template, back.count) == (
        "Parent", "parent", ev.url_template, 7)
    assert [parse_repro_step(s)[0] for s in back.steps] == [
        ReproVerb.LOGIN, ReproVerb.GOTO, ReproVerb.CLICK]


def test_finding_refuses_a_repro_that_cannot_be_replayed_or_leaks() -> None:
    ev = LeakEvidence(foreign_row_count=3, field_names=["Name"], url_template="/students/{id}")
    base: dict[str, object] = {
        "finding_id": "leak-9", "finding_class": FindingClass.DATA_LEAK, "title": "t",
        "role": "Parent", "platform_id": "parent", "url_template": "/students/{id}", "count": 3,
        "steps": ["login as Parent"], "leak_evidence": ev}
    MultiRoleFinding(**base)
    for over in ({"steps": []}, {"steps": ["dance wildly"]}, {"steps": [f"fill Email = {EMAIL}"]},
                 {"leak_evidence": None}, {"count": 4}, {"title": f"leak of {EMAIL}"},
                 {"role": ""}, {"platform_id": "Not Valid"}, {"stray": 1}):
        with pytest.raises(ValidationError):
            MultiRoleFinding(**{**base, **over})
