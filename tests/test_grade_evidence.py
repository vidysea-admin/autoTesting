"""Does the judge actually SEE the evidence it grades on?

Contract: qa/contracts/grade.md G1/G3 and browser-and-secrets.md B11.
AT-049 requires real image delivery; AT-366 requires explicit missing-image counts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from test_ai_capture import _approval, _capture, _Clock, _judge, _judgment

import autotester.stages.ai_judge as module
from autotester.browser.secrets import SecretStore
from autotester.core import image_privacy
from autotester.core.redact import Redactor
from autotester.providers.mock import MockProvider
from autotester.schema.ai_check import AiCheckKind
from autotester.schema.enums import EvidenceKind, Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Criterion, Judgment, Rubric
from autotester.stages.grade import grade


def make_rubric() -> Rubric:
    return Rubric(
        id="rub_login",
        criteria=[
            Criterion(id="c1", text="Login form is visible before submit"),
            Criterion(id="c2", text="Dashboard greeting appears after submit"),
        ],
        no_fire=["cosmetic spacing"],
    )


def make_result(outcome: Outcome, **kw) -> RawResult:
    evidence = kw.pop("evidence", [
        Evidence(kind=EvidenceKind.SCREENSHOT, path="01-login.png", step_order=1),
        Evidence(kind=EvidenceKind.SCREENSHOT, path="02-dashboard.png", step_order=2),
    ])
    return RawResult(case_id="case_abc", outcome=outcome, evidence=evidence, **kw)


# -- AT-049 the judge actually sees the screenshots, not just their names ----

def test_judge_receives_the_real_screenshot_files_when_run_dir_is_given(
    tmp_path: Path, monkeypatch,
) -> None:
    """Send actual safe image copies, rather than filenames or original pixels."""
    run_dir = tmp_path / "run_1"
    run_dir.mkdir()
    _image(run_dir / "01-login.png", monkeypatch)
    _image(run_dir / "02-dashboard.png", monkeypatch)
    judgment = Judgment(result=Result.PASS, scoreboard="2/2 met", criteria_met=2, criteria_total=2)
    judge = MockProvider(responses={"judge": [judgment]})

    grade(make_rubric(), make_result(Outcome.COMPLETED), "run_1", judge, run_dir=run_dir)

    assert len(judge.judge_images[0]) == 2
    assert all(path.parent != run_dir for path in judge.judge_images[0])


def test_judge_receives_no_images_when_run_dir_is_not_given(tmp_path: Path) -> None:
    """A caller that hasn't been updated yet (an older script) still gets
    today's text-only behavior -- never a crash for a missing run_dir."""
    judgment = Judgment(result=Result.PASS, scoreboard="2/2 met", criteria_met=2, criteria_total=2)
    judge = MockProvider(responses={"judge": [judgment]})

    grade(make_rubric(), make_result(Outcome.COMPLETED), "run_1", judge)

    assert judge.judge_images == [[]]


# -- AT-366 a screenshot that is missing is counted, never dropped in silence -

def _image(path: Path, monkeypatch) -> None:
    Image.new("RGB", (100, 60), "white").save(path)
    header = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
              "left\ttop\twidth\theight\tconf\ttext\n")
    monkeypatch.setattr(image_privacy, "_local_ocr", lambda _: header +
                        "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t99\tprivate\n")


def _run_dir_missing_one(tmp_path: Path, monkeypatch) -> Path:
    """The AT-036 retry class on disk: the run recorded two screenshots and only
    one of them was actually written."""
    run_dir = tmp_path / "run_1"
    run_dir.mkdir()
    _image(run_dir / "01-login.png", monkeypatch)
    return run_dir


def test_a_screenshot_the_run_recorded_but_never_wrote_is_counted_not_dropped(
    tmp_path: Path, monkeypatch,
) -> None:
    """Count missing evidence explicitly; send only sanitized existing images."""
    run_dir = _run_dir_missing_one(tmp_path, monkeypatch)
    judgment = Judgment(result=Result.PASS, scoreboard="2/2 met", criteria_met=2, criteria_total=2)
    judge = MockProvider(responses={"judge": [judgment]})

    verdict = grade(make_rubric(), make_result(Outcome.COMPLETED), "run_1", judge,
                    run_dir=run_dir)

    assert len(judge.judge_images[0]) == 1
    assert judge.judge_images[0][0] != run_dir / "01-login.png"
    assert verdict.images_requested == 2, "both SCREENSHOT evidence rows were offered"
    assert verdict.images_seen == 1, "only one file existed"
    assert verdict.graded_on_partial_evidence is True


