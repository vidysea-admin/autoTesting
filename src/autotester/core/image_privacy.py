"""Mask all locally recognized text before external delivery; withhold when OCR cannot be trusted.

This deliberately preserves layout rather than readable labels: OCR cannot reliably classify
an arbitrary credential or configured field. No OCR text, paths, or exceptions are logged.
The local engine is Tesseract. A low-confidence word is masked, never trusted: its box is
blacked out and the image is still released. The image is withheld (fail closed) when the
engine is missing or fails, recognition is empty, geometry is invalid, or the masked area
exceeds MAX_MASK_FRACTION of the image, or the input is oversized. The masked output is then
read again (at most MAX_REOCR_PASSES times): words still readable are masked too, and the image
is withheld if the cumulative mask passes the limit or text is still found after the last pass.
This is heuristic OCR, not
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
from autotester.schema.image_privacy import (
    CEILING_MASK_LIMIT,
    DEFAULT_MASK_LIMIT,
    ImageSanitation,
)

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_OCR_BYTES = 4 * 1024 * 1024
OCR_TIMEOUT_S = 20
MIN_CONFIDENCE = 85.0
# Every recognized text line is masked across the FULL width, so this fraction is text density,
# not leak risk. 0.6 withheld Pathlynks' post-login dashboard (1366x850, measured 0.621, T-136
# run 5); 0.75 keeps such dense dashboards while a screen that is mostly text still withholds.
MAX_MASK_FRACTION = DEFAULT_MASK_LIMIT  # a project may set its own, `Project.image_mask_limit`
# Re-reads of the masked output (AT-1363): words still readable are masked, then read again.
MAX_REOCR_PASSES = 3
TESSERACT_ENV = "AUTOTESTER_TESSERACT"
WINDOWS_TESSERACT = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
_SAFE_COPIES: dict[Path, str] = {}
_SAFE_LOCK = threading.Lock()
Box = tuple[int, int, int, int]


class ImagePrivacyError(ValueError):
    """An image cannot safely be delivered; messages contain only fixed reason codes."""


def _env_tesseract() -> Path | None:
    """The `AUTOTESTER_TESSERACT` path: process env first, then that one key of the repo `.env`."""
    value = os.environ.get(TESSERACT_ENV)
    if not value:
        try:
            from autotester.core.env import read_dotenv
            value = read_dotenv(repo_root() / ".env").get(TESSERACT_ENV)
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


def _words(tsv: str, size: tuple[int, int]) -> Iterator[tuple[Box, float, str, tuple[str, ...]]]:
    """Validated level-5 rows as (box, confidence, text, line key); invalid input fails closed."""
    for row in csv.DictReader(io.StringIO(tsv), delimiter="	", quoting=csv.QUOTE_NONE):
        if row.get("level") != "5":
            continue
        confidence = float(row["conf"])
        if confidence != confidence or confidence > 100:  # NaN or impossible: not a score
            raise ImagePrivacyError("uncertain_ocr")
        text = row.get("text", "").strip()
        x, y, width, height = [int(row[k]) for k in ("left", "top", "width", "height")]
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x+width > size[0] or y+height > size[1]:
            if not text:
                continue
            raise ImagePrivacyError("invalid_ocr_geometry")
        key = tuple(row[k] for k in ("page_num", "block_num", "par_num", "line_num"))
        yield (x, y, x+width, y+height), confidence, text, key


def _line_bands(lines: dict[tuple[str, ...], list[Box]], size: tuple[int, int]) -> list[Box]:
    """Cover each line's entire horizontal band, including omitted tokens and field values."""
    bands = []
    for words in lines.values():
        top, bottom = min(w[1] for w in words), max(w[3] for w in words)
        bands.append((0, max(0, top-4), size[0], min(size[1], bottom+4)))
    return bands


def _text_boxes(tsv: str, size: tuple[int, int]) -> list[Box]:
    """Boxes to black out: every text line's full band, plus each low-confidence word's box."""
    boxes: list[Box] = []
    lines: dict[tuple[str, ...], list[Box]] = {}
    for box, confidence, text, key in _words(tsv, size):
        if confidence < MIN_CONFIDENCE:
            boxes.append(box)  # uncertain stays hidden, even a word OCR could not read
        if text:
            lines.setdefault(key, []).append(box)
    if not lines:
        raise ImagePrivacyError("no_recognized_text")
    return boxes + _line_bands(lines, size)


