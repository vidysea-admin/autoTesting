"""Real local OCR acceptance and deterministic engine failure boundaries."""

import os
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from pydantic import ValidationError

from autotester.core import image_privacy as privacy
from autotester.schema.image_privacy import ImageSanitation


def test_real_local_ocr_masks_credential_contact_and_configured_field(tmp_path):
    try:
        privacy._find_tesseract()
    except privacy.ImagePrivacyError:
        pytest.skip("local Tesseract runtime is not provisioned")
    path = tmp_path / "private.png"
    image = Image.new("RGB", (1600, 220), "white")
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
    draw = ImageDraw.Draw(image)
    lines = ["Password hunterTwo", "Contact person@example.org", "Custom field privateValue"]
    for index, text in enumerate(lines):
        draw.text((30, 20 + index*60), text, font=font, fill="black")
    image.save(path)
    original = path.read_bytes()
    with privacy.sanitized_images([path]) as batch:
        assert len(batch.paths) == 1, batch.reasons
        assert batch.text_unavailable
        with Image.open(batch.paths[0]) as safe:
            for top in (28, 88, 148):
                assert safe.getpixel((1590, top)) == (0, 0, 0)
            assert safe.getpixel((1590, 210)) == (255, 255, 255)
    assert path.read_bytes() == original


@pytest.mark.parametrize("case,reason", [
    ("pixels", "image_pixel_limit"), ("animated", "animated_image")])
def test_image_format_limits_withhold(tmp_path, monkeypatch, case, reason):
    path = tmp_path / "private.png"
    image = Image.new("RGB", (100, 60), "white")
    if case == "pixels":
        image.save(path)
        monkeypatch.setattr(privacy, "MAX_IMAGE_PIXELS", 1)
    else:
        other = Image.new("RGB", (100, 60), "black")
        image.save(path, format="GIF", save_all=True, append_images=[other])
    monkeypatch.setattr(privacy, "_text_boxes", lambda tsv, size: [(0, 0, 100, 20)])
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: "")
    with privacy.sanitized_images([path]) as batch:
        assert batch.paths == [] and batch.reasons == [reason]


def test_engine_timeout_and_arguments_are_bounded(tmp_path, monkeypatch):
    path = tmp_path / "private.png"
    Image.new("RGB", (100, 60), "white").save(path)
    monkeypatch.setattr(privacy.shutil, "which", lambda _: "tesseract")
    calls = []
    def timeout(command, **kwargs):
        calls.append((command, kwargs))
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])
    monkeypatch.setattr(privacy.subprocess, "run", timeout)
    with privacy.sanitized_images([path]) as batch:
        assert batch.paths == [] and batch.reasons == ["sanitation_failed"]
    assert calls[0][0][-1] == "tsv"
    assert calls[0][1]["timeout"] == 20
    assert calls[0][1]["check"] is True
    assert calls[0][1]["stderr"] is subprocess.DEVNULL


def test_ocr_output_size_limit_before_read(tmp_path, monkeypatch):
    path = tmp_path / "private.png"
    Image.new("RGB", (100, 60), "white").save(path)
    monkeypatch.setattr(privacy.shutil, "which", lambda _: "tesseract")
    monkeypatch.setattr(privacy, "MAX_OCR_BYTES", 1)
    def large_output(command, **kwargs):
        from pathlib import Path
        Path(command[2]).with_suffix(".tsv").write_text("too large", "utf-8")
    monkeypatch.setattr(privacy.subprocess, "run", large_output)
    with privacy.sanitized_images([path]) as batch:
        assert batch.paths == [] and batch.reasons == ["ocr_output_limit"]


def test_sanitation_report_forbids_unknown_fields_and_invalid_counts():
    with pytest.raises(ValidationError):
        ImageSanitation(requested=0, secret_value="forbidden")
    with pytest.raises(ValidationError):
        ImageSanitation(requested=-1)
    with pytest.raises(ValidationError):
        ImageSanitation(requested=1, withheld=-1)


# --- C3: tesseract lookup order: PATH, AUTOTESTER_TESSERACT, standard Windows path ----------

