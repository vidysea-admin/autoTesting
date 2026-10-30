"""REAL-TARGET ACCEPTANCE DRIVER (T-169 GR1-GR4): approvals, evidence files, human checklist.

One job: wrap `generic_acceptance.run_mode` for a real target. It refuses to start without the
signed approvals the mode needs (`require_project_approval`, so a production project needs a
human-granted `production: true` row, D-088/D-096), runs the mode, then writes per-mode
evidence under `qa/evidence/t169-real/<mode>/` and returns a GR1-GR4 checklist that says what
is filled and what only a human can fill. Nothing is scored or decided here (GR3).
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired, require_project_approval
from autotester.core.redact import mask_pii_obj, scrub_url_credentials_obj
from autotester.schema.acceptance import AcceptanceComparison
from autotester.schema.approval import RunApproval
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import ApprovalKind, Result
from autotester.stages.generic_acceptance import Mode, ModeResult, ModeSeams, ModeSpec, run_mode
from autotester.store.project_store import ProjectStore

EVIDENCE_DIR = Path("qa") / "evidence" / "t169-real"
REASON_CHARS = 80
CHECKLIST_JOIN = chr(10)

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
    return scrub_url_credentials_obj(obj)


def required_kinds(mode: Mode) -> list[ApprovalKind]:
    """url_only crawls the live site (CRAWL); both modes press a UI case run (LIVE_CASE)."""
    return ([ApprovalKind.CRAWL] if mode == "url_only" else []) + [ApprovalKind.LIVE_CASE]


def _newest_first(rows: list[RunApproval]) -> list[RunApproval]:
    """Newest grant first. `require_approval` no longer takes the first covering row: it returns
    the human-granted, then widest, covering row (ties keep this order, so newest wins a tie)."""
    return sorted(rows, key=lambda r: r.granted_at, reverse=True)


def crawl_bounds(store: ProjectStore, max_actions: int | None = None,
                 wall_clock_s: float | None = None) -> CrawlBounds:
    """Crawl bounds that fit the covering approval: min(request or default, approval).

    An explicit request larger than every approval raises `ApprovalRequired` (never clamped
    silently). Among rows that cover the request, the one with the widest wall clock, then the
    newest grant, is used, so a 1800 s run selects the 1800 s row and not an older 600 s one."""
    project = store.load_project()
    if project is None:
        raise ValueError(f"project {store.paths.slug!r} is not onboarded; nothing to approve")
    default = CrawlBounds()
    ask_a, ask_w = max_actions or 0, wall_clock_s or 0.0
    rows = _newest_first(store.list_approvals())
    covering: list[RunApproval] = []
    for row in rows:
        try:
            require_project_approval([row], project=project, kind=ApprovalKind.CRAWL,
                                     target=project.base_url, actions=ask_a, wall_clock_s=ask_w)
            covering.append(row)
        except ApprovalRequired:
            continue
    if not covering:  # raise the full, specific refusal over every row
        require_project_approval(rows, project=project, kind=ApprovalKind.CRAWL,
                                 target=project.base_url, actions=ask_a, wall_clock_s=ask_w)
    best = max(covering, key=lambda r: r.wall_clock_s)  # max() keeps the first (newest) on ties
    return CrawlBounds(
        max_actions=min(max_actions or default.max_actions, best.max_actions),
        wall_clock_s=min(wall_clock_s or default.wall_clock_s, best.wall_clock_s))


def preflight(store: ProjectStore, mode: Mode, bounds: CrawlBounds | None = None) -> list[str]:
    """Check every approval the mode needs BEFORE anything starts; raises `ApprovalRequired`
    (message includes the grant command). Returns the approval ids that cover the run. The
    CRAWL row must cover `bounds` (the bounds the crawl will actually use)."""
    project = store.load_project()
    if project is None:
        raise ValueError(f"project {store.paths.slug!r} is not onboarded; nothing to approve")
    rows = _newest_first(store.list_approvals())
    ids = []
    for kind in required_kinds(mode):
        extra = ({"actions": bounds.max_actions, "wall_clock_s": bounds.wall_clock_s}
                 if bounds is not None and kind is ApprovalKind.CRAWL else {})
        ids.append(require_project_approval(rows, project=project, kind=kind,
                                            target=project.base_url, **extra).id)
    return ids


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
    for name, text in texts.items():  # checked-in evidence, not state (M49)
        (out / name).write_text(text, encoding="utf-8")
    return out, lines


def drive_real(client: Any, store: ProjectStore, spec: ModeSpec, seams: ModeSeams,
               evidence_root: Path, *, approver: str = "acceptance-reviewer",
               bounds: CrawlBounds | None = None,
               on_preflight: Callable[[list[str]], None] | None = None,
               ) -> tuple[ModeResult, Path, list[str]]:
    """Preflight approvals (refuse without them), `run_mode`, write evidence, return the
    checklist. `spec.onboard` should be False for an already-onboarded real target."""
    approval_ids = preflight(store, spec.mode, bounds)
    if on_preflight is not None:
        on_preflight(approval_ids)
    result = run_mode(client, store, spec, seams, approver=approver)
    out, lines = write_evidence(store, result, approval_ids, evidence_root)
    return result, out, lines


@contextmanager
def acceptance_client(app: Any, email: str, password: str, slug: str):
    """Log in normally and check existing project permissions before any live seam."""
    from fastapi.testclient import TestClient

    from autotester.auth.access import authorize, resource_for
    from autotester.auth.sessions import resolve_session
    from autotester.schema.auth import PermissionKey

    origin = "https://127.0.0.1"
    with TestClient(app, base_url=origin, headers={"Origin": origin}) as client:
        response = client.post("/auth/login", data={"email": email, "password": password},
                               follow_redirects=False)
        if response.status_code != 303 or response.headers.get("location") != "/":
            raise ValueError("acceptance sign-in refused; check the account and its group access")
        token = client.cookies.get("__Host-at_session") or client.cookies.get("at_session")
        who = resolve_session(token)
        resource = resource_for(slug)
        needed = (PermissionKey.PROJECT_VIEW, PermissionKey.PROJECT_EDIT,
                  PermissionKey.PROJECT_RUN, PermissionKey.REPORT_VIEW)
        if who is None or any(not authorize(who, key, resource) for key in needed):
            raise ValueError("acceptance account needs view, edit, run "
                             "and report access to this project")
        yield client


def require_fresh_baseline(store: ProjectStore, mode: Mode) -> None:
    """Refuse inherited truth/cases or an entry-mode mismatch; never delete user artifacts."""
    from autotester.stages.generic_acceptance import EXPECTED_MODE
    from autotester.stages.orchestrate import choose_mode

    if choose_mode(store.list_sources())[0] != EXPECTED_MODE[mode]:
        raise ValueError("acceptance mode differs from stored teaching inputs; "
                         "use an isolated baseline")
    if store.load_flowspec() is not None or store.list_cases() or store.list_case_proposals():
        raise ValueError("acceptance requires an isolated baseline without prior truth or cases")
