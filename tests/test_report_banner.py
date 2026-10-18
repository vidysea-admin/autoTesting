"""T-209 (multi-role-platform.md MP8): the release-blocking banner is the report's first block.

With any P0 leak or privilege finding the rendered report opens with the banner (count plus a link
to each finding's repro); with none there is no banner at all. Position is asserted, not presence.
"""

from __future__ import annotations

import re

from autotester.schema.leak_evidence import LeakEvidence
from autotester.schema.multi_role_enums import FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.unified_report import (
    ApiSection,
    CoverageSection,
    HistorySection,
    RegressionSection,
    UnifiedReport,
    WorkflowSection,
)
from autotester.stages.report_banner import render_banner, render_repros
from autotester.stages.unified_report_render import render_html


def _report() -> UnifiedReport:
    gone = {"unavailable": "fixture"}
    return UnifiedReport(
        project="demo", run_id="run_1", regression=RegressionSection(**gone),
        api=ApiSection(**gone), workflows=WorkflowSection(**gone),
        history=HistorySection(**gone), coverage=CoverageSection(**gone))


def _finding(fid: str, cls: FindingClass, **over: object) -> MultiRoleFinding:
    fields: dict[str, object] = {
        "finding_id": fid, "finding_class": cls, "title": f"Title of {fid}", "role": "Parent",
        "platform_id": "parent", "url_template": "/students/{id}",
        "steps": ["login as Parent", "goto /students/{id}"], "count": 3}
    if cls is FindingClass.DATA_LEAK:
        fields["leak_evidence"] = LeakEvidence(
            foreign_row_count=3, field_names=["Name"], url_template="/students/{id}")
    return MultiRoleFinding(**{**fields, **over})


LEAK = _finding("leak-1", FindingClass.DATA_LEAK)
PRIV = _finding("priv-1", FindingClass.PRIVILEGE_ESCALATION, count=1)
P1 = _finding("copy-1", FindingClass.COPY_OR_BRANDING)
_HEAD = re.compile(
    r"^(<!doctype html>|<html[^>]*>|<meta[^>]*>|<title>.*?</title>|<style>.*?</style>)",
    re.S | re.I)


def _first_block(html: str) -> str:
    """What follows the document head furniture: the first thing a reader sees."""
    rest = html
    while (m := _HEAD.match(rest)):
        rest = rest[m.end():]
    return rest


def test_banner_is_the_first_block_when_a_p0_exists() -> None:
    html = render_html(_report(), [LEAK, PRIV, P1])
    assert _first_block(html).startswith('<div id="release-blocker"')
    assert html.index('id="release-blocker"') < html.index("<h1>")
    assert html.count('id="release-blocker"') == 1


def test_banner_names_the_count_and_links_every_p0_repro_only() -> None:
    html = render_html(_report(), [LEAK, PRIV, P1])
    banner = html[html.index('id="release-blocker"'):html.index("<h1>")]
    assert "2 release-blocking" in banner
    for f in (LEAK, PRIV):
        assert f'href="#repro-{f.finding_id}"' in banner
        assert f'id="repro-{f.finding_id}"' in html  # the link resolves inside the file
    assert "copy-1" not in banner and "Title of copy-1" not in banner


def test_repro_section_carries_role_platform_template_steps_and_count() -> None:
    repro = render_repros([LEAK])
    for needle in ("Parent", "parent", "/students/{id}", "login as Parent",
                   "goto /students/{id}", "3"):
        assert needle in repro
    assert repro.index("login as Parent") < repro.index("goto /students/{id}")  # ordered


def test_no_banner_without_a_p0_leak_or_privilege_finding() -> None:
    plain = render_html(_report())
    for findings in ([], [P1], [_finding("x-1", FindingClass.LINK_FAILURE)]):
        html = render_html(_report(), findings)
        assert "release-blocker" not in html and "release-blocking" not in html
        assert html == plain
    assert render_banner([P1]) == "" and render_banner([]) == ""


def test_banner_text_is_escaped() -> None:
    nasty = _finding("leak-x", FindingClass.DATA_LEAK, title="<script>alert(1)</script> leak")
    html = render_html(_report(), [nasty])
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
