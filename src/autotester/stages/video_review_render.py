"""Render a stored review as Markdown or HTML with the identical item set (TV10, TV4, TV6).

Pure formatting over `VideoReview.items`: rejected and overflow items are never rendered, narration
state and unreviewed spans are written in plain words, and the system never writes the word
"confirmed" -- only a human's own status is echoed back, labelled as theirs.
"""

from __future__ import annotations

import html

from autotester.schema.video_review import ConfirmItem, VideoReview
from autotester.stages.video_review_prompt import clock

HEAD = ("id", "time", "screen", "seen", "suggestion", "severity", "origin", "status")


def _status(item: ConfirmItem) -> str:
    return "open" if item.status == "open" else f"{item.status} (set by a human)"


def _row(item: ConfirmItem) -> list[str]:
    seen = item.seen
    if item.quote:
        seen += f' -- narrator: "{item.quote}"'
    notes = [n for n in (item.narration_note, item.downgrade) if n]
    if notes:
        seen += f" [{'; '.join(notes)}]"
    return [item.id, clock(item.time_s), item.screen, seen, item.suggestion,
            str(item.severity.value), item.origin, _status(item)]


def _lines(review: VideoReview) -> list[tuple[str, str]]:
    """(label, text) header lines shared by both formats."""
    out = [("Status", review.status + (f" ({review.reason})" if review.reason else "")),
           ("Summary", review.summary or "(none)"),
           ("Narration", review.narration_note), ("Coverage", review.coverage_note)]
    if review.count_note:
        out.append(("Count", review.count_note))
    if review.overflow:
        out.append(("Held back", f"{len(review.overflow)} more item(s) beyond the 5-item limit"))
    return [(k, v) for k, v in out if v]


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(review: VideoReview) -> str:
    out = [f"# Video review {review.id}", ""]
    out += [f"**{k}:** {_cell(v)}" for k, v in _lines(review)]
    out += ["", "| " + " | ".join(HEAD) + " |", "|" + " --- |" * len(HEAD)]
    out += ["| " + " | ".join(_cell(c) for c in _row(i)) + " |" for i in review.items]
    return "\n".join(out) + "\n"


def render_html(review: VideoReview) -> str:
    esc = html.escape
    head = "".join(f"<th>{h}</th>" for h in HEAD)
    cells = ["".join(f"<td>{esc(c)}</td>" for c in _row(i)) for i in review.items]
    rows = "".join(f'<tr data-item-id="{esc(i.id)}">{c}</tr>'
                   for i, c in zip(review.items, cells, strict=True))
    meta = "".join(f"<p><b>{k}:</b> {esc(v)}</p>" for k, v in _lines(review))
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f"<title>Video review {esc(review.id)}</title></head><body>"
            f"<h1>Video review {esc(review.id)}</h1>{meta}"
            f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></body></html>\n")
