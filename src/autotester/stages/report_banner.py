"""The release-blocking banner and the repro sections it links to (MP8, A3).

One job: build the HTML for the top-of-report banner. With any P0 leak or privilege finding it
returns a banner naming how many there are and linking each finding's repro; with none it returns
an empty string, so no banner renders. `stages/unified_report_render.py` calls it first. Every value
is HTML-escaped. The repro sections carry role, platform, URL template, the ordered steps and the
count (MP10) and nothing from the leaked data.
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.stages.finding_priority import is_release_blocking

BANNER_STYLE = (
    "<style>.rb{background:#7f1d1d;color:#fff;border:3px solid #450a0a;padding:.75rem 1rem;"
    "margin:0 0 1rem}.rb a{color:#fff;text-decoration:underline}.rb h2{margin:0 0 .25rem}"
    "</style>")


def _e(value: object) -> str:
    return escape(str(value))


def _blocking(findings: Sequence[MultiRoleFinding]) -> list[MultiRoleFinding]:
    return [f for f in findings if is_release_blocking(f)]


def render_banner(findings: Sequence[MultiRoleFinding]) -> str:
    """The banner for the P0 findings in `findings`, or "" when there are none."""
    blocking = _blocking(findings)
    if not blocking:
        return ""
    noun = "finding" if len(blocking) == 1 else "findings"
    items = "".join(
        f'<li><a href="#repro-{_e(f.finding_id)}">{_e(f.title)}</a> '
        f"({_e(f.finding_class.value.replace('_', ' '))}, {_e(f.role)} on {_e(f.platform_id)})</li>"
        for f in blocking)
    return (f'<div id="release-blocker" class="rb" role="alert"><h2>Release blocked: '
            f"{len(blocking)} release-blocking {noun}</h2>"
            f"<p>Do not ship this build until each one is fixed. Repro for each:</p>"
            f"<ul>{items}</ul></div>")


def render_repros(findings: Sequence[MultiRoleFinding]) -> str:
    """One section per P0 finding that the banner links to; "" when there are none."""
    sections = []
    for f in _blocking(findings):
        steps = "".join(f"<li>{_e(step)}</li>" for step in f.steps)
        sections.append(
            f'<section id="repro-{_e(f.finding_id)}"><h2>Repro: {_e(f.title)}</h2>'
            f"<p>Role <b>{_e(f.role)}</b> on platform <b>{_e(f.platform_id)}</b> at "
            f"<code>{_e(f.url_template)}</code>. Foreign rows seen: <b>{_e(f.count)}</b>. "
            f"The leaked data itself is deliberately not stored.</p><ol>{steps}</ol></section>")
    return "".join(sections)
