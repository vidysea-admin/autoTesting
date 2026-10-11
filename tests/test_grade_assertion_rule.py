"""AT-773 / D-074(b), grade.md G6, execute.md E1: a failed deterministic assertion never PASSes.

`grade()` is the one guard. A run whose outcome is ASSERTION_FAILED (the executor
recorded an unmet declared expectation) may end FAIL or INCONCLUSIVE, never PASS,
whatever the judge says. Rule: judge PASS on such a run -> INCONCLUSIVE (the judge
contradicted a recorded fact, so a human must look); judge FAIL / INCONCLUSIVE
pass through unchanged. COMPLETED runs are untouched.
"""

from __future__ import annotations

from autotester.providers.mock import MockProvider
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Failure, Judgment, Rubric
from autotester.stages.grade import grade

UNMET = "assert visible_text: unmet (expected 'YOUR PROGRESS')"


def _rubric() -> Rubric:
    return Rubric(id="rub_t", criteria=[Criterion(id="c1", text="Dashboard is shown")])


def _result(outcome: Outcome) -> RawResult:
    evidence = [Evidence(kind=EvidenceKind.SCREENSHOT, path="01.png", step_order=1)]
    if outcome is Outcome.ASSERTION_FAILED:
        evidence.append(Evidence(kind=EvidenceKind.DOM, path=UNMET, step_order=1))
    return RawResult(case_id="case_t", outcome=outcome, evidence=evidence)


def _pass() -> Judgment:
    return Judgment(result=Result.PASS, scoreboard="1/1 met", criteria_met=1, criteria_total=1)


def test_judge_pass_on_an_unmet_login_assertion_is_never_pass() -> None:
    """T-122: the Pathlynks login run whose 'YOUR PROGRESS' marker assertion was unmet
    still got a judge PASS (6 of 6 re-grades). That must no longer end PASS."""
    judge = MockProvider(responses={"judge": [_pass()]})
    verdict = grade(_rubric(), _result(Outcome.ASSERTION_FAILED), "run_1", judge)

    assert judge.prompts, "the judge still sees the run; the guard is applied to its answer"
    assert verdict.result is not Result.PASS
    assert verdict.result is Result.INCONCLUSIVE
    assert "D-074" in (verdict.note or "") and UNMET in (verdict.note or "")


def test_judge_pass_on_a_completed_run_carrying_unmet_assert_evidence_is_never_pass() -> None:
    """G6 also covers any run that carries `assert <field>: unmet` evidence, even if its
    outcome enum was not ASSERTION_FAILED (e.g. a network assertion recorded unmet)."""
    result = _result(Outcome.COMPLETED)
    result.evidence.append(Evidence(kind=EvidenceKind.NETWORK,
                                    path="assert network: unmet ('/api/me')", step_order=2))
    judge = MockProvider(responses={"judge": [_pass()]})
    verdict = grade(_rubric(), result, "run_1", judge)

    assert verdict.result is Result.INCONCLUSIVE
    assert "assert network: unmet" in (verdict.note or "")


def test_met_assertions_do_not_trigger_the_guard() -> None:
    """Same case, assertion met (`assert visible_text: met`), judge PASS -> PASS."""
    result = _result(Outcome.COMPLETED)
    result.evidence.append(Evidence(kind=EvidenceKind.DOM,
                                    path="assert visible_text: met ('X')", step_order=1))
    judge = MockProvider(responses={"judge": [_pass()]})
    assert grade(_rubric(), result, "run_1", judge).result is Result.PASS


def test_judge_pass_on_a_completed_run_still_passes() -> None:
    """A normal run with every assertion met and a judge PASS is unaffected."""
    judge = MockProvider(responses={"judge": [_pass()]})
    verdict = grade(_rubric(), _result(Outcome.COMPLETED), "run_1", judge)

    assert verdict.result is Result.PASS
    assert verdict.note is None


def test_judge_fail_on_an_assertion_failed_run_stays_fail_with_its_failures() -> None:
    """The judge agreeing with the recorded failure keeps FAIL and its cited failures."""
    failure = Failure(criterion_id="c1", reason="dashboard marker missing",
                      evidence_refs=["01.png"])
    judgment = Judgment(result=Result.FAIL, scoreboard="0/1 met", criteria_met=0,
                        criteria_total=1, failures=[failure])
    judge = MockProvider(responses={"judge": [judgment]})
    verdict = grade(_rubric(), _result(Outcome.ASSERTION_FAILED), "run_1", judge)

    assert verdict.result is Result.FAIL
    assert verdict.failures == [failure]


def test_judge_inconclusive_on_an_assertion_failed_run_stays_inconclusive() -> None:
    """A judge that cannot tell stays INCONCLUSIVE; the guard never upgrades anything."""
    judgment = Judgment(result=Result.INCONCLUSIVE, scoreboard="?", criteria_total=1,
                        note="evidence too thin")
    judge = MockProvider(responses={"judge": [judgment]})
    verdict = grade(_rubric(), _result(Outcome.ASSERTION_FAILED), "run_1", judge)

    assert verdict.result is Result.INCONCLUSIVE

