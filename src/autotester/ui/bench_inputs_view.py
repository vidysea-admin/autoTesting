"""Markup for the benchmark-input controls: the real / false-positive marks on a finding list
(crawl and run pages) and the benchmark-inputs page (T-136 marks, T-218 answer list).

One job: render. Every interpolated string is escaped. The answer list is never read here: the
page shows its sha256, counts and pin time only, and holds no link that serves the file.
"""

from __future__ import annotations

from html import escape

from autotester.auth.access import authorize, resource_for
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey
from autotester.schema.bench import BenchMarks, Finding
from autotester.schema.ceo_inputs import AtomicListPin
from autotester.stages import bench_marks
from autotester.stages.acceptance_comparison import corpus_id_for
from autotester.stages.bench import findings_from_verdicts
from autotester.stages.crawl_findings import crawl_findings_for
from autotester.store.project_store import ProjectStore
from autotester.ui import theme

_STATUS = {"real": ("real bug", "positive"), "false_positive": ("false positive", "danger")}


def may_mark(slug: str) -> bool:
    """True when the signed-in account may edit this project (the same permission the
    route policy demands for the POST routes)."""
    who = current_principal()
    return who is not None and authorize(who, PermissionKey.PROJECT_EDIT, resource_for(slug))


def _status(finding: Finding) -> str:
    if finding.matched_bug_id is not None:
        return theme.pill("matched to a known bug", "positive")
    text, tone = _STATUS.get(finding.adjudication or "", ("unadjudicated", "neutral"))
    return theme.pill(text, tone)


def _button(slug: str, key: str, verdict: str, label: str, next_path: str, css: str) -> str:
    return (f"<form method='post' action='/projects/{slug}/bench/marks' class='inline-form'>"
            f"<input type='hidden' name='finding' value='{key}'>"
            f"<input type='hidden' name='verdict' value='{verdict}'>"
            f"<input type='hidden' name='next' value='{escape(next_path, quote=True)}'>"
            f"<button type='submit' class='btn btn-sm {css}'>{label}</button></form>")


def _controls(slug: str, key: str, finding: Finding, next_path: str) -> str:
    if finding.matched_bug_id is not None:
        return "<span class='meta'>ruled by the known-bug list</span>"
    if finding.adjudication is not None:
        return _button(slug, key, "clear", "Undo mark", next_path, "")
    return (_button(slug, key, "real", "Mark real bug", next_path, "")
            + _button(slug, key, "false_positive", "Mark false positive", next_path, "btn-danger"))


def findings_card(slug: str, next_path: str, found: list[Finding], marks: BenchMarks,
                  *, may_edit: bool) -> str:
    """The AutoTester findings of this page, each with its ruling and (for an editor) the
    controls to mark it real or false and to undo. No findings: no card."""
    if not found:
        return ""
    safe = escape(slug)
    rows = []
    for finding in bench_marks.marked(found, marks):
        key = bench_marks.finding_key(finding)
        action = (_controls(safe, key, finding, next_path) if may_edit
                  else "<span class='meta'>read-only</span>")
        rows.append(f"<tr><td>{escape(finding.text)}</td><td>{_status(finding)}</td>"
                    f"<td>{action}</td></tr>")
    note = ("" if may_edit else "<p class='meta'>You can see the rulings; marking a finding "
            "needs permission to edit this project.</p>")
    table = ("<table class='data-table'><thead><tr><th>Finding</th><th>Ruling</th>"
             f"<th>Action</th></tr></thead><tbody>{''.join(rows)}</tbody></table>")
    return theme.card(
        "<p class='meta'>Mark each finding real or false. Unmarked findings stay unadjudicated "
        "and are not counted in the false-positive rate.</p>" + note + table,
        title="AutoTester findings: rule on them")


def _pin_card(slug: str, pin: AtomicListPin | None, *, may_edit: bool) -> str:
    if pin is None:
        state = "<p>No answer list is pinned for this project yet.</p>"
    else:
        old = (f"<li>replaced {len(pin.replaced_sha256)} earlier list(s)</li>"
               if pin.replaced_sha256 else "")
        state = (f"<p>Pinned list: <code>{escape(pin.sha256)}</code></p><ul>"
                 f"<li>{pin.items} atomic findings, {pin.bytes} bytes</li>"
                 f"<li>pinned {escape(pin.pinned_at.strftime('%Y-%m-%d %H:%M UTC'))} "
                 f"by {escape(pin.pinned_by)}</li>{old}</ul>")
    if may_edit:
        form = (
            f"<form method='post' action='/projects/{escape(slug)}/bench/atomic-list' "
            "enctype='multipart/form-data'>"
            "<p><label for='atomic-list-file'>Atomic answer list (JSON file)</label><br>"
            "<input id='atomic-list-file' type='file' name='atomic_list' "
            "accept='.json,application/json' required></p>"
            "<button type='submit' class='btn btn-primary'>Upload and pin</button></form>")
    else:
        form = "<p class='meta'>Uploading needs permission to edit this project.</p>"
    hint = ("<p class='meta'>The file is a JSON object <code>{\"items\": [{\"id\", \"priority\", "
            "\"technique\", \"needs_seeded_data\"}]}</code>: ids and categories only, no finding "
            "text. It is stored privately on the server and never shown again; only its sha256 "
            "and counts are.</p>")
    return theme.card(state + hint + form, title="Private benchmark answer list")


def page_body(slug: str, name: str, marks: BenchMarks, pin: AtomicListPin | None,
              *, may_edit: bool) -> str:
    safe = escape(slug)
    real = sum(1 for m in marks.marks.values() if m.verdict == "real")
    false = len(marks.marks) - real
    summary = theme.card(
        "<div class='stat-row'>" + theme.stat(str(real), "ruled real bugs")
        + theme.stat(str(false), "ruled false positives") + "</div>"
        f"<p>Rule on findings from the <a href='/projects/{safe}/crawls'>crawl pages</a> and "
        f"the <a href='/projects/{safe}/report'>run pages</a>. "
        "<code>scripts/check_acceptance_comparison.py</code> computes the false-positive "
        "rate from these rulings.</p>", title="Findings you have ruled")
    crumbs = theme.breadcrumb(("Projects", "/"), (escape(name), f"/projects/{safe}"),
                              ("Benchmark inputs", None))
    return crumbs + "<h1>Benchmark inputs</h1>" + summary + _pin_card(slug, pin, may_edit=may_edit)


def crawl_card(store: ProjectStore, slug: str, crawl_id: str) -> str:
    """The marking card for one crawl's findings (the crawl page)."""
    return findings_card(
        slug, f"/projects/{slug}/crawls/{crawl_id}", crawl_findings_for(store, [crawl_id]),
        bench_marks.load_marks(store, corpus_id_for(slug)), may_edit=may_mark(slug))


def run_card(store: ProjectStore, slug: str, run_id: str) -> str:
    """The marking card for one run's FAIL findings (the run page)."""
    return findings_card(
        slug, f"/projects/{slug}/runs/{run_id}",
        findings_from_verdicts(store.load_verdicts(run_id), {}),
        bench_marks.load_marks(store, corpus_id_for(slug)), may_edit=may_mark(slug))