@pytest.fixture
def lookup(monkeypatch, tmp_path):
    """Isolated lookup: every source starts empty; tests switch on one at a time."""
    exes = {name: tmp_path / name / "tesseract.exe" for name in ("env", "dotenv", "win")}
    for exe in exes.values():
        exe.parent.mkdir()
        exe.write_text("", "utf-8")
    monkeypatch.setattr(privacy.shutil, "which", lambda name: None)
    monkeypatch.setattr(privacy, "WINDOWS_TESSERACT", tmp_path / "none" / "tesseract.exe")
    monkeypatch.delenv(privacy.TESSERACT_ENV, raising=False)
    monkeypatch.setattr(privacy, "repo_root", lambda: tmp_path)
    return exes


def test_lookup_prefers_path_over_env_and_windows(lookup, monkeypatch):
    monkeypatch.setattr(privacy.shutil, "which", lambda name: "from-path")
    monkeypatch.setenv(privacy.TESSERACT_ENV, str(lookup["env"]))
    monkeypatch.setattr(privacy, "WINDOWS_TESSERACT", lookup["win"])
    assert privacy._find_tesseract() == "from-path"


def test_lookup_env_beats_windows_and_dotenv(lookup, monkeypatch, tmp_path):
    monkeypatch.setenv(privacy.TESSERACT_ENV, str(lookup["env"]))
    monkeypatch.setattr(privacy, "WINDOWS_TESSERACT", lookup["win"])
    (tmp_path / ".env").write_text(f"{privacy.TESSERACT_ENV}={lookup['dotenv']}\n", "utf-8")
    assert Path(privacy._find_tesseract()) == lookup["env"]


def test_lookup_reads_only_that_key_from_repo_dotenv(lookup, monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        f"OTHER_KEY=do-not-touch\n{privacy.TESSERACT_ENV}={lookup['dotenv']}\n", "utf-8")
    monkeypatch.setattr(privacy, "WINDOWS_TESSERACT", lookup["win"])
    assert Path(privacy._find_tesseract()) == lookup["dotenv"]
    assert "OTHER_KEY" not in os.environ


def test_lookup_falls_back_to_windows_install(lookup, monkeypatch):
    monkeypatch.setattr(privacy, "WINDOWS_TESSERACT", lookup["win"])
    assert Path(privacy._find_tesseract()) == lookup["win"]


def test_lookup_ignores_nonexistent_env_path_then_fails_closed(lookup, monkeypatch, tmp_path):
    monkeypatch.setenv(privacy.TESSERACT_ENV, str(tmp_path / "nowhere" / "tesseract.exe"))
    with pytest.raises(privacy.ImagePrivacyError, match="local_ocr_unavailable"):
        privacy._find_tesseract()


# --- T-136 gate A: a dense post-login dashboard is kept, a mostly-sensitive screen is not ------

_HDR = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
        "left\ttop\twidth\theight\tconf\ttext\n")
DASHBOARD = (1366, 850)  # the Pathlynks run-5 post-login screenshot size (mask fraction 0.621)


def _dense_lines(count: int) -> tuple[str, list[int]]:
    """OCR of `count` stacked text lines (20px tall, 32px pitch): line 1 holds a confident
    secret, line 2 a low-confidence word, the rest are ordinary dashboard text."""
    rows, tops = [], []
    for n in range(1, count + 1):
        top, conf = 20 + (n-1)*32, 30 if n == 2 else 97
        text = "hunterTwo" if n == 1 else f"widget{n}"
        rows.append(f"5\t1\t1\t1\t{n}\t1\t40\t{top}\t120\t20\t{conf}\t{text}\n")
        tops.append(top)
    return _HDR + "".join(rows), tops


def _mask_fraction(tsv: str) -> float:
    boxes = privacy._text_boxes(tsv, DASHBOARD)
    area = Image.new("L", DASHBOARD, 0)
    for box in boxes:
        ImageDraw.Draw(area).rectangle(box, fill=255)
    return area.histogram()[255] / (DASHBOARD[0]*DASHBOARD[1])


