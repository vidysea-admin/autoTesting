"""Mask all locally recognized text before external delivery; withhold when OCR cannot be trusted.

This deliberately preserves layout rather than readable labels: OCR cannot reliably classify
an arbitrary credential or configured field. No OCR text, paths, or exceptions are logged.
The local engine is Tesseract. A low-confidence word is masked, never trusted: its box is
blacked out and the image is still released. The image is withheld (fail closed) when the
engine is missing or fails, recognition is empty, geometry is invalid, or the masked area
exceeds MAX_MASK_FRACTION of the image, or the input is oversized. This is heuristic OCR, not
proof of absence of personal data in faces, artwork or unrecognized glyphs. Original evidence
is never overwritten.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from autotester.core.paths import repo_root
from autotester.schema.image_privacy import ImageSanitation

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_OCR_BYTES = 4 * 1024 * 1024
OCR_TIMEOUT_S = 20
MIN_CONFIDENCE = 85.0
MAX_MASK_FRACTION = 0.6
TESSERACT_ENV = "AUTOTESTER_TESSERACT"
WINDOWS_TESSERACT = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
_SAFE_COPIES: dict[Path, str] = {}
_SAFE_LOCK = threading.Lock()


class ImagePrivacyError(ValueError):
    """An image cannot safely be delivered; messages contain only fixed reason codes."""


def _env_tesseract() -> Path | None:
    """The `AUTOTESTER_TESSERACT` path: process env first, then that one key of the repo `.env`."""
    value = os.environ.get(TESSERACT_ENV)
    if not value:
        try:
            from dotenv import dotenv_values
            value = dotenv_values(repo_root() / ".env").get(TESSERACT_ENV)
        except OSError:
            value = None
    return Path(value) if value else None


def _find_tesseract() -> str:
    """PATH, then AUTOTESTER_TESSERACT, then the standard Windows install; else fail closed."""
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in (_env_tesseract(), WINDOWS_TESSERACT):
        if candidate is not None and candidate.is_file():
            return str(candidate)
    raise ImagePrivacyError("local_ocr_unavailable")


def _local_ocr(path: Path) -> str:
    executable = _find_tesseract()
    # Output to a temporary file: subprocess PIPE would accumulate unbounded OCR output.
    with TemporaryDirectory(prefix="autotester-ocr-") as scratch:
        output = Path(scratch) / "ocr"
        subprocess.run([executable, str(path.resolve()), str(output), "tsv"],
                       check=True, timeout=OCR_TIMEOUT_S, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        tsv = output.with_suffix(".tsv")
        if tsv.stat().st_size > MAX_OCR_BYTES:
            raise ImagePrivacyError("ocr_output_limit")
        return tsv.read_text(encoding="utf-8")


def _text_boxes(tsv: str, size: tuple[int, int]) -> list[tuple[int, int, int, int]]:
    """Boxes to black out: every text line's full band, plus each low-confidence word's box."""
    boxes = []
    lines: dict[tuple[str, ...], list[tuple[int, int, int, int]]] = {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        if row.get("level") != "5":
            continue
        confidence = float(row["conf"])
        if confidence != confidence or confidence > 100:  # NaN or impossible: not a score
            raise ImagePrivacyError("uncertain_ocr")
        blank = not row.get("text", "").strip()
        x, y, width, height = [int(row[k]) for k in ("left", "top", "width", "height")]
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x+width > size[0] or y+height > size[1]:
            if blank:
                continue
            raise ImagePrivacyError("invalid_ocr_geometry")
        box = (x, y, x+width, y+height)
        if confidence < MIN_CONFIDENCE:
            boxes.append(box)  # uncertain stays hidden, even a word OCR could not read
        if blank:
            continue
        key = tuple(row[k] for k in ("page_num", "block_num", "par_num", "line_num"))
        lines.setdefault(key, []).append(box)
    for words in lines.values():
        # Cover the entire horizontal band, including omitted tokens and field values.
        top, bottom = min(w[1] for w in words), max(w[3] for w in words)
        boxes.append((0, max(0, top-4), size[0], min(size[1], bottom+4)))
    if not lines:
        raise ImagePrivacyError("no_recognized_text")
    return boxes


def _check_mask_area(boxes: list[tuple[int, int, int, int]], size: tuple[int, int]) -> None:
    from PIL import Image, ImageDraw

    area = Image.new("L", size, 0)
    drawing = ImageDraw.Draw(area)
    for box in boxes:
        drawing.rectangle(box, fill=255)
    if area.histogram()[255] > MAX_MASK_FRACTION * size[0] * size[1]:
        raise ImagePrivacyError("mask_exceeds_limit")


def _sanitize_one(source: Path, destination: Path) -> None:
    from PIL import Image, ImageDraw

    if not source.is_file() or source.stat().st_size > MAX_IMAGE_BYTES:
        raise ImagePrivacyError("image_unavailable_or_oversized")
    with Image.open(source) as original:
        if original.width * original.height > MAX_IMAGE_PIXELS:
            raise ImagePrivacyError("image_pixel_limit")
        if getattr(original, "n_frames", 1) != 1:
            raise ImagePrivacyError("animated_image")
        image = original.convert("RGB")  # strips alpha; PNG output strips metadata
    # OCR and mask the SAME decoded snapshot, even if source changes concurrently.
    image.save(destination, format="PNG")
    boxes = _text_boxes(_local_ocr(destination), image.size)
    _check_mask_area(boxes, image.size)
    drawing = ImageDraw.Draw(image)
    for box in boxes:
        drawing.rectangle(box, fill="black")
    image.save(destination, format="PNG")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_copy(path: Path) -> bool:
    resolved = path.resolve()
    with _SAFE_LOCK:
        expected = _SAFE_COPIES.get(resolved)
    return (expected is not None and path.is_file() and path.stat().st_size <= MAX_IMAGE_BYTES
            and _digest(path) == expected)


def _prepare_image(source: Path, target: Path) -> Path:
    if _safe_copy(source):
        return source
    _sanitize_one(source, target)
    with _SAFE_LOCK:
        _SAFE_COPIES[target.resolve()] = _digest(target)
    return target


@contextmanager
def sanitized_images(paths: list[Path] | None) -> Iterator[ImageSanitation]:
    """Temporary safe copies and value-free shortfall evidence; deleted after the call.

    All text bands are masked, including credentials/contact/configured fields, so no
    secret values need cross this interface. Missing dependencies and every sanitation
    failure withhold that image. Callers MUST expose incomplete evidence to the user.
    """
    batch = ImageSanitation(requested=len(paths or []))
    with TemporaryDirectory(prefix="autotester-images-") as scratch:
        try:
            for index, source in enumerate(paths or []):
                target = Path(scratch) / f"image-{index}.png"
                try:
                    batch.paths.append(_prepare_image(source, target))
                except Exception as exc:  # never echo paths, OCR or local-engine errors
                    reason = str(exc) if isinstance(exc, ImagePrivacyError) else "sanitation_failed"
                    batch.withheld += 1
                    batch.reasons.append(reason)
            yield batch
        finally:
            with _SAFE_LOCK:
                for target in Path(scratch).glob("*.png"):
                    _SAFE_COPIES.pop(target.resolve(), None)