def test_the_shortfall_reaches_the_field_the_report_actually_renders(
    tmp_path: Path, monkeypatch,
) -> None:
    """The report renders scoreboard; persist the shortfall there and in note."""
    run_dir = _run_dir_missing_one(tmp_path, monkeypatch)
    judgment = Judgment(result=Result.PASS, scoreboard="2/2 met", criteria_met=2, criteria_total=2)
    judge = MockProvider(responses={"judge": [judgment]})

    verdict = grade(make_rubric(), make_result(Outcome.COMPLETED), "run_1", judge,
                    run_dir=run_dir)

    assert "graded on 1 of 2 screenshots" in verdict.scoreboard, "the rendered field"
    assert verdict.scoreboard.endswith("2/2 met"), "the judge's own scoreboard must survive"
    assert "graded on 1 of 2 screenshots" in (verdict.note or ""), "the durable record"


def test_a_complete_run_is_not_labelled_partial_and_keeps_its_own_note(
    tmp_path: Path, monkeypatch,
) -> None:
    """Complete pixel counts still disclose missing visual text and preserve judge notes."""
    run_dir = _run_dir_missing_one(tmp_path, monkeypatch)
    _image(run_dir / "02-dashboard.png", monkeypatch)
    judgment = Judgment(result=Result.PASS, scoreboard="2/2 met", criteria_met=2,
                        criteria_total=2, note="clean run")
    judge = MockProvider(responses={"judge": [judgment]})

    verdict = grade(make_rubric(), make_result(Outcome.COMPLETED), "run_1", judge,
                    run_dir=run_dir)

    assert (verdict.images_requested, verdict.images_seen) == (2, 2)
    assert verdict.graded_on_partial_evidence is False
    assert verdict.note.endswith("clean run"), "the judge's note must survive"
    assert verdict.scoreboard.endswith("2/2 met"), "nor its scoreboard"
    assert "Visual evidence incomplete" in verdict.note
    assert verdict.result is Result.INCONCLUSIVE


def test_a_judgement_on_no_images_at_all_is_visible_as_such(tmp_path: Path) -> None:
    """The worst case and the one that motivated AT-366: every screenshot
    missing, the judge grading on prompt text alone -- the exact AT-049 state --
    and nothing anywhere saying so."""
    run_dir = tmp_path / "run_1"
    run_dir.mkdir()
    judgment = Judgment(result=Result.PASS, scoreboard="2/2 met", criteria_met=2, criteria_total=2)
    judge = MockProvider(responses={"judge": [judgment]})

    verdict = grade(make_rubric(), make_result(Outcome.COMPLETED), "run_1", judge,
                    run_dir=run_dir)

    assert judge.judge_images == [[]]
    assert (verdict.images_requested, verdict.images_seen) == (2, 0)
    assert verdict.graded_on_partial_evidence is True
    assert "graded on 0 of 2 screenshots" in (verdict.note or "")


def test_a_caller_with_no_run_dir_is_not_falsely_flagged_as_partial() -> None:
    """`run_dir=None` is the documented text-only path, not a lost file. It must
    report 0 requested -- flagging it partial would make every older script
    caller look like it had dropped evidence."""
    judgment = Judgment(result=Result.PASS, scoreboard="2/2 met", criteria_met=2, criteria_total=2)
    judge = MockProvider(responses={"judge": [judgment]})

    verdict = grade(make_rubric(), make_result(Outcome.COMPLETED), "run_1", judge)

    assert (verdict.images_requested, verdict.images_seen) == (0, 0)
    assert verdict.graded_on_partial_evidence is False


@pytest.mark.parametrize("check", list(AiCheckKind))
@pytest.mark.parametrize("state", ["empty", "direct", "timed"])
def test_ai_capture_incomplete_observation_reaches_grade_without_judge(
    monkeypatch, check, state,
) -> None:
    seen, real = [], module.grade
    def spy(*args, **kwargs):
        returned = real(*args, **kwargs)
        seen.append((args[1], args[3], returned))
        return returned
    monkeypatch.setattr(module, "grade", spy)
    def forbid_judge(*args, **kwargs):
        raise AssertionError("incomplete capture reached computed judge")
    monkeypatch.setattr(module._ComputedJudge, "judge", forbid_judge)
    cap = _capture(check, prompts=[], expected_keys=["answer"])
    if state == "direct":
        cap = _capture(check).model_copy(update={"unsent_prompts": 2})
    elif state == "timed":
        cap = _capture(check, prompts=["a", "b", "c", "d"], wall_clock_s=1.5,
                       approvals=[_approval(wall_clock_s=1.5)], clock=_Clock(step=0.5))
    judge = MockProvider(responses={"judge": [_judgment(Result.PASS)]})
    verdict = _judge(cap, judge, reference="Paris", latency_budget_s=99)
    assert len(seen) == 1
    raw, instrument, returned = seen[0]
    assert verdict is returned and verdict.result is Result.INCONCLUSIVE
    assert raw.outcome is Outcome.ERRORED
    assert raw.duration_s == sum(e.latency_s for e in cap.exchanges)
    assert f"capture: exchanges={len(cap.exchanges)} unsent_prompts={cap.unsent_prompts}" in [
        e.path for e in raw.evidence]
    if state != "empty":
        assert cap.exchanges and cap.unsent_prompts > 0 and cap.exchanges[0].status == 200
        assert f"prompt[0]: {cap.exchanges[0].prompt}" in [e.path for e in raw.evidence]
        assert f"response[0]: {cap.exchanges[0].response}" in [e.path for e in raw.evidence]
        assert raw.error == "incomplete capture: prompts remain unsent"
    assert instrument.usage == [] and instrument.trace is None
    assert judge.prompts == [] and judge.usage == []


