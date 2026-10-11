"""Parse a reviewer's pointer file into typed lines and a whole error list (TV1).

One job: text in, `PointerParse` out. Nothing is clamped, reordered or skipped, so
`len(parsed) + len(errors) == non_blank_lines` for every input. The frame plan that
consumes these lines is `stages/video_review_plan.py`.
"""

from __future__ import annotations

import re

from autotester.schema.video_pointer import PointerError, PointerLine, PointerParse

MAX_FREE_POINTERS = 3
"""A reviewer may leave at most three free-text pointers per review (R32)."""
MAX_POINTER_LINES = 100
"""Most non-blank pointer lines per review (P5: a chosen limit; the contract names none)."""
MAX_POINTER_NOTE_CHARS = 500
"""Longest note (or free-text pointer) in characters. It is prompt text, so it is bounded (P5)."""
MAX_POINTER_FILE_BYTES = 32768
"""Largest pointer file in bytes (32 KiB); a bigger one is refused unread (P5)."""
BASE_FRAMES_PER_MIN = 4
"""Base depth: frames per minute analysed outside any pointer window (TV2)."""
POINTER_FRAMES_PER_MIN = 12
"""Pointer depth, a whole multiple of base depth so the denser grid contains the base grid."""

_TIME = r"(?:(\d{1,2}):)?(\d{1,3}):(\d{1,2})"
_TIME_RE = re.compile(rf"^(~)?{_TIME}(?:-{_TIME})?$")
_TIMEISH_RE = re.compile(r"^[~-]*\d+:")
_NEG_RE = re.compile(r"^-\s*\d")
_LINE_SPLIT_RE = re.compile(r"\r\n|\r|\n")


def _seconds(h: str | None, m: str, s: str) -> tuple[float | None, str]:
    """(seconds, '') or (None, reason). `H:MM:SS` needs minutes < 60; seconds are always < 60."""
    if int(s) >= 60:
        return None, f"seconds must be 0-59, got {int(s)} in the time"
    if h is not None and int(m) >= 60:
        return None, f"minutes must be 0-59 once hours are given, got {int(m)}"
    return float((int(h) * 60 + int(m)) * 60 + int(s)) if h else float(int(m) * 60 + int(s)), ""


def _time_part(head: str, duration_s: float) -> tuple[PointerLine | None, str]:
    """A time head (`~12:30`, `1:02:03`, `12:30-14:00`) -> line (line_no unset) or a reason."""
    if _NEG_RE.match(head):
        return None, "negative time is not allowed"
    m = _TIME_RE.match(head)
    if m is None:
        return None, "unparsable time; use 12:30, 1:02:03, ~12:30 or 12:30-14:00"
    start, why = _seconds(m.group(2), m.group(3), m.group(4))
    if start is None:
        return None, why
    end: float | None = None
    if m.group(6) is not None:
        end, why = _seconds(m.group(5), m.group(6), m.group(7))
        if end is None:
            return None, why
        if end <= start:
            return None, f"reversed or empty range: end {end:g}s is not after start {start:g}s"
        if end > duration_s:
            return None, f"window ends at {end:g}s, past the recording duration {duration_s:g}s"
    if start >= duration_s:
        return None, f"time {start:g}s is at or past the recording duration {duration_s:g}s"
    kind = "window" if end is not None else "time"
    return PointerLine(line_no=1, kind=kind, start_s=start, end_s=end,
                       approx=m.group(1) is not None), ""


def _parse_line(raw: str, duration_s: float) -> tuple[PointerLine | None, str]:
    head, sep, note = raw.partition("|")
    head, note = head.strip(), note.strip()
    if sep:
        line, why = _time_part(head, duration_s)
        if line is None:
            return None, why
        return line.model_copy(update={"text": note or None}), ""
    if _TIME_RE.match(head) or _NEG_RE.match(head):
        return _time_part(head, duration_s)
    if _TIMEISH_RE.match(head):
        return None, "unparsable: text after a time needs a '|' between them"
    return PointerLine(line_no=1, kind="free", text=head), ""


def oversize_parse(size: int) -> PointerParse:
    """The one-error parse for a pointer file over `MAX_POINTER_FILE_BYTES` (counted as 1 line)."""
    why = f"pointer file is {size} bytes, over the {MAX_POINTER_FILE_BYTES} byte limit"
    return PointerParse(non_blank_lines=1, errors=[PointerError(line_no=1, reason=why)])


def parse_pointers(text: str, duration_s: float) -> PointerParse:
    """Parse every non-blank line of `text` against a recording of `duration_s` seconds.

    Accepts a BOM, `\r\n`/`\r`/`\n` endings and surrounding whitespace. Line numbers are
    1-based physical lines (blank lines count). A fourth free pointer, a line past
    `MAX_POINTER_LINES`, a note over `MAX_POINTER_NOTE_CHARS` and a file over
    `MAX_POINTER_FILE_BYTES` are errors, never truncated."""
    size = len(text) if len(text) > MAX_POINTER_FILE_BYTES else len(text.encode("utf-8"))
    if size > MAX_POINTER_FILE_BYTES:
        return oversize_parse(size)
    out = PointerParse()
    free_seen = 0
    for no, raw in enumerate(_LINE_SPLIT_RE.split(text.lstrip("﻿")), start=1):
        if not raw.strip():
            continue
        out.non_blank_lines += 1
        if out.non_blank_lines > MAX_POINTER_LINES:
            out.errors.append(PointerError(
                line_no=no, reason=f"too many pointer lines (max {MAX_POINTER_LINES})"))
            continue
        line, why = _parse_line(raw.strip(), duration_s)
        if line is not None and line.text and len(line.text) > MAX_POINTER_NOTE_CHARS:
            line, why = None, f"note is {len(line.text)} characters (max {MAX_POINTER_NOTE_CHARS})"
        if line is not None and line.kind == "free":
            free_seen += 1
            if free_seen > MAX_FREE_POINTERS:
                line, why = None, f"too many free-text pointers (max {MAX_FREE_POINTERS})"
        if line is None:
            out.errors.append(PointerError(line_no=no, reason=why))
        else:
            out.parsed.append(line.model_copy(update={"line_no": no}))
    return out


def canonical_pointers(parse: PointerParse) -> list[list[object]]:
    """Order- and line-number-independent form of the parsed lines, for the review id (TV10).

    Sorted, so reordering a file does not change the id; any change of time, window,
    approx flag or note does."""
    rows = [[p.kind, p.start_s, p.end_s, p.approx, p.text or ""] for p in parse.parsed]
    return sorted(rows, key=lambda r: (str(r[0]), r[1] or -1.0, r[2] or -1.0, str(r[3]), r[4]))
