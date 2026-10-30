"""AI REPORT: one Excel workbook of a project's stored Track C evidence, grouped by tier (T-155).

Contract: qa/contracts/ai-target.md AI9-AI14, core-invariants C5/C7, report-export.md RE1/RE5.
Presentation over evidence already on disk, like `stages/crawl_report.py`: it reads the check
entries the caller passes, the captures and their stored verdicts under
`projects/<slug>/ai/behavioural/<id>/{capture,verdict}.json`, the adversarial run records and
`ai/adversarial/refusals.jsonl`. It decides nothing, calls no model, opens no connection, and writes
only the one workbook the caller names. A blocked check reads BLOCKED with its reason and action,
an empty tier is shown at 0, and no stored result is said out loud rather than shown as health.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from openpyxl import Workbook

from autotester.core.excel import autosize_columns, clean_cell
from autotester.core.redact import Redactor
from autotester.schema.ai_check import AiCapture
from autotester.schema.ai_probe import ProbeRefusal, ProbeRun
from autotester.schema.catalog import TIER_ORDER, AiCheckEntry, Tier
from autotester.schema.verdict import Verdict
from autotester.stages.ai_capture import CaptureWithheld
from autotester.stages.ai_catalog import CHECK_TIER
from autotester.store.filestore import exists_path, list_children, read_json
from autotester.store.project_store import ProjectStore

NO_RESULTS = "No AI results are stored for this project: nothing below has been run or judged."
COLUMNS = ["Tier", "Check", "Method", "Status", "Criteria", "Grader", "Capture", "Criterion",
           "Reason", "Fix hint", "Note", "Detail"]
_KIND_ORDER = {kind: i for i, kind in enumerate(CHECK_TIER)}


class Stored(NamedTuple):
    """One stored behavioural capture and its verdict, if one was stored. `None` capture means
    the file exists but could not be read."""

    folder: str
    capture: AiCapture | None
    verdict: Verdict | None


def _load(path: Path, model: type[Any]) -> tuple[Any, bool]:
    """(object, unreadable). A missing file is (None, False); a malformed one (None, True)."""
    try:
        return read_json(path, model), False
    except ValueError:
        return None, True


def _stored_captures(ai_dir: Path) -> list[Stored]:
    found: list[Stored] = []
    root = ai_dir / "behavioural"
    for folder in (root / name for name in list_children(root)):
        cap, bad = _load(folder / "capture.json", AiCapture)
        if cap is None and not bad:
            continue
        verdict, _ = _load(folder / "verdict.json", Verdict)
        found.append(Stored(folder.name, cap, verdict))
    return sorted(found, key=lambda s: (s.capture.created_at if s.capture else "", s.folder))


def _grader(verdict: Verdict) -> str:
    return "computed (rule)" if verdict.grader_provider == "rule" else (
        f"judge: {verdict.grader_provider}")


def _entry_row(entry: AiCheckEntry) -> list[str] | None:
    """The row an entry earns by itself: not applicable, blocked, or None when it can run."""
    head = [entry.tier.value, entry.kind.value, entry.method.value]
    if not entry.applicable:
        return [*head, "NOT APPLICABLE", *[""] * 7,
                "this target's kind does not take this check"]
    if not entry.runnable:
        reason = entry.blocked_reason.value if entry.blocked_reason else "unknown"
        return [*head, "BLOCKED", *[""] * 7,
                f"Blocked: {reason}. To clear: {entry.unblock_action}"]
    return None


def _not_run_row(entry: AiCheckEntry) -> list[str]:
    return [entry.tier.value, entry.kind.value, entry.method.value, "NOT RUN", *[""] * 7,
            "runnable, but no stored capture for this check"]


def _result_rows(item: Stored, entry: AiCheckEntry | None) -> list[list[str]]:
    cap = item.capture
    if cap is None:
        return [["", "", "", "UNREADABLE", *[""] * 6, item.folder,
                 "capture.json could not be read"]]
    method = entry.method.value if entry else ""
    head = [CHECK_TIER[cap.check].value, cap.check.value, method]
    where = f"{item.folder}: {cap.endpoint}"
    verdict = item.verdict
    if verdict is None:
        return [[*head, "CAPTURED, NOT JUDGED", "", "", where, "", "", "", "",
                 "a capture is stored but no verdict is"]]
    fails = verdict.failures or [None]
    rows = []
    for i, failure in enumerate(fails):
        rows.append([
            *head, verdict.result.value, verdict.scoreboard, _grader(verdict), where,
            failure.criterion_id if failure else "", failure.reason if failure else "",
            (failure.fix_hint or "") if failure else "", (verdict.note or "") if i == 0 else "",
            ""])
    return rows


def _tier_sheet(tier: Tier, entries: list[AiCheckEntry], stored: list[Stored]) -> list[list[str]]:
    mine = [e for e in entries if e.tier is tier]
    runnable = sum(1 for e in mine if e.runnable)
    by_kind = {e.kind: e for e in mine}
    done = {s.capture.check for s in stored if s.capture and CHECK_TIER[s.capture.check] is tier}
    rows: list[tuple[int, list[str]]] = []
    for entry in mine:
        row = _entry_row(entry) or (None if entry.kind in done else _not_run_row(entry))
        if row:
            rows.append((_KIND_ORDER[entry.kind], row))
    for item in stored:
        if item.capture is None or CHECK_TIER[item.capture.check] is tier:
            order = _KIND_ORDER.get(item.capture.check, 99) if item.capture else 99
            entry = by_kind.get(item.capture.check) if item.capture else None
            rows += [(order, r) for r in _result_rows(item, entry)]
    heading = f"{tier.value} - {runnable} runnable of {len(mine)} checks"
    body = [r for _, r in sorted(rows, key=lambda pair: pair[0])]
    return [[heading], COLUMNS, *body]


def _run_row(run: ProbeRun) -> list[str]:
    errors = sum(1 for r in run.records if r.exchange.error)
    detail = (f"{len(run.records)} probe(s) sent of {run.planned_probes} planned; "
              f"{errors} transport error(s); approval {run.approval_id}")
    if run.cap_hit:
        detail += f"; a bound stopped the run with {run.unsent_probes} probe(s) unsent"
    return ["run", run.run_id, run.endpoint, f"production={run.production}", "NOT JUDGED",
            ", ".join(run.probe_sets), detail]


def _refusal_rows(log: Path) -> list[list[str]]:
    """AD7 rows, plus an honest statement when the log is absent, empty or partly unreadable."""
    head = ["Kind", "Target", "Timestamp", "Requested probes", "Reason"]
    if not log.exists():
        return [head, ["refused attempts",
                       "no refused attempts recorded: refusals.jsonl does not exist"]]
    rows, bad = [], []
    for number, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            r = ProbeRefusal.model_validate_json(line)
        except ValueError:
            bad.append(str(number))
            continue
        rows.append(["refused attempt", r.target, r.timestamp, str(r.requested_probes), r.reason])
    if bad:
        rows.append(["refused attempts", "the refusal log could not be read in full: "
                     f"line(s) {', '.join(bad)} are malformed"])
    elif not rows:
        rows.append(["refused attempts", "no refused attempts recorded: refusals.jsonl is empty"])
    return [head, *rows]


def _adversarial_sheet(entries: list[AiCheckEntry], ai_dir: Path) -> tuple[
        list[list[str]], int]:
    adv = ai_dir / "adversarial"
    runs, rows = [], []
    for run_json in (adv / name / "run.json" for name in list_children(adv)
                     if exists_path(adv / name / "run.json")):
        run, bad = _load(run_json, ProbeRun)
        if run is not None:
            runs.append(run)
            rows.append(_run_row(run))
        elif bad:
            rows.append(["run", run_json.parent.name, "", "", "UNREADABLE", "",
                         "run.json could not be read"])
    mine = [e for e in entries if e.tier is Tier.ADVERSARIAL]
    heading = (f"adversarial - {sum(1 for e in mine if e.runnable)} runnable of {len(mine)} "
               f"checks; {len(rows)} stored run(s)")
    runs_head = ["Kind", "Run", "Endpoint", "Production", "Status", "Probe sets", "Detail"]
    body = rows or [["run", "no adversarial run is stored"]]
    return [[heading], runs_head, *body, [], *_refusal_rows(adv / "refusals.jsonl")], len(rows)


def _summary(project: str, entries: list[AiCheckEntry], stored: list[Stored],
             adv_runs: int) -> list[list[str]]:
    caps = len(stored)
    rows = [["Tier", "Checks", "Runnable", "Blocked", "Not applicable", "Stored results"]]
    for tier in TIER_ORDER:
        mine = [e for e in entries if e.tier is tier]
        if tier is Tier.ADVERSARIAL:
            results = adv_runs
        else:
            results = sum(1 for s in stored if s.capture and CHECK_TIER[s.capture.check] is tier)
        rows.append([tier.value, str(len(mine)), str(sum(1 for e in mine if e.runnable)),
                     str(sum(1 for e in mine if e.applicable and not e.runnable)),
                     str(sum(1 for e in mine if not e.applicable)), str(results)])
    statement = NO_RESULTS if caps + adv_runs == 0 else (
        f"{caps} stored capture(s) and {adv_runs} adversarial run(s).")
    return [[f"AI test report - project {project}"], [statement], [], *rows]


def _write(path: Path, sheets: dict[str, list[list[str]]], redactor: Redactor) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    text: list[str] = []
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            clean = [clean_cell(redactor.scrub(c)) for c in row]
            ws.append(clean)
            text += clean
        autosize_columns(ws)
    try:
        redactor.assert_clean("\n".join(text))
    except ValueError:
        raise CaptureWithheld("a secret survived scrubbing; the report was withheld") from None
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def export_ai_report(store: ProjectStore, out: Path | None = None, *,
                     checks: list[AiCheckEntry], redactor: Redactor) -> Path:
    """Write the workbook at `out` (default `projects/<slug>/ai/ai-report.xlsx`) from stored
    evidence and the caller's check entries."""
    out = out or store.paths.ai_report
    ai_dir = store.paths.ai_dir
    stored = _stored_captures(ai_dir)
    adversarial, adv_runs = _adversarial_sheet(checks, ai_dir)
    sheets = {"Summary": _summary(store.paths.slug, checks, stored, adv_runs)}
    for tier in TIER_ORDER:
        sheets[tier.value] = adversarial if tier is Tier.ADVERSARIAL else _tier_sheet(
            tier, checks, stored)
    _write(out, sheets, redactor)
    return out

