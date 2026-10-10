"""AI JUDGE: map captured observations into the existing grade stage's evidence and rubric.

Contract: qa/contracts/ai-target.md AI6-AI7, core-invariants C5/C7. `stages/ai_capture.py` only
observes; this module adapts two instruments the registry records per check
(`ai_catalog.CHECK_METHOD`):

* COMPUTED (response shape, latency): a rule over the numbers and flags the capturer recorded.
  A private Provider supplies a Judgment to grade; no model call or usage span is emitted.
* JUDGED (ground truth, tool use, hand-offs): the capture becomes a `RawResult` and goes,
  unmodified, to `stages/grade.py::grade` against a `Rubric`, which is the only judgement path.

Before anything reaches a prompt the capture and the reference are scrubbed again and must stay
clean (`Redactor.scrub` then `Redactor.assert_clean`); otherwise `CaptureWithheld` is raised and no
model is called.
"""

from __future__ import annotations

from math import isfinite
from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.ids import content_id
from autotester.core.paths import RepoDocs
from autotester.core.redact import Redactor
from autotester.providers.base import ModelT, Provider
from autotester.schema.ai_check import AiCapture, AiCheckKind, AiCheckMethod
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Failure, Judgment, Rubric, Verdict
from autotester.stages.ai_capture import CaptureWithheld
from autotester.stages.ai_catalog import CHECK_METHOD
from autotester.stages.grade import grade

_CRITERIA: dict[AiCheckKind, list[tuple[str, str]]] = {
    AiCheckKind.RESPONSE_SHAPE: [
        ("AI-RS1", "Every response is a JSON object."),
        ("AI-RS2", "Every response contains every expected key."),
    ],
    AiCheckKind.LATENCY_BUDGET: [
        ("AI-LB1", "Every prompt was answered successfully."),
        ("AI-LB2", "Every answer arrived within the latency budget of {budget}s."),
    ],
    AiCheckKind.GROUND_TRUTH_ANSWER: [
        ("AI-GT1", "Each response agrees with the reference answer: {reference}"),
        ("AI-GT2", "No response states a fact that contradicts the reference answer."),
    ],
    AiCheckKind.TOOL_USE: [
        ("AI-TU1", "Each tool the system called is relevant to the prompt that triggered it."),
        ("AI-TU2", "Each response is consistent with the tools called and claims no tool "
                   "result that was not called."),
    ],
    AiCheckKind.HANDOFF_ORDER: [
        ("AI-HO1", "The hand-offs recorded for each prompt are in a sensible order and none "
                   "repeats in a loop."),
        ("AI-HO2", "Each final response is consistent with the hand-offs recorded."),
    ],
}
_NO_FIRE = ["wording, tone or length differences", "formatting of the response"]


def _scrubbed(cap: AiCapture, redactor: Redactor) -> AiCapture:
    """The capture with every string re-scrubbed; refused whole if a secret still shows."""
    clean = AiCapture.model_validate(redactor.scrub_obj(cap.model_dump(mode="json")))
    _assert_clean(redactor, clean.model_dump_json())
    return clean


def _assert_clean(redactor: Redactor, text: str) -> None:
    try:
        redactor.assert_clean(text)
    except ValueError:
        raise CaptureWithheld("a secret reached the judge side; nothing was judged") from None


def _case_id(cap: AiCapture) -> str:
    prompts = [e.prompt for e in cap.exchanges]
    return content_id("aic", {"check": cap.check.value, "endpoint": cap.endpoint,
                              "prompts": prompts})


def _rubric(cap: AiCapture, case_id: str, reference: str | None, budget: float | None) -> Rubric:
    criteria = [
        Criterion(id=cid, text=text.format(budget=budget, reference=reference))
        for cid, text in _CRITERIA[cap.check]
    ]
    return Rubric(id=f"rub_{cap.check.value}", case_id=case_id, criteria=criteria,
                  no_fire=_NO_FIRE)


def _evidence(cap: AiCapture) -> list[Evidence]:
    rows = [Evidence(kind=EvidenceKind.NETWORK, label="capture",
                     path=f"capture: exchanges={len(cap.exchanges)} "
                          f"unsent_prompts={cap.unsent_prompts}")]
    for i, ex in enumerate(cap.exchanges):
        facts = [("prompt", ex.prompt), ("response", ex.response)]
        if cap.check is AiCheckKind.TOOL_USE:
            facts.append(("tools_called", ", ".join(ex.tools_called)))
        if cap.check is AiCheckKind.HANDOFF_ORDER:
            facts.append(("handoffs", " > ".join(ex.handoffs)))
        facts.append(("exchange", f"status={ex.status} error={ex.error} "
                      f"latency_s={ex.latency_s} is_json={ex.is_json} "
                      f"missing_keys={ex.missing_keys}"))
        rows += [Evidence(kind=EvidenceKind.NETWORK, path=f"{label}[{i}]: {text}",
                          step_order=i, label=label) for label, text in facts]
    return rows


