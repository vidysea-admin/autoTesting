"""One job: render a run's preflight warnings as a card for the run report page."""

from __future__ import annotations

from html import escape


def warnings_card(warnings: list[str] | None) -> str:
    if not warnings:
        return ""
    items = "".join(f"<li>{escape(w)}</li>" for w in warnings)
    return (f"<div class='card preflight-warnings'><h3>Preflight warnings ({len(warnings)})</h3>"
            f"<p>Warnings only: every case below still ran.</p><ul>{items}</ul></div>")
