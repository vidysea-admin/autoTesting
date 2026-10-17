"""Pixel-level and fail-closed tests of local image sanitation; no external calls."""

import pytest
from PIL import Image

from autotester.core import image_privacy as privacy

HEADER = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
          "left\ttop\twidth\theight\tconf\ttext\n")


def _tsv(text="person@example.org", confidence=97, left=10, top=10, width=35, height=10):
    return HEADER + f"5\t1\t1\t1\t1\t1\t{left}\t{top}\t{width}\t{height}\t{confidence}\t{text}\n"


@pytest.fixture
def screenshot(tmp_path):
    path = tmp_path / "original.png"
    Image.new("RGB", (100, 60), "white").save(path)
    return path


def test_masked_pixels_no_raw_overwrite_and_cleanup(screenshot, monkeypatch):
    before = screenshot.read_bytes()
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv())
    with privacy.sanitized_images([screenshot]) as batch:
        assert batch.requested == 1 and batch.withheld == 0 and not batch.incomplete
        assert batch.text_unavailable
        target = batch.paths[0]
        with Image.open(target) as image:
            assert image.getpixel((0, 10)) == (0, 0, 0)
            assert image.getpixel((99, 19)) == (0, 0, 0)
            assert image.getpixel((50, 50)) == (255, 255, 255)
        assert screenshot.read_bytes() == before
    assert not target.exists()
    assert not privacy._SAFE_COPIES


@pytest.mark.parametrize("value", ["unclassified-password", "contact@example.org", "9876543210",
                                  "custom private field", "Student name: Ravi Kumar"])
def test_all_text_values_are_covered(screenshot, monkeypatch, value):
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv(value))
    with privacy.sanitized_images([screenshot]) as batch:
        assert len(batch.paths) == 1
        with Image.open(batch.paths[0]) as image:
            assert image.getpixel((20, 15)) == (0, 0, 0)


@pytest.mark.parametrize("tsv", [_tsv(confidence="nan"),
                                  _tsv(confidence=101), _tsv(left=-1), _tsv(width=200),
                                  _tsv(height=0), HEADER, "malformed\ntext\n"])
def test_uncertain_or_invalid_ocr_withheld(screenshot, monkeypatch, tsv):
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: tsv)
    with privacy.sanitized_images([screenshot]) as batch:
        assert batch.paths == [] and batch.withheld == 1 and batch.incomplete
        assert batch.reasons


@pytest.fixture
def no_engine(monkeypatch, tmp_path):
    """No tesseract anywhere: not on PATH, no env path, no standard install, empty repo .env."""
    monkeypatch.setattr(privacy.shutil, "which", lambda name: None)
    monkeypatch.setattr(privacy, "WINDOWS_TESSERACT", tmp_path / "absent" / "tesseract.exe")
    monkeypatch.delenv(privacy.TESSERACT_ENV, raising=False)
    monkeypatch.setattr(privacy, "repo_root", lambda: tmp_path)


def test_missing_engine_is_not_silently_text_only(screenshot, no_engine):
    with privacy.sanitized_images([screenshot]) as batch:
        assert batch.paths == []
        assert batch.reasons == ["local_ocr_unavailable"]


def test_errors_do_not_disclose_ocr_or_source(screenshot, monkeypatch):
    def fail(path):
        raise RuntimeError("sensitive-value person@example.org C:/private-file.png")
    monkeypatch.setattr(privacy, "_local_ocr", fail)
    with privacy.sanitized_images([screenshot]) as batch:
        assert batch.reasons == ["sanitation_failed"]


def test_nested_sanitizers_reuse_only_verified_copy(screenshot, monkeypatch):
    calls = []
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: calls.append(path) or _tsv())
    with privacy.sanitized_images([screenshot]) as outer:
        with privacy.sanitized_images(outer.paths) as inner:
            assert inner.paths == outer.paths
            assert len(calls) == 1
        assert outer.paths[0].exists()
        assert privacy._safe_copy(outer.paths[0])
        outer.paths[0].write_bytes(screenshot.read_bytes())
        with privacy.sanitized_images(outer.paths) as changed:
            assert changed.paths != outer.paths
            assert len(calls) == 2


def test_ocr_uses_decoded_snapshot_not_mutable_source(screenshot, monkeypatch):
    def ocr(path):
        assert path != screenshot
        assert path.read_bytes() == screenshot.read_bytes()
        screenshot.write_bytes(b"changed source")
        return _tsv()
    monkeypatch.setattr(privacy, "_local_ocr", ocr)
    with privacy.sanitized_images([screenshot]) as batch:
        assert len(batch.paths) == 1
        with Image.open(batch.paths[0]) as image:
            assert image.getpixel((20, 15)) == (0, 0, 0)


