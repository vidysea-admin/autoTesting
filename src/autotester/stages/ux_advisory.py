"""The advisory UX pass: read a finished run's evidence as a persona, record findings (T-190).

D-048 / `qa/contracts/persona-ux-advisory.md` PU2-PU8. This stage is a second READER of the
evidence `execute.py` already recorded. It runs after the functional results and verdicts are on
disk, never re-drives the product, and never writes a `Verdict`, `Judgment`, `RawResult` or any
rubric -- its only write is `ux_report.json` (`ProjectStore.save_ux_report`). `grade.py` and the
rubric builders do not import it or any persona type (PU4, pinned by a test).

Every model call goes through `Provider.judge` with the `ux_judge` skill prompt (PU5), after the
fully-assembled prompt passes `SecretStore.guard_prompt` (PU6). A persona's device/locale claim is
checked against the case that actually ran (PU8/E6) before any call. The per-run budget counts
logical UX calls, failed attempts included; it is NOT a money/token ceiling.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from pydantic import ValidationError

from autotester.browser.secrets import SecretStore
from autotester.core.excel import autosize_columns
from autotester.core.paths import RepoDocs
from autotester.core.redact import Redactor
from autotester.providers.base import Provider, ProviderError, load_skill_prompt
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, EvidenceKind, Outcome
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.user_persona import UserPersona
from autotester.schema.ux_report import (
    UXCaseOutcome,
    UXCaseStatus,
    UXDraft,
    UXFinding,
    UXJudgment,
    UXReport,
)
from autotester.store import ProjectStore

SKILL_NAME = "ux_judge"  # src/autotester/skills/ux_judge/SKILL.md
MAX_IMAGES = 4
"""Screenshots sent per UX call -- a payload bound, not a quality claim."""
MAX_EVIDENCE_LINES = 40
DEFAULT_LOCALE_LANGS = frozenset({"en"})
"""Languages a run makes no locale claim for. `browser/conditions.py` cannot enact a locale, so
any other language is a LOCALE_I18N claim a plain case never enacted (PU8)."""
_MOBILE_WORDS = ("mobile", "phone", "tablet", "android", "iphone")
_DESKTOP_WORDS = ("desktop", "laptop")
_ADVISORY_STATUSES = (UXCaseStatus.SKIPPED_BUDGET, UXCaseStatus.PROVIDER_ERROR,
                      UXCaseStatus.WITHHELD)
"""Statuses an export must disclose even with zero findings: the reading is incomplete."""


def _device_class(device: str) -> str | None:
    lowered = device.lower()
    if any(word in lowered for word in _MOBILE_WORDS):
        return "mobile"
    if any(word in lowered for word in _DESKTOP_WORDS):
        return "desktop"
    return None


def alignment_refusal(persona: UserPersona, case: Case, result: RawResult) -> str | None:
    """PU8 (E6/AT-581): a fixed reason when the persona's device/locale claim does not match
    what the run actually executed under, else None. Reasons are fixed text -- never a persona
    value -- because they are persisted."""
    if result.outcome is Outcome.NOT_RUN:
        return "the case did not run (its execution condition was not enacted)"
    claimed = _device_class(persona.device)
    if claimed is None:
        return "the persona's device is not a condition this run can claim"
    ran_as = "mobile" if case.case_class is CaseClass.VIEWPORT_MOBILE else "desktop"
    if claimed != ran_as:
        return "the persona's device does not match the viewport the case ran under"
    language = persona.locale.split("-")[0].split("_")[0].lower()
    if language not in DEFAULT_LOCALE_LANGS and case.case_class is not CaseClass.LOCALE_I18N:
        return "the persona's locale is a claim this case never enacted"
    return None


def _evidence_lines(result: RawResult) -> list[str]:
    lines = []
    for ev in result.evidence[:MAX_EVIDENCE_LINES]:
        step = f" (step {ev.step_order})" if ev.step_order is not None else ""
        label = f" -- {ev.label}" if ev.label else ""
        lines.append(f"- [{ev.kind.value}] {ev.path}{step}{label}")
    return lines


def build_ux_prompt(persona: UserPersona, result: RawResult, docs: RepoDocs) -> str:
    """The `ux_judge` SKILL.md body with this persona and evidence filled in (PU5: a prompt
    file, never an inline string; a missing file raises `FileNotFoundError`)."""
    template = load_skill_prompt(SKILL_NAME, skills_dir=docs.skills_dir)
    who = (f"role: {persona.role}\ntech comfort: {persona.tech_comfort.value}\n"
           f"language/locale: {persona.locale}\ndevice: {persona.device}")
    evidence = f"outcome: {result.outcome.value}\n" + "\n".join(_evidence_lines(result))
    return template.replace("{{PERSONA}}", who).replace("{{EVIDENCE}}", evidence)


def _screenshots(result: RawResult, run_dir: Path) -> list[Path]:
    """Screenshot files that really exist inside `run_dir`, at most `MAX_IMAGES`."""
    root = run_dir.resolve()
    found: list[Path] = []
    for ev in result.evidence:
        if ev.kind is not EvidenceKind.SCREENSHOT:
            continue
        candidate = (run_dir / ev.path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            found.append(candidate)
    return found[:MAX_IMAGES]


def _validated(draft: UXDraft, case_id: str, persona_id: str, result: RawResult,
               redactor: Redactor) -> UXFinding | None:
    """A draft becomes a finding only when what it cites is real evidence on this result."""
    steps = {e.step_order for e in result.evidence if e.step_order is not None}
    paths = {e.path for e in result.evidence}
    if draft.step_order is None and draft.evidence_path is None:
        return None
    if draft.step_order is not None and draft.step_order not in steps:
        return None
    if draft.evidence_path is not None and draft.evidence_path not in paths:
        return None
    return UXFinding(case_id=case_id, persona_id=persona_id, severity=draft.severity,
                     finding=redactor.scrub(draft.finding), step_order=draft.step_order,
                     evidence_path=draft.evidence_path)


def judge_case_ux(
    case: Case, result: RawResult, persona: UserPersona, provider: Provider, *,
    secrets: SecretStore, run_dir: Path, docs: RepoDocs | None = None,
) -> UXCaseOutcome:
    """One advisory reading of one case. Raises `ValueError` BEFORE any provider call when the
    assembled prompt carries a raw credential (PU6) and `FileNotFoundError` when the skill file
    is missing (PU5). Reads `result`; never mutates it and never sees a `Verdict` (PU3)."""
    prompt = secrets.guard_prompt(build_ux_prompt(persona, result, docs or RepoDocs()))
    try:
        judgment = provider.judge(prompt, UXJudgment, images=_screenshots(result, run_dir),
                                  prompt_file=SKILL_NAME, fed_id=case.id)
    except (ProviderError, ValidationError) as exc:
        return UXCaseOutcome(case_id=case.id, persona_id=persona.id,
                             status=UXCaseStatus.PROVIDER_ERROR,
                             reason=f"the UX provider call failed ({type(exc).__name__})")
    redactor = secrets.redactor()
    kept = [f for d in judgment.findings
            for f in [_validated(d, case.id, persona.id, result, redactor)] if f is not None]
    return UXCaseOutcome(case_id=case.id, persona_id=persona.id, status=UXCaseStatus.ANALYZED,
                         dropped_findings=len(judgment.findings) - len(kept), findings=kept)


def _resolve_persona(
    case: Case, project: Project, personas: dict[str, UserPersona]
) -> UserPersona | UXCaseOutcome:
    """Case ref first, project ref as the fallback; a dangling ref is recorded, never guessed."""
    ref = case.user_persona_ref or project.user_persona_ref
    if ref is None:
        return _skip(case.id, None, UXCaseStatus.NO_PERSONA,
                     "no persona is attached to the case or the project")
    persona = personas.get(ref)
    if persona is None:
        return _skip(case.id, ref, UXCaseStatus.MISSING_PERSONA,
                     "the referenced persona is not on file")
    return persona


def _skip(case_id: str, persona_id: str | None, status: UXCaseStatus, reason: str
          ) -> UXCaseOutcome:
    return UXCaseOutcome(case_id=case_id, persona_id=persona_id, status=status, reason=reason)


def _advise_case(
    case_id: str, case: Case | None, result: RawResult | None, project: Project,
    personas: dict[str, UserPersona], provider: Provider, secrets: SecretStore,
    run_dir: Path, budget_left: int, docs: RepoDocs | None,
) -> tuple[UXCaseOutcome, int]:
    """(outcome, calls spent) for one case. The eligibility gates run before the budget, so
    `skipped_budget` only ever names a case that WOULD have been read."""
    if case is None or result is None:
        return _skip(case_id, None, UXCaseStatus.NO_EVIDENCE,
                     "the case or its result is not on file"), 0
    persona = _resolve_persona(case, project, personas)
    if isinstance(persona, UXCaseOutcome):
        return persona, 0
    refusal = alignment_refusal(persona, case, result)
    if refusal is not None:
        return _skip(case_id, persona.id, UXCaseStatus.REFUSED_CONDITION, refusal), 0
    if not _screenshots(result, run_dir):
        return _skip(case_id, persona.id, UXCaseStatus.NO_EVIDENCE,
                     "no screenshot evidence is on disk"), 0
    if budget_left <= 0:
        return _skip(case_id, persona.id, UXCaseStatus.SKIPPED_BUDGET,
                     "the per-run UX call budget was exhausted"), 0
    try:
        outcome = judge_case_ux(case, result, persona, provider, secrets=secrets,
                                run_dir=run_dir, docs=docs)
    except ValueError:  # the redaction guard fired: nothing was sent (PU6)
        return _skip(case_id, persona.id, UXCaseStatus.WITHHELD,
                     "a credential value reached the UX prompt, so it was not sent"), 0
    return outcome, 1


def run_ux_advisory(
    store: ProjectStore, run_id: str, provider: Provider, *,
    secrets: SecretStore | None = None, docs: RepoDocs | None = None,
) -> UXReport | None:
    """The one post-functional advisory pass for a persisted run. `None` (and no file) unless
    the project opted in (`ux_policy.enabled`). Reads cases/results/personas, writes only
    `ux_report.json`; cases are processed once, in the run's case order."""
    project = store.load_project()
    if project is None or not project.ux_policy.enabled:
        return None
    secrets = secrets or SecretStore.load(project, store.paths.env_file, strict=False)
    run = store.load_run(run_id)
    results = {r.case_id: r for r in store.load_results(run_id)}
    cases = {c.id: c for c in store.list_cases()}
    personas = {p.id: p for p in store.list_user_personas()}
    cap, used, outcomes = project.ux_policy.max_calls, 0, []
    for case_id in (run.case_ids if run and run.case_ids else list(results)):
        outcome, spent = _advise_case(
            case_id, cases.get(case_id), results.get(case_id), project, personas, provider,
            secrets, store.paths.run_dir(run_id), cap - used, docs)
        used += spent
        outcomes.append(outcome)
    report = UXReport(run_id=run_id, project=store.paths.slug, provider=provider.label,
                      max_calls=cap, calls_used=used, cases=outcomes)
    store.save_ux_report(report)
    return report