@pytest.mark.parametrize("check,field,secret", [
    (AiCheckKind.TOOL_USE, "tools_called", "ab, cd"),
    (AiCheckKind.HANDOFF_ORDER, "handoffs", "ab > cd"),
])
def test_ai_joined_short_secret_is_withheld_by_actual_grade(monkeypatch, check, field, secret):
    cap = _capture(check)
    cap = cap.model_copy(update={"exchanges": [
        cap.exchanges[0].model_copy(update={field: ["ab", "cd"]})]})
    before, seen, real = cap.model_dump_json(), [], module.grade
    assert secret not in before
    def spy(*args, **kwargs):
        returned = real(*args, **kwargs)
        seen.append((kwargs.get("redactor"), returned))
        return returned
    monkeypatch.setattr(module, "grade", spy)
    redactor = Redactor({"KEY": secret})
    judge = MockProvider(responses={"judge": [_judgment()]})
    verdict = module.judge_capture(cap, run_id="joined", judge=judge, redactor=redactor)
    assert verdict.result is Result.BLOCKED
    assert seen == [(redactor, verdict)] and cap.model_dump_json() == before
    assert judge.prompts == [] and judge.usage == [] and secret not in (verdict.note or "")
    clean = _capture(check)
    allowed = module.judge_capture(clean, run_id="clean", judge=judge, redactor=redactor)
    assert allowed is seen[-1][1] and allowed.result is Result.PASS
    assert len(judge.prompts) == 1 and secret not in judge.prompts[0][1]


def test_ai_computed_grade_enforces_the_final_prompt_redactor(monkeypatch):
    seen, real = [], module.grade
    def spy(*args, **kwargs):
        returned = real(*args, **kwargs)
        seen.append((kwargs.get("redactor"), returned))
        return returned
    monkeypatch.setattr(module, "grade", spy)
    cap = _capture(AiCheckKind.RESPONSE_SHAPE, expected_keys=["answer"])
    redactor = Redactor({"KEY": "prompt[0]: capital"})
    assert "prompt[0]: capital" not in cap.model_dump_json()
    judge = MockProvider()
    verdict = module.judge_capture(cap, run_id="computed", judge=judge, redactor=redactor)
    assert verdict.result is Result.BLOCKED and seen == [(redactor, verdict)]
    assert judge.prompts == [] and judge.usage == []


@pytest.mark.parametrize("budget", [None, float("nan"), float("inf"), -float("inf"), -0.1])
def test_ai_invalid_latency_budget_refuses_before_grade(monkeypatch, budget):
    calls = []
    def forbidden_grade(*args, **kwargs):
        calls.append(args)
        raise AssertionError("invalid latency budget reached grade")
    monkeypatch.setattr(module, "grade", forbidden_grade)
    judge = MockProvider()
    with pytest.raises(ValueError, match="latency_budget"):
        _judge(_capture(AiCheckKind.LATENCY_BUDGET), judge, latency_budget_s=budget)
    assert calls == [] and judge.prompts == [] and judge.usage == []


@pytest.mark.parametrize("budget,expected", [
    (0, Result.FAIL), (0.5, Result.PASS), (99, Result.PASS)])
def test_ai_valid_latency_boundary_remains_computed(budget, expected):
    judge = MockProvider()
    verdict = _judge(_capture(AiCheckKind.LATENCY_BUDGET), judge, latency_budget_s=budget)
    assert verdict.result is expected and judge.prompts == [] and judge.usage == []


@pytest.mark.parametrize("redactor", [None, Redactor({})])
def test_grade_secret_store_guard_survives_optional_redactor(redactor):
    secret = "synthetic-known-grade-secret"
    project = Project(slug="demo", name="Demo", base_url="https://demo.test",
                      allowed_domains=["demo.test"])
    secrets = SecretStore(project, {"DEMO_PASSWORD": secret})
    rubric = make_rubric()
    rubric.criteria[0].text = secret
    judge = MockProvider(responses={"judge": [_judgment()]})
    verdict = grade(rubric, make_result(Outcome.COMPLETED), "guard", judge,
                    secrets=secrets, redactor=redactor)
    assert verdict.result is Result.BLOCKED and secret not in verdict.model_dump_json()
    assert judge.prompts == [] and judge.usage == []