def test_active_safe_copy_still_respects_image_size_limit(screenshot, monkeypatch):
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv())
    with privacy.sanitized_images([screenshot]) as batch:
        monkeypatch.setattr(privacy, "MAX_IMAGE_BYTES", 1)
        with privacy.sanitized_images(batch.paths) as nested:
            assert nested.paths == [] and nested.withheld == 1


def test_missing_and_oversized_images_withheld(screenshot, tmp_path, monkeypatch):
    monkeypatch.setattr(privacy, "MAX_IMAGE_BYTES", 1)
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv())
    with privacy.sanitized_images([screenshot, tmp_path / "missing.png"]) as batch:
        assert batch.paths == [] and batch.withheld == 2
        assert batch.reasons == ["image_unavailable_or_oversized"] * 2


def test_edge_geometry_alpha_and_metadata(screenshot, monkeypatch):
    Image.new("RGBA", (100, 60), (255, 255, 255, 0)).save(screenshot)
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv(left=0, top=0))
    with privacy.sanitized_images([screenshot]) as batch, Image.open(batch.paths[0]) as image:
        assert image.mode == "RGB" and image.info == {}
        assert image.getpixel((99, 0)) == (0, 0, 0)


def test_empty_batch_does_not_need_engine():
    with privacy.sanitized_images(None) as batch:
        assert batch.requested == 0 and batch.paths == [] and not batch.incomplete


def test_context_error_still_cleans_temporary_copies(screenshot, monkeypatch):
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv())
    with pytest.raises(RuntimeError), privacy.sanitized_images([screenshot]) as batch:
        path = batch.paths[0]
        raise RuntimeError("caller failed")
    assert not path.exists() and not privacy._SAFE_COPIES


def test_grade_withholds_unreadable_image_and_cannot_pass(screenshot, no_engine):
    from autotester.providers.mock import MockProvider
    from autotester.schema.enums import EvidenceKind, Outcome, Result
    from autotester.schema.run import Evidence, RawResult
    from autotester.schema.verdict import Criterion, Judgment, Rubric
    from autotester.stages.grade import grade

    class RecordingJudge(MockProvider):
        def judge(self, prompt, schema, images=None, **kwargs):
            assert images == []
            assert "Visual evidence incomplete" in prompt
            return super().judge(prompt, schema, images=images, **kwargs)

    judge = RecordingJudge(responses={"judge": [Judgment(
        result=Result.PASS, scoreboard="1/1", criteria_met=1, criteria_total=1)]})
    result = RawResult(case_id="case-privacy", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.SCREENSHOT, path=screenshot.name)])
    rubric = Rubric(id="rub-privacy", criteria=[Criterion(id="c1", text="Greeting is readable")])
    verdict = grade(rubric, result, "run-privacy", judge, run_dir=screenshot.parent)
    assert verdict.images_requested == 1 and verdict.images_seen == 0
    assert verdict.result is Result.INCONCLUSIVE
    assert "privacy" in verdict.scoreboard and "privacy" in verdict.note


def test_grade_delivers_safe_copy_and_reports_text_unavailable(screenshot, monkeypatch):
    from autotester.providers.mock import MockProvider
    from autotester.schema.enums import EvidenceKind, Outcome, Result
    from autotester.schema.run import Evidence, RawResult
    from autotester.schema.verdict import Criterion, Judgment, Rubric
    from autotester.stages.grade import grade

    class RecordingJudge(MockProvider):
        def judge(self, prompt, schema, images=None, **kwargs):
            assert images and images[0] != screenshot
            with Image.open(images[0]) as image:
                assert image.getpixel((20, 15)) == (0, 0, 0)
            assert "readable screenshot text is unavailable" in prompt
            return super().judge(prompt, schema, images=images, **kwargs)

    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv())
    judge = RecordingJudge(responses={"judge": [Judgment(
        result=Result.PASS, scoreboard="1/1", criteria_met=1, criteria_total=1)]})
    result = RawResult(case_id="case-privacy", outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.SCREENSHOT, path=screenshot.name)])
    rubric = Rubric(id="rub-privacy", criteria=[Criterion(id="c1", text="Greeting is readable")])
    verdict = grade(rubric, result, "run-privacy", judge, run_dir=screenshot.parent)
    assert verdict.images_requested == verdict.images_seen == 1
    assert verdict.result is Result.INCONCLUSIVE and "privacy" in verdict.scoreboard


# --- C1: a low-confidence word is masked, the image is released -----------------------------

def _rows(*words):
    """TSV rows (line_num, text, conf, left, top, width, height) on a 400x120 image."""
    return HEADER + "".join(
        f"5\t1\t1\t1\t{line}\t1\t{left}\t{top}\t{width}\t{height}\t{conf}\t{text}\n"
        for line, text, conf, left, top, width, height in words)


