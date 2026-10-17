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
