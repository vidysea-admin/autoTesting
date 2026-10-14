"""Draws a `UnifiedReport` as ONE self-contained HTML file (T-168, DC1-DC3).

One job — presentation. It formats values the loaders already copied from their owners and
computes none of its own: no totals, percentages or tallies, because a figure drawn here would
have no owner and no test (DC2; a test greps this file for the arithmetic builtins). A section
with no input says `Unavailable: <reason>`; a crawl that did not finish is drawn amber with its
gaps listed, never green (DC1); a release with no trusted baseline makes no regression claim.
"""

from __future__ import annotations

from html import escape

from autotester.schema.unified_report import (
    ApiSection,
    CaseLine,
    CoverageSection,
    HistorySection,
    RegressionSection,
    RevisionLine,
    UnifiedReport,
    WorkflowSection,
)

_STYLE = """<style>
:root{--fg:#1f2937;--bg:#fff;--line:#d1d5db;--ok:#166534;--bad:#b91c1c;--warn:#92400e;
--warnbg:#fef3c7}
@media(prefers-color-scheme:dark){:root{--fg:#e5e7eb;--bg:#111827;--line:#374151;--ok:#86efac;
--bad:#fca5a5;--warn:#fcd34d;--warnbg:#451a03}}
body{font:15px/1.5 system-ui,sans-serif;color:var(--fg);background:var(--bg);max-width:70rem;
margin:0 auto;padding:1rem 16px}
section{border-top:2px solid var(--line);margin-top:1.5rem;padding-top:.5rem}
table{border-collapse:collapse;width:100%}td,th{border:1px solid var(--line);padding:.3rem .5rem;
text-align:left;vertical-align:top;overflow-wrap:anywhere}
.warn{background:var(--warnbg);color:var(--warn);padding:.5rem .75rem;border-radius:4px}
.ok{color:var(--ok)}.bad{color:var(--bad)}.muted{opacity:.75}
</style>"""

_TONE = {"PASS": "ok", "passed": "ok", "FAIL": "bad", "failed": "bad", "errored": "bad"}


def _e(value: object) -> str:
    return escape("" if value is None else str(value))


