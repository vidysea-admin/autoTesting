"""The Review card on the video page: a Run review form (if allowed) and the latest review.

One job: HTML for the review panel, reusing `stages.video_review_render` for the item rows so the
page, the Markdown and the HTML export show the same set. Everything user-derived is escaped.
"""

from __future__ import annotations

from html import escape as esc

from autotester.schema.video_review import VideoReview
from autotester.stages.video_review_render import BASELINE_NOTE, HEAD, _lines, _row
from autotester.ui import theme


def run_form(base: str) -> str:
    return (f"<form method='post' action='{base}/review'>"
            "<div class='field'><label for='review-pointers'>Pointers (optional)</label>"
            "<textarea id='review-pointers' name='pointers' rows='4' maxlength='20000' "
            "placeholder='1:00 | checkout total (one per line)'></textarea></div>"
            "<p class='meta'>One per line: a second, a window like 3:00-4:00, or ~8:00 for "
            "approximate, with an optional note after a bar. Pointers raise attention; the rest "
            "of the video is still looked at. Frames go to the model only after redaction and "
            "only with a recorded approval.</p>"
            "<button class='btn btn-primary' type='submit'>Run review</button></form>")


def review_body(review: VideoReview) -> str:
    meta = "".join(f"<p><b>{esc(k)}:</b> {esc(v)}</p>" for k, v in _lines(review))
    head = "".join(f"<th>{esc(h)}</th>" for h in HEAD)
    rows = "".join(
        f"<tr data-item-id='{esc(i.id)}'>" + "".join(f"<td>{esc(c)}</td>" for c in _row(i))
        + "</tr>" for i in review.items) or "<tr><td colspan='8'>No items.</td></tr>"
    return (meta + f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
            f"<p class='meta'>{esc(BASELINE_NOTE)}</p>")


def review_panel(base: str, latest: VideoReview | None, *, can_run: bool) -> str:
    body = review_body(latest) if latest else "<p>No review has been run for this video yet.</p>"
    if can_run:
        body += "<h3>Run a review</h3>" + run_form(base)
    return "<div id='review'>" + theme.card(body, title="Review") + "</div>"


def review_refusal_page(back: str, title: str, lines: list[str]) -> str:
    items = "".join(f"<li>{esc(line)}</li>" for line in lines)
    body = (f"<h1>{esc(title)}</h1><ul>{items}</ul>"
            f"<a class='btn' href='{esc(back)}'>Back to the video</a>")
    return theme.page(title, theme.card(body))
