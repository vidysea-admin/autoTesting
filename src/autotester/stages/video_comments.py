"""Timestamped comments on a video, and promoting one to a pointer (TP2, TP6).

One job: validate and store a comment (second, text, author from the session), and turn a
comment into a pointer line the review's own parser (`stages/video_pointers.py`) accepts. The
text is stored exactly as given and is escaped wherever it is shown (the views do that). A
promoted comment keeps its row; promoting again changes nothing.
"""

from __future__ import annotations

import math
import re
import sqlite3
from datetime import UTC, datetime

from autotester.auth import db
from autotester.schema.video_share import MAX_COMMENT_CHARS, MIN_COMMENT_CHARS, VideoComment
from autotester.stages.video_access import clean_email
from autotester.stages.video_pointers import MAX_POINTER_NOTE_CHARS, parse_pointers


class CommentError(ValueError):
    """The comment was refused; the message is the sentence the page shows."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def parse_at_s(raw: object, duration_s: float | None) -> float:
    """The second a comment is pinned to: a finite number in [0, duration]. Without a known
    duration only the lower bound and finiteness apply."""
    try:
        if isinstance(raw, bool):
            raise TypeError
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        raise CommentError("the time must be a number of seconds") from None
    if not math.isfinite(value) or value < 0:
        raise CommentError("the time must be zero or more seconds")
    if duration_s is not None and value > duration_s:
        raise CommentError(f"the time is past the end of the video ({duration_s:g} seconds)")
    return value


def clean_text(raw: object) -> str:
    text = str(raw or "").strip()
    if not MIN_COMMENT_CHARS <= len(text) <= MAX_COMMENT_CHARS:
        raise CommentError(f"a comment is {MIN_COMMENT_CHARS} to {MAX_COMMENT_CHARS} characters")
    return text


def _row(row: sqlite3.Row) -> VideoComment:
    return VideoComment(id=row["id"], slug=row["slug"], video_id=row["video_id"],
                        author=row["author"], at_s=row["at_s"], text=row["text"],
                        created_at=row["created_at"], edited_at=row["edited_at"],
                        pointer_line=row["pointer_line"])


def add_comment(slug: str, video_id: str, author: str, at_s: float, text: str) -> VideoComment:
    with db.transaction() as conn:
        new_id = conn.execute(
            "INSERT INTO video_comments (slug, video_id, author, at_s, text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (slug, video_id, clean_email(author), at_s, text, _now())).lastrowid
        row = conn.execute("SELECT * FROM video_comments WHERE id = ?", (new_id,)).fetchone()
    return _row(row)


def list_comments(slug: str, video_id: str) -> list[VideoComment]:
    """Oldest second first, then oldest comment first."""
    if not db.store_exists():
        return []
    with db.reading() as conn:
        return [_row(r) for r in conn.execute(
            "SELECT * FROM video_comments WHERE slug = ? AND video_id = ? ORDER BY at_s, id",
            (slug, video_id))]


def get_comment(slug: str, video_id: str, comment_id: int) -> VideoComment | None:
    """A comment of THIS video only: an id from another video is not found."""
    if not db.store_exists():
        return None
    with db.reading() as conn:
        row = conn.execute("SELECT * FROM video_comments WHERE id = ? AND slug = ? AND "
                           "video_id = ?", (comment_id, slug, video_id)).fetchone()
    return None if row is None else _row(row)


def edit_comment(comment_id: int, text: str) -> VideoComment | None:
    """Replace the text and stamp `edited_at` (the marker the page shows)."""
    with db.transaction() as conn:
        conn.execute("UPDATE video_comments SET text = ?, edited_at = ? WHERE id = ?",
                     (text, _now(), comment_id))
        row = conn.execute("SELECT * FROM video_comments WHERE id = ?", (comment_id,)).fetchone()
    return None if row is None else _row(row)


def delete_comment(comment_id: int) -> None:
    with db.transaction() as conn:
        conn.execute("DELETE FROM video_comments WHERE id = ?", (comment_id,))


def _clock(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def pointer_line(at_s: float, text: str, duration_s: float | None) -> str:
    """The pointer line for a comment, in the format `parse_pointers` accepts, checked by that
    same parser. Falls back, never drops: a note too long is cut to the note limit; a time the
    parser refuses (at or past the end) becomes a free-text pointer."""
    note = re.sub(r"\s+", " ", text).strip()
    limit = math.inf if duration_s is None else duration_s
    clock = _clock(int(at_s))
    for candidate in (f"{clock} | {note}",
                      f"{clock} | {note[:MAX_POINTER_NOTE_CHARS - 1]}…"):
        if not parse_pointers(candidate, limit).errors:
            return candidate
    free = note[:MAX_POINTER_NOTE_CHARS]
    if parse_pointers(free, limit).errors:  # text that looks like a time: label it, keep it
        free = f"note: {free}"[:MAX_POINTER_NOTE_CHARS]
    return free


def promote(comment_id: int, line: str) -> VideoComment | None:
    """Record the pointer line once (a second promotion is a no-op); the comment stays."""
    with db.transaction() as conn:
        conn.execute("UPDATE video_comments SET pointer_line = ? WHERE id = ? AND "
                     "pointer_line IS NULL", (line, comment_id))
        row = conn.execute("SELECT * FROM video_comments WHERE id = ?", (comment_id,)).fetchone()
    return None if row is None else _row(row)


def pointer_text(slug: str, video_id: str) -> str:
    """Every promoted pointer of a video, one per line: the text the review takes as pointers."""
    return "\n".join(c.pointer_line for c in list_comments(slug, video_id) if c.pointer_line)
