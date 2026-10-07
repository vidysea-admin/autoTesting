"""Behavioural capture + judgement. Contract: ai-target.md AI6-AI7; core-invariants C5/C7; D-018.

The capturer observes, the judge side decides: these tests drive an injected `send` (no network)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from autotester.core.consent import ApprovalRequired
from autotester.core.redact import Redactor
from autotester.providers.mock import MockProvider
from autotester.schema.ai_check import AiCapture, AiCheckKind, AiExchange, AiReply
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind, Result
from autotester.schema.verdict import Failure, Judgment
from autotester.stages import ai_capture
from autotester.stages.ai_capture import CaptureWithheld, capture_run
from autotester.stages.ai_judge import judge_capture

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
URL = "https://llm.test/chat"
NOW = datetime(2026, 10, 7, tzinfo=UTC)
SECRET = "sk-live-1234567890abcdef"


def _approval(**kw: object) -> RunApproval:
    fields: dict[str, object] = {
        "project": "demo", "run_kind": ApprovalKind.LIVE_CASE, "target": URL,
        "scope": "behavioural capture of the chat endpoint", "max_actions": 10,
        "wall_clock_s": 60.0, "granted_by": "umesh", "granted_at": "2026-10-01",
        "expires_at": "2026-12-01"}
    fields.update(kw)
    return RunApproval(**fields).sign()  # type: ignore[arg-type]


def _reply(text: str = '{"answer": "Paris"}', **kw: object) -> AiReply:
    return AiReply(status=200, text=text, **kw)  # type: ignore[arg-type]


class _Clock:
    """Each call advances by `step`, so every send takes exactly `step` seconds."""

    def __init__(self, step: float = 0.5) -> None:
        self.t, self.step = 0.0, step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def _capture(check: AiCheckKind = AiCheckKind.GROUND_TRUTH_ANSWER, *, send=None,
             prompts=("capital of France?",), approvals=None, redactor=None, **kw: object):
    return capture_run(
        project="demo", endpoint=URL, check=check, prompts=list(prompts),
        send=send or (lambda url, prompt: _reply()),
        approvals=[_approval()] if approvals is None else approvals,
        redactor=redactor or Redactor({"KEY": SECRET}), clock=kw.pop("clock", _Clock()),
        now=NOW, **kw)


def _judge(cap: AiCapture, judge: MockProvider | None = None, **kw: object):
    return judge_capture(cap, run_id="run_1", judge=judge or MockProvider(),
                         redactor=Redactor({"KEY": SECRET}), **kw)  # type: ignore[arg-type]


def _judgment(result: Result = Result.PASS, **kw: object) -> Judgment:
    base: dict[str, object] = {"result": result, "criteria_met": 2, "criteria_total": 2}
    base.update(kw)
    return Judgment(**base)  # type: ignore[arg-type]


# -- the capturer observes ----------------------------------------------------------------

def test_capture_records_facts_latency_and_scrubs_every_field() -> None:
    sent: list[tuple[str, str]] = []

    def send(url: str, prompt: str) -> AiReply:
        sent.append((url, prompt))
        return _reply(json.dumps({"answer": "Paris", "debug": SECRET}),
                      tools_called=["search"], handoffs=["router"])

    cap = _capture(AiCheckKind.RESPONSE_SHAPE, send=send, expected_keys=["answer", "sources"])
    assert sent == [(URL, "capital of France?")]
    ex = cap.exchanges[0]
    assert ex.latency_s == pytest.approx(0.5) and ex.status == 200 and ex.is_json
    assert ex.missing_keys == ["sources"] and ex.tools_called == ["search"]
    assert SECRET not in cap.model_dump_json() and "[REDACTED]" in ex.response


def test_capture_carries_no_judgement_field() -> None:
    cap = _capture()
    names = set(AiCapture.model_fields) | set(AiExchange.model_fields)
    assert not names & {"result", "verdict", "passed", "outcome", "score"}
    assert cap.unsent_prompts == 0


def test_capturer_source_never_constructs_a_verdict_or_result() -> None:
    text = (SRC / "stages" / "ai_capture.py").read_text(encoding="utf-8")
    assert not re.search(r"Result\.|Verdict\(", text)
    assert "grade" not in text.lower().replace("upgrade", "")


def test_a_send_failure_is_recorded_not_raised_and_names_no_value() -> None:
    def send(url: str, prompt: str) -> AiReply:
        raise ConnectionError(f"refused for {SECRET}")

    ex = _capture(send=send).exchanges[0]
    assert ex.status is None and ex.error and SECRET not in ex.error


def test_wall_clock_stops_the_capture_and_says_how_many_prompts_went_unsent() -> None:
    cap = _capture(prompts=["a", "b", "c", "d"], approvals=[_approval(wall_clock_s=1.5)],
                   wall_clock_s=1.5, clock=_Clock(step=0.5))
    assert 0 < len(cap.exchanges) < 4
    assert cap.unsent_prompts == 4 - len(cap.exchanges)


# -- the gates before anything is sent ----------------------------------------------------

def test_no_matching_approval_means_nothing_is_sent() -> None:
    sent: list[str] = []

    def send(url: str, prompt: str) -> AiReply:
        sent.append(prompt)
        return _reply()

    for approvals in ([], [_approval(target="https://other.test/chat")],
                      [_approval(run_kind=ApprovalKind.CRAWL)], [_approval(max_actions=0)]):
        with pytest.raises(ApprovalRequired):
            _capture(send=send, approvals=approvals)
    assert sent == []


def test_a_raw_secret_in_a_prompt_is_never_sent_to_the_endpoint() -> None:
    sent: list[str] = []

    def send(url: str, prompt: str) -> AiReply:
        sent.append(prompt)
        return _reply()

    with pytest.raises(CaptureWithheld):
        _capture(send=send, prompts=[f"my key is {SECRET}"])
    assert sent == []


def test_an_encoded_secret_surviving_the_scrub_withholds_the_capture() -> None:
    import base64
    encoded = base64.b64encode(SECRET.encode()).decode()
    with pytest.raises(CaptureWithheld) as err:
        _capture(send=lambda u, p: _reply(f'{{"answer": "{encoded}"}}'))
    assert SECRET not in str(err.value) and encoded not in str(err.value)


# -- AI6: judgement comes back from grade(), not from the capture ------------------------

def test_the_judged_verdict_comes_from_the_judge_not_the_capture(monkeypatch) -> None:
    cap = _capture(send=lambda u, p: _reply('{"answer": "Lyon"}'))
    fail = _judgment(Result.FAIL, criteria_met=1, failures=[Failure(
        criterion_id="AI-GT1", reason="wrong city", evidence_refs=["[network] response[0]"])])
    judge = MockProvider(responses={"judge": [fail]})
    verdict = _judge(cap, judge, reference="Paris")
    assert verdict.result is Result.FAIL and verdict.grader_provider == "mock"
    ok = MockProvider(responses={"judge": [_judgment(Result.PASS)]})
    assert _judge(_capture(), ok, reference="Paris").result is Result.PASS


def test_the_capture_is_handed_to_grade_unmodified(monkeypatch) -> None:
    import autotester.stages.ai_judge as module
    seen: list[object] = []
    real = module.grade

    def spy(rubric, raw, *args, **kwargs):
        seen.append(raw)
        return real(rubric, raw, *args, **kwargs)

    monkeypatch.setattr(module, "grade", spy)
    cap = _capture(send=lambda u, p: _reply("Paris is the capital.", tools_called=["wiki"]))
    judge = MockProvider(responses={"judge": [_judgment()]})
    _judge(cap, judge, reference="Paris")
    paths = [e.path for e in seen[0].evidence]  # type: ignore[attr-defined]
    assert "response[0]: Paris is the capital." in paths
    assert "prompt[0]: capital of France?" in paths


def test_judged_checks_that_need_a_reference_refuse_without_one() -> None:
    with pytest.raises(ValueError, match="reference"):
        _judge(_capture(), MockProvider())


def test_an_errored_capture_never_reaches_the_judge() -> None:
    def send(url: str, prompt: str) -> AiReply:
        raise TimeoutError("slow")

    judge = MockProvider(responses={"judge": [_judgment()]})
    verdict = _judge(_capture(send=send), judge, reference="Paris")
    assert verdict.result is Result.INCONCLUSIVE and judge.prompts == []


# -- computed checks: code decides from recorded facts, no judge --------------------------

def test_response_shape_is_computed_from_recorded_facts() -> None:
    good = _capture(AiCheckKind.RESPONSE_SHAPE, expected_keys=["answer"])
    bad = _capture(AiCheckKind.RESPONSE_SHAPE, expected_keys=["answer", "sources"])
    plain = _capture(AiCheckKind.RESPONSE_SHAPE, send=lambda u, p: _reply("not json"),
                     expected_keys=["answer"])
    judge = MockProvider()
    assert _judge(good, judge).result is Result.PASS
    assert _judge(bad, judge).result is Result.FAIL
    assert _judge(plain, judge).result is Result.FAIL
    v = _judge(bad, judge)
    assert v.grader_provider == "rule" and v.failures[0].evidence_refs
    assert judge.prompts == [], "a computed check never calls a model"


def test_latency_is_computed_against_the_budget_in_code() -> None:
    cap = _capture(AiCheckKind.LATENCY_BUDGET, clock=_Clock(step=2.0))
    judge = MockProvider()
    assert _judge(cap, judge, latency_budget_s=2.5).result is Result.PASS
    assert _judge(cap, judge, latency_budget_s=1.0).result is Result.FAIL
    assert judge.prompts == []
    with pytest.raises(ValueError, match="latency_budget_s"):
        _judge(cap, judge)


def test_a_failed_exchange_fails_the_latency_check() -> None:
    def send(url: str, prompt: str) -> AiReply:
        raise TimeoutError("slow")

    cap = _capture(AiCheckKind.LATENCY_BUDGET, send=send)
    assert _judge(cap, latency_budget_s=99).result is Result.FAIL


def test_an_empty_capture_is_inconclusive_never_a_pass() -> None:
    cap = _capture(AiCheckKind.RESPONSE_SHAPE, prompts=[], expected_keys=["answer"])
    assert _judge(cap).result is Result.INCONCLUSIVE


# -- AI7: nothing secret-shaped reaches the judge prompt ---------------------------------

def test_a_secret_in_the_target_response_never_reaches_the_judge_prompt() -> None:
    cap = _capture(send=lambda u, p: _reply(f"Paris. Also my key is {SECRET}"))
    judge = MockProvider(responses={"judge": [_judgment()]})
    _judge(cap, judge, reference="Paris")
    prompt = judge.prompts[0][1]
    assert SECRET not in prompt and "[REDACTED]" in prompt


def _by_hand(response: str) -> AiCapture:
    return AiCapture(project="demo", endpoint=URL, check=AiCheckKind.GROUND_TRUTH_ANSWER,
                     exchanges=[AiExchange(prompt="q", response=response, status=200,
                                           latency_s=0.1, is_json=False)])


def test_a_hand_built_capture_is_scrubbed_again_at_the_judge() -> None:
    judge = MockProvider(responses={"judge": [_judgment()]})
    _judge(_by_hand(f"key {SECRET}"), judge, reference=f"answer, key {SECRET}")
    assert SECRET not in judge.prompts[0][1]


def test_a_hand_built_capture_with_an_encoded_secret_never_reaches_the_judge() -> None:
    import base64
    judge = MockProvider(responses={"judge": [_judgment()]})
    with pytest.raises(CaptureWithheld):
        _judge(_by_hand(base64.b64encode(SECRET.encode()).decode()), judge, reference="Paris")
    assert judge.prompts == []


def test_module_exposes_no_second_grading_path() -> None:
    assert not hasattr(ai_capture, "grade")
