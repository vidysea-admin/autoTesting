"""GRADE: an independent, stateless judge reads a Rubric + a RawResult's evidence.

The executor never grades itself (core-invariants C7) — this stage never sees the
case's steps or script, only the rubric and the evidence execute.py recorded.
`BLOCKED_HITL`/`ERRORED` outcomes are judged deterministically (there is nothing
coherent to grade); only `COMPLETED` runs reach the judge. The judge's raw answer
is then self-consistency-checked before it becomes a `Verdict` — an unevidenced
failure, or a PASS that doesn't add up, is downgraded to INCONCLUSIVE rather than
trusted. Contract: qa/contracts/grade.md.
"""

from __future__ import annotations

from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider, load_skill_prompt
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Failure, Judgment, Rubric, Verdict

SKILL_NAME = "grade"  # src/autotester/skills/grade/SKILL.md (T-175, was grade_v1.md)


def _render_evidence(result: RawResult) -> str:
    lines = [f"outcome: {result.outcome.value}"]
    for ev in result.evidence:
        loc = f" (step {ev.step_order})" if ev.step_order is not None else ""
        lines.append(f"- [{ev.kind.value}] {ev.path}{loc}")
    return "\n".join(lines)


def _render_rubric(rubric: Rubric) -> str:
    criteria = "\n".join(
        f"- {c.id}: {c.text}" + (" (evidence required)" if c.evidence_required else "")
        for c in rubric.criteria
    )
    no_fire = "\n".join(f"- {n}" for n in rubric.no_fire) or "(none)"
    return f"criteria:\n{criteria}\n\nno-fire (do not flag these):\n{no_fire}"


def build_grade_prompt(rubric: Rubric, result: RawResult, docs: RepoDocs) -> str:
    template = load_skill_prompt(SKILL_NAME, skills_dir=docs.skills_dir)
    return (
        template.replace("{{RUBRIC}}", _render_rubric(rubric))
        .replace("{{EVIDENCE}}", _render_evidence(result))
        .replace("{{FORMAT}}", rubric.feedback_format)
    )


def _inconsistency(rubric: Rubric, judgment: Judgment) -> str | None:
    """Why `judgment` cannot be trusted as-is, or None if it's self-consistent."""
    known_ids = {c.id for c in rubric.criteria}
    evidence_required = {c.id for c in rubric.criteria if c.evidence_required}
    for failure in judgment.failures:
        if failure.criterion_id not in known_ids:
            return f"failure cites unknown criterion '{failure.criterion_id}'"
        if failure.criterion_id in evidence_required and not failure.evidence_refs:
            return f"failure on '{failure.criterion_id}' has no evidence_refs"
    if judgment.criteria_total != len(rubric.criteria):
        return f"criteria_total {judgment.criteria_total} != rubric has {len(rubric.criteria)}"
    if judgment.result is Result.PASS and judgment.failures:
        return "PASS but failures is non-empty"
    if judgment.result is Result.FAIL and not judgment.failures:
        return "FAIL but no failures cited"
    return None


def _verdict(
    run_id: str, result: RawResult, rubric: Rubric, *, verdict_result: Result,
    provider_id: str, scoreboard: str, note: str | None = None,
    criteria_met: int = 0, failures: list[Failure] | None = None,
    images_requested: int = 0, images_seen: int = 0,
) -> Verdict:
    return Verdict(
        run_id=run_id, case_id=result.case_id, result=verdict_result, scoreboard=scoreboard,
        criteria_met=criteria_met, criteria_total=len(rubric.criteria),
        failures=failures or [], grader_provider=provider_id,
        rubric_hash=rubric.fingerprint, note=note,
        images_requested=images_requested, images_seen=images_seen,
    )


def _screenshot_paths(result: RawResult, run_dir: Path | None) -> list[Path]:
    """Real image files the judge should actually see — AT-049: `_render_evidence`
    only ever put a screenshot's *filename* in the prompt, so a text-only judge
    was grading blind, guessing plausibility from a label it could not verify.
    `run_dir` is optional so a caller without one yet (an older script) still
    gets today's text-only behavior, never a crash."""
    if run_dir is None:
        return []
    return [
        run_dir / ev.path for ev in result.evidence if ev.kind is EvidenceKind.SCREENSHOT
    ]


def _withheld(
    run_id: str, result: RawResult, rubric: Rubric, prompt: str,
    secrets: SecretStore | None,
) -> Verdict | None:
    """A BLOCKED verdict when a credential reached the grading prompt, else None.

    AT-070: refusing to send the prompt is right, but crashing the run is not — a
    credential that reached a rubric (e.g. via a case title feeding `claim_of`)
    would otherwise 500 every subsequent run with no way back. Fail this case
    loudly and safely instead, naming no value."""
    if secrets is None:
        return None
    try:
        secrets.guard_prompt(prompt)
    except ValueError as exc:
        return _verdict(
            run_id, result, rubric, verdict_result=Result.BLOCKED,
            provider_id="rule", scoreboard="not judged: prompt withheld",
            note=f"a credential value reached the grading prompt, so it was not sent "
                 f"({type(exc).__name__}). Remove it from the case and use "
                 f"{{{{SECRET:KEY}}}} instead.",
        )
    return None