@pytest.fixture
def wide(tmp_path):
    path = tmp_path / "wide.png"
    Image.new("RGB", (400, 120), "white").save(path)
    return path


@pytest.mark.parametrize("confidence", [84, 40, 0, -1])
def test_low_confidence_word_is_masked_and_image_released(screenshot, monkeypatch, confidence):
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv(confidence=confidence))
    with privacy.sanitized_images([screenshot]) as batch:
        assert len(batch.paths) == 1 and batch.withheld == 0 and not batch.incomplete
        with Image.open(batch.paths[0]) as image:
            assert image.getpixel((12, 12)) == (0, 0, 0)
            assert image.getpixel((50, 50)) == (255, 255, 255)


@pytest.mark.parametrize("text", ["faint", ""])
def test_low_confidence_box_is_blacked_next_to_planted_secret(wide, monkeypatch, text):
    # Line 1 is a confident secret; line 2 is a low-confidence word (or unreadable blank).
    tsv = _rows((1, "hunterTwo", 97, 10, 10, 90, 20), (2, text, 30, 10, 80, 60, 20))
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: tsv)
    with privacy.sanitized_images([wide]) as batch:
        assert len(batch.paths) == 1, batch.reasons
        with Image.open(batch.paths[0]) as image:
            assert image.getpixel((40, 20)) == (0, 0, 0)      # secret band
            assert image.getpixel((40, 90)) == (0, 0, 0)      # low-confidence box
            assert image.getpixel((300, 110)) == (255, 255, 255)


def test_no_raw_secret_text_survives_ocr_reread(tmp_path, monkeypatch):
    from PIL import ImageDraw, ImageFont
    try:
        privacy._find_tesseract()
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
    except (privacy.ImagePrivacyError, OSError):
        pytest.skip("local Tesseract or font is not provisioned")
    path = tmp_path / "secret.png"
    image = Image.new("RGB", (900, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 20), "Password hunterTwo", font=font, fill="black")
    draw.text((30, 120), "faint blurry word", font=font, fill=(200, 200, 200))
    image.save(path)
    real = privacy._text_boxes
    def with_low_word(tsv, size):  # real OCR plus one forced low-confidence word on line 2
        return real(tsv + "5\t1\t1\t1\t9\t1\t30\t120\t250\t40\t20\t\n", size)
    monkeypatch.setattr(privacy, "_text_boxes", with_low_word)
    with privacy.sanitized_images([path]) as batch:
        assert len(batch.paths) == 1, batch.reasons
        reread = privacy._local_ocr(batch.paths[0]).lower()
    assert "hunter" not in reread and "password" not in reread and "faint" not in reread


def test_mask_over_sane_fraction_is_withheld(screenshot, monkeypatch):
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: _tsv(confidence=40))
    monkeypatch.setattr(privacy, "MAX_MASK_FRACTION", 0.1)
    with privacy.sanitized_images([screenshot]) as batch:
        assert batch.paths == [] and batch.reasons == ["mask_exceeds_limit"]
    assert 0 < privacy.MAX_MASK_FRACTION <= 1


# --- C2: fail closed is preserved ------------------------------------------------------------

@pytest.mark.parametrize("tsv,reason", [
    (HEADER, "no_recognized_text"), (_rows((1, "", 10, 5, 5, 20, 10)), "no_recognized_text"),
    (_tsv(confidence=101), "uncertain_ocr"), (_tsv(confidence="nan"), "uncertain_ocr"),
    (_tsv(width=200), "invalid_ocr_geometry")])
def test_unusable_ocr_still_withholds_with_fixed_reason(screenshot, monkeypatch, tsv, reason):
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: tsv)
    with privacy.sanitized_images([screenshot]) as batch:
        assert batch.paths == [] and batch.reasons == [reason]


def test_ocr_failure_still_withholds_and_does_not_disclose(screenshot, monkeypatch):
    def fail(path):
        raise OSError("tesseract crashed on C:/private/secret.png")
    monkeypatch.setattr(privacy, "_local_ocr", fail)
    with privacy.sanitized_images([screenshot]) as batch:
        assert batch.paths == [] and batch.withheld == 1 and batch.reasons == ["sanitation_failed"]


def test_token_starting_with_quote_does_not_swallow_following_secret_row(wide, monkeypatch):
    # Tesseract TSV is unquoted: a token like `"hi` must not hide the secret row after it.
    tsv = _rows((1, '"hi', 97, 10, 10, 40, 20), (2, "hunterTwo", 97, 10, 80, 90, 20))
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: tsv)
    with privacy.sanitized_images([wide]) as batch:
        assert len(batch.paths) == 1, batch.reasons
        with Image.open(batch.paths[0]) as image:
            assert image.getpixel((40, 20)) == (0, 0, 0)
            assert image.getpixel((40, 90)) == (0, 0, 0)      # secret row after the quote token
