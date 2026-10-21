"""AT-1363: the sanitizer re-OCRs its own output; readable text is masked or the image withheld.

Synthetic images only. A stub OCR plays the engine: pass 1 reads some words, later passes read
the words pass 1 missed. One test uses the real local Tesseract when it is provisioned.
"""

import pytest
from PIL import Image, ImageDraw, ImageFont

from autotester.core import image_privacy as privacy

HEADER = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
          "left\ttop\twidth\theight\tconf\ttext\n")
BLACK, WHITE = (0, 0, 0), (255, 255, 255)


def _row(line, text, top, left=10, width=60, height=14, conf=97):
    return f"5\t1\t1\t1\t{line}\t1\t{left}\t{top}\t{width}\t{height}\t{conf}\t{text}\n"


def _passes(*per_pass):
    """An OCR stub returning one TSV per call (the last repeats); `calls` counts the runs."""
    calls = []
    def ocr(path):
        calls.append(path)
        return HEADER + "".join(per_pass[min(len(calls), len(per_pass)) - 1])
    ocr.calls = calls
    return ocr


@pytest.fixture
def wide(tmp_path):
    path = tmp_path / "wide.png"
    Image.new("RGB", (400, 200), "white").save(path)
    return path


def _sanitize(path):
    with privacy.sanitized_images([path]) as batch:
        kept = []
        for safe in batch.paths:
            with Image.open(safe) as image:
                kept.append(image.convert("RGB"))
        return batch, kept


def test_c1_words_missed_on_pass_one_are_masked_after_re_ocr(wide, monkeypatch):
    ocr = _passes([_row(1, "Password", 10)], [_row(1, "hunterTwo", 80)], [])
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert len(kept) == 1 and batch.withheld == 0, batch.reasons
    assert kept[0].getpixel((200, 16)) == BLACK      # pass 1 band
    assert kept[0].getpixel((200, 86)) == BLACK      # the word only pass 2 read
    assert kept[0].getpixel((200, 160)) == WHITE
    assert len(ocr.calls) == 3                       # mask, re-mask, verified clean


def test_c1_the_re_ocr_reads_the_sanitized_pixels_not_the_original(wide, monkeypatch):
    seen = []
    def ocr(path):
        with Image.open(path) as image:
            seen.append(image.convert("RGB").getpixel((200, 16)))
        return HEADER + (_row(1, "Password", 10) if len(seen) == 1 else "")
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert len(kept) == 1, batch.reasons
    assert seen == [WHITE, BLACK]


def test_c1_text_that_surfaces_on_each_of_two_re_reads_is_masked_and_the_third_read_is_clean(
        wide, monkeypatch):
    ocr = _passes([_row(1, "a", 10)], [_row(1, "b", 60)], [_row(1, "c", 110)], [])
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert len(kept) == 1 and batch.withheld == 0, batch.reasons
    assert [kept[0].getpixel((200, y)) for y in (16, 66, 116)] == [BLACK] * 3
    assert len(ocr.calls) == 4


def test_c1_a_clean_image_is_kept_after_one_verifying_re_ocr(wide, monkeypatch):
    ocr = _passes([_row(1, "Dashboard", 10)], [])
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert len(kept) == 1 and batch.withheld == 0 and not batch.incomplete
    assert len(ocr.calls) == 2


def test_c1_a_box_the_re_ocr_reports_inside_the_black_mask_is_not_readable(wide, monkeypatch):
    ocr = _passes([_row(1, "Password", 10)])         # every pass reports the same, now black, word
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert len(kept) == 1 and batch.withheld == 0, batch.reasons
    assert len(ocr.calls) == 2


def test_c1_text_the_re_ocr_keeps_finding_every_pass_is_withheld_after_the_last(wide, monkeypatch):
    ocr = _passes([_row(1, "a", 10)], [_row(1, "b", 50)], [_row(1, "c", 90)], [_row(1, "d", 130)],
                  [_row(1, "e", 170)])
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert kept == [] and batch.withheld == 1 and batch.reasons == ["text_remains_after_mask"]
    assert len(ocr.calls) == 1 + privacy.MAX_REOCR_PASSES      # bounded, never open-ended


def test_c1_the_third_re_mask_is_not_trusted_without_a_clean_read(wide, monkeypatch):
    ocr = _passes([_row(1, "a", 10)], [_row(1, "b", 50)], [_row(1, "c", 90)], [_row(1, "d", 130)])
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert kept == [] and batch.reasons == ["text_remains_after_mask"]


def test_c2_cumulative_mask_over_the_limit_is_withheld_on_a_later_pass(wide, monkeypatch):
    monkeypatch.setattr(privacy, "MAX_MASK_FRACTION", 0.2)
    ocr = _passes([_row(1, "a", 10)], [_row(1, "b", 100)], [])
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert kept == [] and batch.reasons == ["mask_exceeds_limit"]


def test_c2_each_pass_alone_under_the_limit_is_kept(wide, monkeypatch):
    monkeypatch.setattr(privacy, "MAX_MASK_FRACTION", 0.2)
    ocr = _passes([_row(1, "a", 10)], [])
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert len(kept) == 1 and batch.withheld == 0


def test_c2_a_re_ocr_failure_withholds_without_disclosure(wide, monkeypatch):
    calls = []
    def ocr(path):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("tesseract crashed on C:/private/secret.png")
        return HEADER + _row(1, "x", 10)
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    batch, kept = _sanitize(wide)
    assert kept == [] and batch.reasons == ["sanitation_failed"]


def test_c2_a_re_ocr_with_unusable_geometry_withholds(wide, monkeypatch):
    bad = _row(1, "x", 10, left=380, width=100)
    monkeypatch.setattr(privacy, "_local_ocr", _passes([_row(1, "a", 10)], [bad]))
    batch, kept = _sanitize(wide)
    assert kept == [] and batch.reasons == ["invalid_ocr_geometry"]


def test_c3_real_tesseract_reread_of_the_sanitized_screenshot_finds_no_word(tmp_path):
    try:
        privacy._find_tesseract()
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 26)
        small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
    except (privacy.ImagePrivacyError, OSError):
        pytest.skip("local Tesseract or font is not provisioned")
    path = tmp_path / "private.png"
    image = Image.new("RGB", (900, 260), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 20), "Password hunterTwo", font=font, fill="black")
    draw.text((30, 90), "Contact person@example.org", font=font, fill=(90, 90, 90))
    draw.text((30, 160), "small print about the student record", font=small, fill=(120, 120, 120))
    image.save(path)
    with privacy.sanitized_images([path]) as batch:
        if batch.paths:
            reread = privacy._local_ocr(batch.paths[0])
            words = [row.split("\t")[11].strip() for row in reread.splitlines()[1:]
                     if row.startswith("5\t") and len(row.split("\t")) > 11]
            assert [w for w in words if w] == []
        else:
            assert batch.reasons and batch.reasons[0] in {
                "text_remains_after_mask", "mask_exceeds_limit"}