def _table(head: list[str], rows: list[list[str]]) -> str:
    cells = "".join(f"<th>{_e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><tr>{cells}</tr>{body}</table>"


def _unavailable(reason: str) -> str:
    return f"<p class='warn'>Unavailable: {_e(reason)}</p>"


def _listed(label: str, items: list[str]) -> str:
    return f"<p><b>{_e(label)}:</b> {_e(', '.join(items) or 'none')}</p>"


def _regression(sec: RegressionSection) -> str:
    if sec.unavailable:
        return _unavailable(sec.unavailable)
    diff, out = sec.diff, []
    if not sec.finished:
        out.append("<p class='warn'>This release is not finished: its results are partial.</p>")
    if sec.flagged_bad:
        out.append(f"<p class='warn'>Flagged bad: {_e(sec.flagged_reason)}</p>")
    out.append(f"<p>Release <code>{_e(sec.release_run_id)}</code> · build "
               f"<code>{_e(sec.git_sha or 'not recorded')}</code></p>")
    if diff.baseline_run_id is None:
        out.append(f"<p class='warn'>No trusted baseline, so no regression claim is made. "
                   f"{_e(diff.note)}</p>")
    else:
        out.append(f"<p>Baseline <code>{_e(diff.baseline_run_id)}</code> "
                   f"(rule <code>{_e(diff.baseline_rule)}</code>)</p>")
        out += [_listed("Regressed (passed in the baseline, not now)", diff.regressed),
                _listed("Fixed", diff.fixed), _listed("New cases (no baseline counterpart)",
                                                      diff.new_cases)]
    flows = [[_e(f.flow_id), f"<span class='{_TONE.get(f.status, '')}'>"
              f"{_e(f.status.replace('_', ' '))}</span>", _e(', '.join(f.case_ids) or '-')]
             for f in sec.flows]
    issues = [[_e(i.flow_id), _e(i.case_id or '-'), _e(i.kind.replace('_', ' ')), _e(i.detail)]
              for i in sec.issues]
    out.append("<h3>Flows</h3>" + _table(["Flow", "Status", "Cases"], flows))
    out.append("<h3>Issues (the release's single log)</h3>"
               + (_table(["Flow", "Case", "Kind", "Detail"], issues) if issues else "<p>none</p>"))
    return "".join(out)


def _api(sec: ApiSection) -> str:
    if sec.unavailable:
        return _unavailable(sec.unavailable)
    read = _e("; ".join(sec.sources_read))
    if not sec.failures:
        return f"<p>No failing first-party response in the evidence read ({read}).</p>"
    rows = [[_e(f.source), _e(f.method or "-"), _e(f.url or f.raw),
             _e(f.status if f.status is not None else "unreadable")] for f in sec.failures]
    return (f"<p class='muted'>Evidence read: {read}</p>"
            + _table(["Source", "Method", "URL", "Status"], rows))


def _case(line: CaseLine) -> str:
    tone = _TONE.get(line.result, "")
    head = (f"<h3>{_e(line.title)} <code>{_e(line.case_id)}</code> "
            f"<span class='{tone}'>{_e(line.result)}</span></h3>"
            f"<p class='muted'>flow {_e(line.flow_id or 'unknown')} · executor outcome "
            f"{_e(line.outcome or 'none')} {_e(line.scoreboard)}"
            f"{' · ' + _e(line.provenance) if line.provenance else ''}</p>")
    why = f"<p class='warn'>{_e(line.reason)}</p>" if line.reason else ""
    fails = "".join(
        f"<li><b>{_e(f.criterion_id)}</b>: {_e(f.reason)}"
        + (f" (fix: {_e(f.fix_hint)})" if f.fix_hint else "") + "</li>" for f in line.failures)
    steps = "".join(f"<li>{_e(s)}</li>" for s in line.repro_steps)
    return (head + why + (f"<ul>{fails}</ul>" if fails else "")
            + (f"<p>Repro steps:</p><ul>{steps}</ul>" if steps else ""))


def _workflows(sec: WorkflowSection) -> str:
    if sec.unavailable:
        return _unavailable(sec.unavailable)
    return "".join(_case(c) for c in sec.cases)


def _revision(line: RevisionLine) -> str:
    rev, counts = line.revision, line.counts
    shown = " · ".join(f"{_e(k.replace('_', ' '))} {_e(n)}" for k, n in counts.items())
    out = [f"<h3>{_e(rev.at)}</h3><p>{_e(rev.summary)}</p><p>{shown}</p>"]
    if counts["missing_unjudged"]:
        out.append("<p class='warn'>Incomplete diff: these stored screens were not judged (a "
                   "bound or skipped screen kept the crawl from seeing them); they are NOT "
                   f"reported as missing: {_e(', '.join(rev.missing_unjudged))}</p>")
    for label, keys in (("New", rev.new_screens), ("Changed", rev.changed_screens),
                        ("Missing", rev.missing_screens), ("Broken", rev.broken_screens)):
        out.append(_listed(label, keys) if keys else "")
    return "".join(out)


def _history(sec: HistorySection) -> str:
    return _unavailable(sec.unavailable) if sec.unavailable else "".join(
        _revision(r) for r in sec.revisions)


def _coverage(sec: CoverageSection) -> str:
    if sec.unavailable:
        return _unavailable(sec.unavailable)
    out = [f"<p>Crawl <code>{_e(sec.crawl_id)}</code> (the same figures as the crawl page)</p>"]
    if sec.incomplete:
        out.append("<p class='warn'>Incomplete: this crawl did not exercise the whole product. "
                   "Every gap is listed by reason below; none of them counts as covered.</p>")
    out.append(_table(["Item", "Value"], [[_e(k), _e(v)] for k, v in sec.rows]))
    out.append("<h3>Not exercised</h3>" + (
        _table(["Reason", "What"], [[_e(r), _e(w)] for r, w in sec.unreached])
        if sec.unreached else "<p>none recorded</p>"))
    return "".join(out)


def render_html(report: UnifiedReport) -> str:
    """The whole report as one HTML document (no scripts, no external assets)."""
    parts = (("regression", "1. Regression against the last trusted release",
              _regression(report.regression)),
             ("api", "2. API failures (first-party responses)", _api(report.api)),
             ("workflows", "3. Workflows and cases", _workflows(report.workflows)),
             ("history", "4. Change history", _history(report.history)),
             ("coverage", "Crawl coverage", _coverage(report.coverage)))
    body = "".join(f'<section id="{k}"><h2>{_e(t)}</h2>{h}</section>' for k, t, h in parts)
    return (f"<!doctype html><html lang='en'><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Damage-control report - {_e(report.project)}</title>{_STYLE}"
            f"<h1>Damage-control report: {_e(report.project)}</h1>"
            f"<p>Run <code>{_e(report.run_id)}</code>. Built from stored evidence only; nothing "
            f"here is recomputed, and anything missing says so.</p>{body}</html>")