# -- export presentation (PU7): findings are their own section, never merged with failures ----
def load_ux_state(store: ProjectStore, run_id: str) -> tuple[UXReport | None, str | None]:
    """(report, error). (None, None) = UX never ran for this run; (None, msg) = a report file
    exists but cannot be read -- exports must say so, never show it as zero findings."""
    try:
        return store.load_ux_report(run_id), None
    except ValueError:
        return None, "ux_report.json exists but is unreadable (invalid JSON or schema)"


def ux_findings_html(state: tuple[UXReport | None, str | None], case_id: str,
                     redactor: Redactor) -> str:
    """A `<div class='ux-findings'>` sibling of the failures block, or "" when this case has
    nothing to disclose (no empty section, matching the other exports' convention)."""
    report, error = state
    head = ("<div class='ux-findings' style='margin-top:.6rem'><h3 style='font-size:.85rem;"
            "margin:.6rem 0 .2rem'>UX findings (advisory — not a pass/fail)</h3>")
    if error is not None:
        return f"{head}<p class='meta'>UX report unavailable: {escape(error)}</p></div>"
    outcome = report.outcome_for(case_id) if report else None
    if outcome is None or not (outcome.findings or outcome.status in _ADVISORY_STATUSES):
        return ""
    items = "".join(
        f"<li><code>{f.severity.value}</code> — {escape(redactor.scrub(f.finding))}"
        f" <span class='meta'>({escape(f.evidence_path or f'step {f.step_order}')})</span></li>"
        for f in outcome.findings)
    note = ("" if outcome.findings else
            f"<p class='meta'>UX pass incomplete for this case: {escape(outcome.status.value)}"
            f" — {escape(outcome.reason or '')}</p>")
    return f"{head}<ul>{items}</ul>{note}</div>" if items else f"{head}{note}</div>"


def add_ux_sheet(wb, state: tuple[UXReport | None, str | None], cases: dict[str, Case],
                 redactor: Redactor) -> None:
    """A distinct 'UX findings (advisory)' sheet -- never columns of the Failures/Repro cells.
    No sheet when UX never ran or there is nothing to disclose."""
    report, error = state
    rows: list[list[str]] = []
    if error is not None:
        rows.append(["", "", "unavailable", error, "", ""])
    for outcome in (report.cases if report else []):
        case = cases.get(outcome.case_id)
        title = redactor.scrub(case.title) if case else outcome.case_id
        for f in outcome.findings:
            rows.append([title, f.persona_id, f.severity.value, redactor.scrub(f.finding),
                         "" if f.step_order is None else str(f.step_order), f.evidence_path or ""])
        if not outcome.findings and outcome.status in _ADVISORY_STATUSES:
            rows.append([title, outcome.persona_id or "", outcome.status.value,
                         outcome.reason or "", "", ""])
    if not rows:
        return
    ws = wb.create_sheet("UX findings (advisory)")
    ws.append(["Case", "Persona", "UX severity / status", "UX finding", "Step", "Evidence"])
    for row in rows:
        ws.append(row)
    autosize_columns(ws)
