"""REAL-TARGET ACCEPTANCE DRIVER (T-169 GR1-GR4): approvals, evidence files, human checklist.

One job: wrap `generic_acceptance.run_mode` for a real target. It refuses to start without the
signed approvals the mode needs (`require_project_approval`, so a production project needs a
human-granted `production: true` row, D-088/D-096), runs the mode, then writes per-mode
evidence under `qa/evidence/t169-real/<mode>/` and returns a GR1-GR4 checklist that says what
is filled and what only a human can fill. Nothing is scored or decided here (GR3).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from autotester.browser.secrets import SecretStore
from autotester.core.consent import require_project_approval
from autotester.core.redact import mask_pii_obj
from autotester.schema.acceptance import AcceptanceComparison
from autotester.schema.enums import ApprovalKind, Result
from autotester.stages.generic_acceptance import Mode, ModeResult, ModeSeams, ModeSpec, run_mode
from autotester.store.project_store import ProjectStore

EVIDENCE_DIR = Path("qa") / "evidence" / "t169-real"
REASON_CHARS = 80
CHECKLIST_JOIN = chr(10)
_URL_SECRET = re.compile(
    r"([?&;](?:[\w.-]*(?:token|key|secret|password|passwd|sig|session|auth|code)[\w.-]*)=)"
    r"[^&\s\"'<>]+", re.I)


def _scrub(obj: Any, store: ProjectStore) -> Any:
    """Known secret values -> mask, emails/phones -> masked, URL credential params -> mask."""
    project = store.load_project()
    redactor = (SecretStore.load(project, store.paths.env_file, strict=False).redactor()
                if project is not None else None)
    if redactor is not None:
        obj = redactor.scrub_obj(obj)
    obj = mask_pii_obj(obj)
    return _scrub_urls(obj)


def _scrub_urls(obj: Any) -> Any:
    if isinstance(obj, str):
        return _URL_SECRET.sub(r"[REDACTED]", obj)
    if isinstance(obj, dict):
        return {k: _scrub_urls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_urls(v) for v in obj]
    return obj


def required_kinds(mode: Mode) -> list[ApprovalKind]:
    """url_only crawls the live site (CRAWL); both modes press a UI case run (LIVE_CASE)."""
    return ([ApprovalKind.CRAWL] if mode == "url_only" else []) + [ApprovalKind.LIVE_CASE]


def preflight(store: ProjectStore, mode: Mode) -> list[str]:
    """Check every approval the mode needs BEFORE anything starts; raises `ApprovalRequired`
    (message includes the grant command). Returns the approval ids that cover the run."""
    project = store.load_project()
    if project is None:
        raise ValueError(f"project {store.paths.slug!r} is not onboarded; nothing to approve")
    rows = store.list_approvals()
    return [require_project_approval(rows, project=project, kind=kind,
                                     target=project.base_url).id
            for kind in required_kinds(mode)]


def verdict_counts(store: ProjectStore, run_id: str) -> tuple[dict[str, int], dict[str, int]]:
    """(count per Result, INCONCLUSIVE breakdown by first-failure reason, truncated)."""
    verdicts = store.load_verdicts(run_id)
    counts = {r.value: 0 for r in Result}
    counts.update(Counter(v.result.value for v in verdicts))
    why = Counter((_scrub(v.failures[0].reason, store)[:REASON_CHARS] if v.failures
                   else "no reason recorded") for v in verdicts
                  if v.result is Result.INCONCLUSIVE)
    return counts, dict(why)


def _gr_checklist(mode: Mode, cmp: AcceptanceComparison, problems: list[str],
                  approval_ids: list[str]) -> list[str]:
    """GR1-GR4 lines: `[x]` filled by this run, `[ ]` needs a human (Umesh)."""
    tr = cmp.autotester
    incomplete = f" -- INCOMPLETE: {'; '.join(problems)}" if problems else ""
    return [
        f"[x] GR1 {mode}: ran through the app's routes (approvals {', '.join(approval_ids)}); "
        "[ ] human: confirm the vision, agent and browser seams were real, not mocks",
        f"[{'x' if not problems else ' '}] GR2 {mode}: comparison artifact written "
        f"(FP {tr.false_positive_rate.text()}, time_s {tr.duration_s.text()}, "
        f"recall {tr.severity_weighted_recall.text()}){incomplete}",
        "[ ] GR2 human: branch coverage, adjudicated bugs-found list, and the AT-281 "
        "thresholds (open question Q3, docs/intent.md) -- Umesh sets these",
        "[ ] GR3 human: Umesh's verdict line (AutoTester vs the expert human tester) recorded "
        "as a decision on the comparison artifact -- never computed",
        "[x] GR4: the UI run trigger refuses a production project without a human production "
        "row before any browser launch (tests/test_real_acceptance.py::"
        "test_ui_run_trigger_refuses_production_without_approval; ui/routes_runs.py::"
        "trigger_run -> stages/run_launcher.py::prepare_run -> require_live_case_approval); "
        "the report must still state what the run actually did",
    ]


def write_evidence(store: ProjectStore, result: ModeResult, approval_ids: list[str],
                   evidence_root: Path) -> tuple[Path, list[str]]:
    """Write `<root>/qa/evidence/t169-real/<mode>/{evidence.json,comparison.json,checklist.md}`."""
    out = evidence_root / EVIDENCE_DIR / result.mode
    out.mkdir(parents=True, exist_ok=True)
    counts, inconclusive = verdict_counts(store, result.run_id)
    lines = _gr_checklist(result.mode, result.comparison, result.problems, approval_ids)
    evidence: dict[str, Any] = {
        "project": store.paths.slug, "mode": result.mode, "run_id": result.run_id,
        "approval_ids": approval_ids, "verdict_counts": counts,
        "inconclusive_breakdown": inconclusive, "comparison_problems": result.problems,
        "human_verdict": None,
    }
    evidence = _scrub(evidence, store)
    comparison = _scrub(result.comparison.model_dump(mode="json"), store)
    lines = _scrub(lines, store)
    texts = {"evidence.json": json.dumps(evidence, indent=2),
             "comparison.json": json.dumps(comparison, indent=2),
             "checklist.md": CHECKLIST_JOIN.join(lines) + CHECKLIST_JOIN}
    project = store.load_project()
    if project is not None:  # hard gate before anything touches disk
        redactor = SecretStore.load(project, store.paths.env_file, strict=False).redactor()
        for text in texts.values():
            redactor.assert_clean(text)
    for name, text in texts.items():
        (out / name).write_text(text, encoding="utf-8")
    return out, lines


def drive_real(client: Any, store: ProjectStore, spec: ModeSpec, seams: ModeSeams,
               evidence_root: Path, *, approver: str = "acceptance-reviewer",
               on_preflight: Callable[[list[str]], None] | None = None,
               ) -> tuple[ModeResult, Path, list[str]]:
    """Preflight approvals (refuse without them), `run_mode`, write evidence, return the
    checklist. `spec.onboard` should be False for an already-onboarded real target."""
    approval_ids = preflight(store, spec.mode)
    if on_preflight is not None:
        on_preflight(approval_ids)
    result = run_mode(client, store, spec, seams, approver=approver)
    out, lines = write_evidence(store, result, approval_ids, evidence_root)
    return result, out, lines
