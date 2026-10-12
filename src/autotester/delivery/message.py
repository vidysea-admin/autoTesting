"""Compose the report e-mail from a stored `ReportSummary` and a template file (hosting.md HO28).

One job: turn the summary into a subject and a body. It reads the stored label, it never works
one out (TT7). The wording lives in `templates/report_email.txt`; this module only fills it.
Every filled value was validated by the schema (single line, no path, no query-bearing link) and
the finished text goes through the caller's scrubber, so a planted secret is masked.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from pathlib import Path
from string import Template

from autotester.schema.delivery import RenderedMessage, ReportSummary

TEMPLATE_PATH = Path(__file__).parent / "templates" / "report_email.txt"


def render_message(summary: ReportSummary,
                   scrub: Callable[[str], str] = lambda text: text) -> RenderedMessage:
    """Fill the template. `scrub` is `Redactor.scrub` bound over the `.env` values."""
    values = {
        "project": summary.project_name, "run_id": summary.run_id,
        "finished": summary.finished_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "label": summary.label.value, "passed": summary.counts.passed,
        "failed": summary.counts.failed, "blocked": summary.counts.blocked,
        "inconclusive": summary.counts.inconclusive, "coverage": summary.coverage_line,
        "link": summary.report_url,
    }
    filled = Template(TEMPLATE_PATH.read_text(encoding="utf-8")).substitute(values)
    head, _, body = scrub(filled).partition("\n\n")
    return RenderedMessage(subject=head.removeprefix("Subject: "), body=body.strip() + "\n")