def _outcome_verdict(result: RawResult, rubric: Rubric, run_id: str) -> Verdict | None:
    """The deterministic outcomes a judge never sees (D-032: ASSERTION_FAILED
    is deliberately NOT one of them — a declared expectation failing is
    evidence to weigh, not a refusal to judge; the judge may disagree with a
    wrongly-authored expectation, and only the grader can tell a case defect
    from a product defect)."""
    if result.outcome is Outcome.BLOCKED_HITL:
        return _verdict(run_id, result, rubric, verdict_result=Result.BLOCKED,
                         provider_id="rule", scoreboard="not judged: execution was blocked",
                         note=result.hitl_prompt)
    if result.outcome is Outcome.ERRORED:
        return _verdict(run_id, result, rubric, verdict_result=Result.INCONCLUSIVE,
                         provider_id="rule", scoreboard="not judged: execution errored",
                         note=result.error)
    if result.outcome is Outcome.NOT_RUN:
        # D-045/AT-581 (E6): the case's execution condition could not be enacted -- it never
        # ran, so it never reaches the judge and can never come back PASS.
        return _verdict(run_id, result, rubric, verdict_result=Result.INCONCLUSIVE,
                         provider_id="rule", scoreboard="not judged: execution condition "
                         "could not be enacted", note=result.not_run_reason)
    return None


def grade(rubric: Rubric, result: RawResult, run_id: str, judge: Provider,
          docs: RepoDocs | None = None, run_dir: Path | None = None,
          secrets: SecretStore | None = None) -> Verdict:
    """Judge one case's execution against `rubric`. Never sees the case's own steps.

    `secrets`, when given, gates the built prompt through
    `SecretStore.guard_prompt` before it reaches a model. That gate is
    documented as "call before every model call" but had no production
    caller: protection rested entirely on evidence having been scrubbed at
    `session._record`. Optional so the existing script callers are unchanged.
    D-032/AT-540: an ASSERTION_FAILED run still reaches the judge — the
    recorded unmet assertions travel inside the evidence list, so the judge
    weighs recorded facts, not just pixels."""
    outcome = _outcome_verdict(result, rubric, run_id)
    if outcome is not None:
        return outcome

    prompt = build_grade_prompt(rubric, result, docs or RepoDocs())
    withheld = _withheld(run_id, result, rubric, prompt, secrets)
    if withheld is not None:
        return withheld

    # AT-366: filter HERE, once, and count what was lost. All three providers drop a
    # non-existent path in silence, so a screenshot the executor recorded but failed to
    # write (the AT-036 retry class) produced a shorter list with no error, no log line
    # and no trace on the Verdict -- a judgement rendered on a subset of its evidence,
    # indistinguishable from one rendered on all of it. The counts travel on the Verdict
    # so the grader's output and the report can both read them.
    requested = _screenshot_paths(result, run_dir)
    seen = [path for path in requested if path.exists()]
    counts = {"images_requested": len(requested), "images_seen": len(seen)}

    judgment = judge.judge(prompt, Judgment, images=seen,
                           prompt_file=SKILL_NAME, fed_id=result.case_id)
    problem = _inconsistency(rubric, judgment)
    if problem is not None:
        return _verdict(run_id, result, rubric, verdict_result=Result.INCONCLUSIVE,
                         provider_id=judge.id, scoreboard="judge output rejected",
                         note=f"self-consistency check failed: {problem}", **counts)
    shortfall = _shortfall(**counts)
    return _verdict(run_id, result, rubric, verdict_result=judgment.result,
                     provider_id=judge.id,
                     scoreboard=_joined(shortfall, judgment.scoreboard) or "",
                     criteria_met=judgment.criteria_met, failures=judgment.failures,
                     note=_joined(shortfall, judgment.note), **counts)


def _shortfall(*, images_requested: int, images_seen: int) -> str | None:
    """One sentence naming what the judge did not see, or None (AT-366).

    A structured count nothing renders is the same silence one layer up, so this
    goes into BOTH the `note` (the durable record) and the `scoreboard` — the
    scoreboard because that is what `report_export.py` actually puts on the page
    (`_case_section`, the summary table); `note` is not rendered anywhere today."""
    if images_seen >= images_requested:
        return None
    return (
        f"graded on {images_seen} of {images_requested} screenshots — "
        f"{images_requested - images_seen} evidence file(s) the run recorded were not on disk"
    )


def _joined(shortfall: str | None, text: str | None) -> str | None:
    """`shortfall` first — it qualifies everything after it."""
    if shortfall is None:
        return text
    return f"{shortfall}. {text}" if text else shortfall