def _leftover_boxes(tsv: str, image) -> list[Box]:
    """Bands of words the re-read of the masked image still finds; none when it reads nothing.

    A word whose box is entirely black is not readable (OCR noise over the mask), so it is
    ignored; any other recognized word, whatever its confidence, is masked with its line.
    """
    lines: dict[tuple[str, ...], list[Box]] = {}
    boxes: list[Box] = []
    for box, _confidence, text, key in _words(tsv, image.size):
        if text and image.crop(box).convert("L").getextrema()[1] > 0:
            boxes.append(box)
            lines.setdefault(key, []).append(box)
    return boxes + _line_bands(lines, image.size)


def _check_mask_area(boxes: list[Box], size: tuple[int, int], limit: float | None) -> None:
    from PIL import Image, ImageDraw

    limit = MAX_MASK_FRACTION if limit is None else limit
    if not 0 < limit <= CEILING_MASK_LIMIT:  # a nonsense limit fails closed, never open
        raise ImagePrivacyError("invalid_mask_limit")
    area = Image.new("L", size, 0)
    drawing = ImageDraw.Draw(area)
    for box in boxes:
        drawing.rectangle(box, fill=255)
    if area.histogram()[255] > limit * size[0] * size[1]:
        raise ImagePrivacyError("mask_exceeds_limit")


def _mask(image, destination: Path, boxes: list[Box], applied: list[Box],
          limit: float | None) -> None:
    """Black out `boxes`; the cumulative mask over every pass must stay within the limit."""
    from PIL import ImageDraw

    applied.extend(boxes)
    _check_mask_area(applied, image.size, limit)
    drawing = ImageDraw.Draw(image)
    for box in boxes:
        drawing.rectangle(box, fill="black")
    image.save(destination, format="PNG")


def _sanitize_one(source: Path, destination: Path, limit: float | None = None) -> None:
    from PIL import Image

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
    applied: list[Box] = []
    _mask(image, destination, _text_boxes(_local_ocr(destination), image.size), applied, limit)
    for _ in range(MAX_REOCR_PASSES):
        leftover = _leftover_boxes(_local_ocr(destination), image)
        if not leftover:
            return  # the sanitized pixels were read again and nothing readable is left
        _mask(image, destination, leftover, applied, limit)
    raise ImagePrivacyError("text_remains_after_mask")  # the last re-mask was never read back


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_copy(path: Path) -> bool:
    resolved = path.resolve()
    with _SAFE_LOCK:
        expected = _SAFE_COPIES.get(resolved)
    return (expected is not None and path.is_file() and path.stat().st_size <= MAX_IMAGE_BYTES
            and _digest(path) == expected)


def _prepare_image(source: Path, target: Path, limit: float | None = None) -> Path:
    if _safe_copy(source):
        return source
    _sanitize_one(source, target, limit)
    with _SAFE_LOCK:
        _SAFE_COPIES[target.resolve()] = _digest(target)
    return target


@contextmanager
def sanitized_images(paths: list[Path] | None, *,
                     mask_limit: float | None = None) -> Iterator[ImageSanitation]:
    """Temporary safe copies and value-free shortfall evidence; deleted after the call.

    All text bands are masked, including credentials/contact/configured fields, so no
    secret values need cross this interface. Missing dependencies and every sanitation
    failure withhold that image. Callers MUST expose incomplete evidence to the user.
    `mask_limit` is the project's cumulative mask limit (None: the default); every detected
    text band is masked either way, the limit only decides when a mostly-text image is withheld.
    """
    batch = ImageSanitation(requested=len(paths or []))
    with TemporaryDirectory(prefix="autotester-images-") as scratch:
        try:
            for index, source in enumerate(paths or []):
                target = Path(scratch) / f"image-{index}.png"
                try:
                    batch.paths.append(_prepare_image(source, target, mask_limit))
                except Exception as exc:  # never echo paths, OCR or local-engine errors
                    reason = str(exc) if isinstance(exc, ImagePrivacyError) else "sanitation_failed"
                    batch.withheld += 1
                    batch.reasons.append(reason)
            yield batch
        finally:
            with _SAFE_LOCK:
                for target in Path(scratch).glob("*.png"):
                    _SAFE_COPIES.pop(target.resolve(), None)