def test_dashboard_shaped_screenshot_is_kept_with_every_text_band_masked(tmp_path, monkeypatch):
    tsv, tops = _dense_lines(19)
    assert 0.6 < _mask_fraction(tsv) <= privacy.MAX_MASK_FRACTION  # over the old 0.6 limit
    path = tmp_path / "dashboard.png"
    Image.new("RGB", DASHBOARD, "white").save(path)
    monkeypatch.setattr(privacy, "_local_ocr", lambda _: tsv)
    with privacy.sanitized_images([path]) as batch:
        assert len(batch.paths) == 1 and batch.reasons == [], batch.reasons
        with Image.open(batch.paths[0]) as safe:
            for top in tops:  # the secret line, the low-confidence line and every other band
                assert safe.getpixel((0, top + 10)) == (0, 0, 0)
                assert safe.getpixel((1365, top + 10)) == (0, 0, 0)
                assert safe.getpixel((60, top + 10)) == (0, 0, 0)
            assert safe.getpixel((700, 849)) == (255, 255, 255)  # below the last band: untouched


def test_mostly_sensitive_screenshot_is_still_withheld(tmp_path, monkeypatch):
    tsv, _ = _dense_lines(26)
    assert _mask_fraction(tsv) > privacy.MAX_MASK_FRACTION
    path = tmp_path / "wall-of-text.png"
    Image.new("RGB", DASHBOARD, "white").save(path)
    monkeypatch.setattr(privacy, "_local_ocr", lambda _: tsv)
    with privacy.sanitized_images([path]) as batch:
        assert batch.paths == [] and batch.reasons == ["mask_exceeds_limit"]


# --- AT-1384: the cumulative mask limit is per project (default unchanged) ---------------------

def _pathlynks_limit() -> float:
    import json
    path = Path(__file__).resolve().parents[1] / "projects" / "pathlynks" / "project.json"
    return json.loads(path.read_text(encoding="utf-8"))["image_mask_limit"]


def _sanitize_dense(tmp_path, monkeypatch, lines: int, **kwargs):
    tsv, tops = _dense_lines(lines)
    path = tmp_path / "dashboard.png"
    Image.new("RGB", DASHBOARD, "white").save(path)
    monkeypatch.setattr(privacy, "_local_ocr", lambda _: tsv)
    with privacy.sanitized_images([path], **kwargs) as batch:
        masked = None
        if batch.paths:
            with Image.open(batch.paths[0]) as safe:
                masked = [safe.getpixel((x, top + 10)) for top in tops for x in (0, 60, 1365)]
        return batch.reasons, masked, _mask_fraction(tsv)


def test_pathlynks_dense_dashboard_is_kept_at_its_project_limit_with_every_band_masked(
    tmp_path, monkeypatch,
) -> None:
    limit = _pathlynks_limit()
    reasons, masked, fraction = _sanitize_dense(tmp_path, monkeypatch, 24, mask_limit=limit)
    assert privacy.MAX_MASK_FRACTION < fraction <= limit  # withheld by default, within Pathlynks'
    assert reasons == [] and masked is not None
    assert set(masked) == {(0, 0, 0)}  # the secret line, the low-confidence line, all the rest


def test_the_default_limit_still_withholds_that_dashboard(tmp_path, monkeypatch) -> None:
    reasons, masked, _ = _sanitize_dense(tmp_path, monkeypatch, 24)
    assert reasons == ["mask_exceeds_limit"] and masked is None


def test_a_mostly_sensitive_image_is_still_withheld_at_the_project_limit(
    tmp_path, monkeypatch,
) -> None:
    reasons, masked, fraction = _sanitize_dense(tmp_path, monkeypatch, 26,
                                                mask_limit=_pathlynks_limit())
    assert fraction > _pathlynks_limit()
    assert reasons == ["mask_exceeds_limit"] and masked is None


@pytest.mark.parametrize("limit", [0, -0.1, 0.95, 1.0, float("nan")])
def test_a_nonsense_mask_limit_fails_closed(tmp_path, monkeypatch, limit) -> None:
    reasons, masked, _ = _sanitize_dense(tmp_path, monkeypatch, 5, mask_limit=limit)
    assert reasons == ["invalid_mask_limit"] and masked is None
