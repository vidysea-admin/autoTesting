"""Split a recording into overlapping chunks a vision model can actually read.

Pure planning here; the encode is `encode_chunks`, which shells out to ffmpeg.
Kept apart because the plan is the part with the interesting edge cases and it
must be testable without a video file or a binary on PATH.

Why overlap at all: a chunk boundary lands mid-action about as often as not, and
a model that sees only the second half of a click reports a screen appearing
from nowhere. The overlap gives the next chunk enough lead-in to recognise what
it walked in on; `stages/adjudicate.py` then drops what it sees twice (A4).
"""

from __future__ import annotations

import subprocess
import time
from math import isfinite
from pathlib import Path

from autotester.schema.media import MediaChunk

DEFAULT_CHUNK_S = 180.0
DEFAULT_OVERLAP_S = 15.0
CHUNK_TIMEOUT_S = 900.0
"""Per-chunk ceiling on the ffmpeg cut (AT-639).

`media/frames.py` bounds a single-still grab at 60s and
`media/transcribe.py` bounds whisper at 3600s; this call was the one
unbounded shell-out of the three, so a wedged ffmpeg hung `prepare`
forever and no health signal said a word. 900s is deliberately generous
-- a 180s chunk re-encoded at `-preset veryfast` finishes in seconds on
any machine that can run the browser, so this bound only ever fires on a
hang, never on slow-but-working work."""

TOTAL_TIMEOUT_S = 1800.0
"""Wall-clock ceiling on the WHOLE `encode_chunks` loop (ISS-at639-1).

`CHUNK_TIMEOUT_S` bounds one cut, but a 40 minute recording plans ~13 chunks,
so a systemically sick ffmpeg (full disk, driver fault) whose every cut ends
just under the per-chunk bound still held INGEST for ~N x 900s. Past this the
loop raises `subprocess.TimeoutExpired`, which `media_prep.prepare` already
turns into UnreadableRecording. Each cut gets `min(CHUNK_TIMEOUT_S, remaining)`
so the last one cannot overshoot the ceiling either."""

MIN_TAIL_S = 10.0
"""A tail shorter than this is folded into the previous chunk rather than sent
on its own: a 4-second clip costs a whole model call to say almost nothing.

**Reachable only when `overlap_s < MIN_TAIL_S`.** The loop breaks on the first
offset whose remainder fits in one chunk, and that remainder is always in
`(overlap_s, chunk_s]` — so at the DEFAULTS (overlap 15 > min tail 10) a runt
tail cannot arise at all. Recorded because a test written at the defaults
appears to exercise this branch and does not: the plan is identical with the
fold disabled, which is how it was found (an INCONCLUSIVE sabotage under C7).
The branch still earns its place — `encode_chunks` is called with a smaller
overlap for short recordings, where the case is real."""


def plan_chunks(duration_s: float, *, chunk_s: float = DEFAULT_CHUNK_S,
                overlap_s: float = DEFAULT_OVERLAP_S,
                min_tail_s: float = MIN_TAIL_S) -> list[tuple[float, float]]:
    """`(offset, length)` pairs covering `duration_s`, overlapping by `overlap_s`.

    Pure. Every downstream timestamp is shifted by its chunk's offset in code
    (`adjudicate.shift`), never by the model, so this function's output is the
    only thing that decides where a reported second actually lands."""
    # Validate BEFORE the short-circuits. Checking after them meant an absurd
    # chunk size was accepted whenever the recording happened to be shorter
    # than it -- the guard only fired on inputs that were already fine.
    if chunk_s <= 0 or not isfinite(chunk_s):
        raise ValueError(f"chunk {chunk_s}s must be a positive, finite number of seconds")
    if overlap_s < 0:
        # AT-167: a negative overlap makes step LONGER than a chunk, so the
        # plan skips stretches of the recording entirely — a gap nothing
        # downstream reports, because a screen no model watched leaves no trace.
        raise ValueError(f"overlap {overlap_s}s cannot be negative — it would skip footage")
    if overlap_s >= chunk_s:
        raise ValueError(f"overlap {overlap_s}s must be shorter than chunk {chunk_s}s")
    if not isfinite(duration_s):
        raise ValueError("duration must be finite")

    if duration_s <= 0:
        return []
    if duration_s <= chunk_s:
        return [(0.0, duration_s)]

    step = chunk_s - overlap_s
    plan: list[tuple[float, float]] = []
    offset = 0.0
    while offset < duration_s:
        remaining = duration_s - offset
        if remaining <= chunk_s:
            if remaining < min_tail_s and plan:
                # Fold the runt into its predecessor rather than spend a call on it.
                prev_offset, _ = plan[-1]
                plan[-1] = (prev_offset, duration_s - prev_offset)
            else:
                plan.append((offset, remaining))
            break
        plan.append((offset, chunk_s))
        offset += step
    return plan


def chunk_name(index: int, offset_s: float) -> str:
    """Sortable and self-describing: the offset is in the filename because a
    chunk that loses its plan is otherwise an anonymous clip."""
    return f"chunk_{index:02d}_{int(offset_s)}s.mp4"


def encode_chunks(source: Path, out_dir: Path,
                  plan: list[tuple[float, float]]) -> list[MediaChunk]:
    """Cut `source` into `plan`'s pieces with ffmpeg. Accurate-seek re-encode.

    `-ss` goes after `-i`. **My original justification for that was wrong**
    (AT-168): I asserted that placing it before makes ffmpeg seek to the nearest
    keyframe and shift the cut by seconds. A checker measured it on ffmpeg
    8.1.1 and both orders produced a byte-identical frame with keyframes 4.27s
    apart. The order stays because it is the conservative one across builds and
    costs nothing here — not because the failure I described happens on this
    ffmpeg. The property that actually matters is measured, not argued: a cut
    lands where the plan says, because every timestamp downstream is relative
    to a chunk offset.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks: list[MediaChunk] = []
    started = time.monotonic()
    for index, (offset_s, length_s) in enumerate(plan):
        path = out_dir / chunk_name(index, offset_s)
        remaining = TOTAL_TIMEOUT_S - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(["ffmpeg", str(source)], TOTAL_TIMEOUT_S)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(source), "-ss", f"{offset_s}", "-t", f"{length_s}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                 "-c:a", "aac", str(path)],
                check=True, capture_output=True,
                timeout=min(CHUNK_TIMEOUT_S, remaining),
            )
        except (OSError, subprocess.SubprocessError):
            # AT-165's lesson, applied here: a timeout kills ffmpeg MID-WRITE,
            # so the chunk on disk is a truncated clip that looks like a real
            # one. Delete it, then re-raise -- `stages/media_prep.prepare`
            # owns the degradation (AT-166: it turns any failure here into
            # UnreadableRecording and writes no media.json, because a partial
            # chunk set reads as a complete plan).
            path.unlink(missing_ok=True)
            raise
        chunks.append(MediaChunk(index=index, offset_s=offset_s, length_s=length_s,
                                 path=str(path)))
    return chunks