def _raw_result(cap: AiCapture, case_id: str) -> RawResult:
    errors = [e.error for e in cap.exchanges if e.error]
    errored = cap.unsent_prompts > 0 or not cap.exchanges or (
        CHECK_METHOD[cap.check] is AiCheckMethod.JUDGED and len(errors) == len(cap.exchanges))
    reason = ("incomplete capture: prompts remain unsent" if cap.unsent_prompts > 0 else
              (", ".join(errors) or "no exchange was captured")) if errored else None
    return RawResult(case_id=case_id, outcome=Outcome.ERRORED if errored else Outcome.COMPLETED,
                     error=reason,
                     duration_s=sum(e.latency_s for e in cap.exchanges),
                     evidence=_evidence(cap))


def _computed_failures(cap: AiCapture, budget: float | None) -> list[Failure]:
    found: list[Failure] = []
    for i, ex in enumerate(cap.exchanges):
        ref = [f"exchange[{i}]"]
        if cap.check is AiCheckKind.RESPONSE_SHAPE:
            if not ex.is_json:
                found.append(Failure(criterion_id="AI-RS1", reason="not a JSON object",
                                     evidence_refs=ref))
            elif ex.missing_keys:
                found.append(Failure(criterion_id="AI-RS2", evidence_refs=ref,
                                     reason="missing keys: " + ", ".join(ex.missing_keys)))
        else:
            if ex.error or ex.status is None or ex.status >= 400:
                found.append(Failure(criterion_id="AI-LB1", evidence_refs=ref,
                                     reason=f"no successful answer (error={ex.error})"))
            elif budget is not None and ex.latency_s > budget:
                found.append(Failure(criterion_id="AI-LB2", evidence_refs=ref,
                                     reason=f"took {ex.latency_s:.2f}s, budget {budget}s"))
    return found


class _ComputedJudge(Provider):
    """Code-only measurement instrument; grade alone accepts it and creates the verdict."""

    id = "rule"

    def __init__(self, cap: AiCapture, rubric: Rubric, budget: float | None) -> None:
        super().__init__()
        self.cap, self.rubric, self.budget = cap, rubric, budget

    def available(self) -> bool:
        return True

    def judge(self, prompt: str, schema: type[ModelT], images: list[Path] | None = None, *,
              prompt_file: str | None = None, fed_id: str | None = None) -> ModelT:
        failures = _computed_failures(self.cap, self.budget)
        total = len(self.rubric.criteria)
        met = total - len({f.criterion_id for f in failures})
        judgment = Judgment(result=Result.FAIL if failures else Result.PASS, criteria_met=met,
                            criteria_total=total, scoreboard=f"Criteria {met}/{total} met.",
                            failures=failures)
        return schema.model_validate(judgment.model_dump())


def _rule_verdict(cap: AiCapture, rubric: Rubric, run_id: str, case_id: str,
                  budget: float | None, *, docs: RepoDocs | None = None,
                  run_dir: Path | None = None, secrets: SecretStore | None = None,
                  redactor: Redactor | None = None) -> Verdict:
    return grade(rubric, _raw_result(cap, case_id), run_id, _ComputedJudge(cap, rubric, budget),
                 docs=docs, run_dir=run_dir, secrets=secrets, redactor=redactor)


def _check_inputs(cap: AiCapture, reference: str | None, budget: float | None) -> None:
    if cap.check is AiCheckKind.GROUND_TRUTH_ANSWER and not reference:
        raise ValueError("a ground_truth_answer check needs a reference answer")
    if cap.check is AiCheckKind.LATENCY_BUDGET and (
            budget is None or not isfinite(budget) or budget < 0):
        raise ValueError("a latency_budget check needs finite nonnegative latency_budget_s")


def judge_capture(
    cap: AiCapture, *, run_id: str, judge: Provider, redactor: Redactor,
    reference: str | None = None, latency_budget_s: float | None = None,
    docs: RepoDocs | None = None, run_dir: Path | None = None,
    secrets: SecretStore | None = None,
) -> Verdict:
    """One grade-owned `Verdict` for one capture, using the check's declared instrument."""
    _check_inputs(cap, reference, latency_budget_s)
    clean = _scrubbed(cap, redactor)
    ref = redactor.scrub(reference) if reference else None
    if ref:
        _assert_clean(redactor, ref)
    case_id = _case_id(clean)
    rubric = _rubric(clean, case_id, ref, latency_budget_s)
    _assert_clean(redactor, rubric.model_dump_json())
    if CHECK_METHOD[clean.check] is AiCheckMethod.COMPUTED:
        return _rule_verdict(clean, rubric, run_id, case_id, latency_budget_s,
                             docs=docs, run_dir=run_dir, secrets=secrets, redactor=redactor)
    raw = _raw_result(clean, case_id)
    return grade(rubric, raw, run_id, judge, docs=docs, run_dir=run_dir,
                 secrets=secrets, redactor=redactor)
