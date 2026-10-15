"""Withhold uncertain images or mask all locally recognized text before external delivery.

This deliberately preserves layout rather than readable labels: OCR cannot reliably classify
an arbitrary credential or configured field. No OCR text, paths, or exceptions are logged.
The local engine is Tesseract; missing engines, empty/uncertain recognition, invalid geometry,
or oversized inputs fail closed. This is heuristic OCR, not proof of absence of personal data
in faces, artwork or unrecognized glyphs. Original evidence is never overwritten.
"""

from __future__ import annotations

import csv
import hashlib
import io
import shutil
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from autotester.schema.image_privacy import ImageSanitation

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_OCR_BYTES = 4 * 1024 * 1024
OCR_TIMEOUT_S = 20
MIN_CONFIDENCE = 85.0
_SAFE_COPIES: dict[Path, str] = {}
_SAFE_LOCK = threading.Lock()


class ImagePrivacyError(ValueError):
    """An image cannot safely be delivered; messages contain only fixed reason codes."""


def _local_ocr(path: Path) -> str:
    executable = shutil.which("tesseract")
    if executable is None:
        raise ImagePrivacyError("local_ocr_unavailable")
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
    boxes = []
    lines: dict[tuple[str, ...], list[tuple[int, int, int, int]]] = {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
        if row.get("level") != "5" or not row.get("text", "").strip():
            continue
        confidence = float(row["conf"])
        if not MIN_CONFIDENCE <= confidence <= 100:
            raise ImagePrivacyError("uncertain_ocr")
        x, y, width, height = [int(row[k]) for k in ("left", "top", "width", "height")]
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x+width > size[0] or y+height > size[1]:
            raise ImagePrivacyError("invalid_ocr_geometry")
        key = tuple(row[k] for k in ("page_num", "block_num", "par_num", "line_num"))
        lines.setdefault(key, []).append((x, y, x+width, y+height))
    for words in lines.values():
        # Cover the entire horizontal band, including omitted tokens and field values.
        top, bottom = min(w[1] for w in words), max(w[3] for w in words)
        boxes.append((0, max(0, top-4), size[0], min(size[1], bottom+4)))
    if not boxes:
        raise ImagePrivacyError("no_recognized_text")
    return boxes


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
