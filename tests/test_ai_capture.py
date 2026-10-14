"""Offline behavioural capture and judgment tests: ai-target AI6-AI7, core C5/C7, D-018."""
from __future__ import annotations

import base64
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from run_approval_fixture import project_of

from autotester.core.consent import ApprovalRequired
from autotester.core.redact import Redactor
from autotester.providers.mock import MockProvider
from autotester.schema.ai_check import AiCapture, AiCheckKind, AiExchange, AiReply
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind, Outcome, Result
from autotester.schema.verdict import Failure, Judgment
from autotester.stages import ai_capture
from autotester.stages.ai_capture import CaptureWithheld, capture_run
from autotester.stages.ai_judge import judge_capture

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
URL = "https://llm.test/chat"
NOW, SECRET = datetime(2026, 10, 7, tzinfo=UTC), "sk-live-1234567890abcdef"
def _approval(**kw: object) -> RunApproval:
    fields: dict[str, object] = {
        "project": "demo", "run_kind": ApprovalKind.LIVE_CASE, "target": URL,
        "scope": "behavioural capture of the chat endpoint", "max_actions": 10, "max_probes": 1,
        "wall_clock_s": 60.0, "granted_by": "umesh", "granted_at": "2026-10-01",
        "expires_at": "2026-12-01"}
    return RunApproval(**{**fields, **kw}).sign()  # type: ignore[arg-type]
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
    return capture_run(project=project_of(kw.pop("project", "demo")),
        endpoint=kw.pop("endpoint", URL), check=check, prompts=list(prompts),
        send=send or (lambda url, prompt: _reply()), clock=kw.pop("clock", _Clock()),
        approvals=[_approval()] if approvals is None else approvals,
        redactor=redactor or Redactor({"KEY": SECRET}), now=NOW, **kw)
def _judge(cap: AiCapture, judge: MockProvider | None = None, **kw: object):
    return judge_capture(cap, run_id="run_1", judge=judge or MockProvider(),
                         redactor=Redactor({"KEY": SECRET}), **kw)  # type: ignore[arg-type]
def _judgment(result: Result = Result.PASS, **kw: object) -> Judgment:
    base: dict[str, object] = {"result": result, "criteria_met": 2, "criteria_total": 2}
    return Judgment(**{**base, **kw})  # type: ignore[arg-type]
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
    assert AiCapture.model_validate_json(cap.model_dump_json()) == cap
    for model, data in ((AiReply, {}), (AiExchange, {"prompt": "q", "latency_s": 0.0}),
            (AiCapture, {"project": "demo", "endpoint": URL, "check": AiCheckKind.TOOL_USE})):
        with pytest.raises(ValueError):
            model.model_validate({**data, "result": "pass"})
    for latency in (None, -1, float("nan"), float("inf"), -float("inf")):
        data = {"prompt": "q", **({"latency_s": latency} if latency is not None else {})}
        with pytest.raises(ValueError):
            AiExchange.model_validate(data)
    zero = AiExchange(prompt="q", latency_s=0.0)
    assert AiExchange.model_validate_json(zero.model_dump_json()).latency_s == 0.0
    with pytest.raises(ValueError):
        AiCapture(project="demo", endpoint=URL, check=AiCheckKind.TOOL_USE, unsent_prompts=-1)
def test_capturer_source_never_constructs_a_verdict_or_result() -> None:
    text = (SRC / "stages" / "ai_capture.py").read_text(encoding="utf-8")
    assert not re.search(r"Result\.|Verdict\(", text)
    assert "grade" not in text.lower().replace("upgrade", "")
def test_a_send_failure_is_recorded_not_raised_and_names_no_value() -> None:
    def send(url: str, prompt: str) -> AiReply:
        raise type(f"Error_{SECRET}", (ConnectionError,), {})(f"refused for {SECRET}")
    ex = _capture(send=send).exchanges[0]
    assert ex.status is None and ex.error and SECRET not in ex.error
    assert ex.error == "transport_error"
def test_wall_clock_stops_the_capture_and_says_how_many_prompts_went_unsent() -> None:
    cap = _capture(prompts=["a", "b", "c", "d"], approvals=[_approval(wall_clock_s=1.5)],
                   wall_clock_s=1.5, clock=_Clock(step=0.5))
    assert 0 < len(cap.exchanges) < 4
    assert cap.unsent_prompts == 4 - len(cap.exchanges)
def test_no_matching_approval_means_nothing_is_sent() -> None:
    sent: list[str] = []
    def send(url: str, prompt: str) -> AiReply:
        sent.append(prompt)
        return _reply()
    invalid = _approval().model_copy(update={"signature": "bad"})
    for approvals in ([], [_approval(target="https://other.test/chat")],
                      [_approval(run_kind=ApprovalKind.CRAWL)], [_approval(max_actions=0)],
                      [invalid], [_approval(expires_at="2026-01-01")],
                      [_approval(project="other")], [_approval(wall_clock_s=59)]):
        with pytest.raises(ApprovalRequired):
            _capture(send=send, approvals=approvals)
    with pytest.raises(ApprovalRequired, match="actions 2 > approved 1"):
        _capture(send=send, prompts=["a", "b"], approvals=[_approval(max_actions=1)])
    with pytest.raises(ApprovalRequired, match="production"):
        _capture(send=send, approvals=[_approval(production=False)], production=True)
    assert sent == []
@pytest.mark.parametrize("spelling", [SECRET, base64.b64encode(SECRET.encode()).decode(),
                                     SECRET.upper(), SECRET[::-1]])
@pytest.mark.parametrize("location", ["first", "later", "endpoint", "project", "approval"])
@pytest.mark.parametrize("matching", [False, True])
def test_a_raw_secret_in_a_prompt_is_never_sent_to_the_endpoint(spelling, location, matching):
    sent: list[str] = []
    def send(url: str, prompt: str) -> AiReply:
        sent.append(prompt)
        return _reply()
    endpoint = URL + "/" + spelling if location == "endpoint" else URL
    project = spelling if location == "project" else "demo"
    prompts = ([spelling] if location == "first" else
               ["safe", spelling] if location == "later" else ["safe"])
    approval = _approval(target=endpoint if matching else URL,
                         project=project if matching else "demo")
    if location == "approval":
        approval = approval.model_copy(update={"id": spelling})
    with pytest.raises(CaptureWithheld) as err:
        _capture(send=send, endpoint=endpoint, project=project,
                 prompts=prompts, approvals=[approval])
    assert sent == []
    assert str(err.value) == "capture input carries a secret value; nothing was sent"
    assert SECRET not in str(err.value) and spelling not in str(err.value)
    assert err.value.__cause__ is None and err.value.__suppress_context__
def test_an_encoded_secret_surviving_the_scrub_withholds_the_capture() -> None:
    encoded = base64.b64encode(SECRET.encode()).decode()
    with pytest.raises(CaptureWithheld) as err:
        _capture(send=lambda u, p: _reply(f'{{"answer": "{encoded}"}}'))
    assert SECRET not in str(err.value) and encoded not in str(err.value)
def test_the_judged_verdict_comes_from_the_judge_not_the_capture(monkeypatch) -> None:
    cap = _capture(send=lambda u, p: _reply('{"answer": "Lyon"}'))
    fail = _judgment(Result.FAIL, criteria_met=1, failures=[Failure(
        criterion_id="AI-GT1", reason="wrong city", evidence_refs=["[network] response[0]"])])
    judge = MockProvider(responses={"judge": [fail]})
    verdict = _judge(cap, judge, reference="Paris")
    assert verdict.result is Result.FAIL and verdict.grader_provider == "mock"
    ok = MockProvider(responses={"judge": [_judgment(Result.PASS)]})
    assert _judge(_capture(), ok, reference="Paris").result is Result.PASS
@pytest.mark.parametrize("check", list(AiCheckKind))
@pytest.mark.parametrize("mixed", [False, True])
def test_the_capture_is_handed_to_grade_unmodified(monkeypatch, check, mixed) -> None:
    import autotester.stages.ai_judge as module
    seen, real = [], module.grade
    def spy(rubric, raw, *args, **kwargs):
        verdict = real(rubric, raw, *args, **kwargs)
        seen.append((rubric, raw, args[1], verdict))
        return verdict
    monkeypatch.setattr(module, "grade", spy)
    def send(url, prompt):
        if prompt == "failed":
            raise TimeoutError("synthetic transport failure")
        return _reply("Paris is the capital.", tools_called=["wiki", "lookup"],
                      handoffs=["router", "researcher", "writer"])
    cap = _capture(check, send=send, prompts=["capital of France?"] + (["failed"] if mixed else []))
    judge = MockProvider(responses={"judge": [_judgment()]})
    verdict = _judge(cap, judge, reference="Paris", latency_budget_s=1)
    rubric, raw, adapter, returned = seen[0]
    assert verdict is returned and raw.outcome is Outcome.COMPLETED
    assert rubric.case_id == raw.case_id == verdict.case_id
    assert verdict.rubric_hash == rubric.fingerprint
    paths = [e.path for e in raw.evidence]
    assert "response[0]: Paris is the capital." in paths
    assert "prompt[0]: capital of France?" in paths
    assert any(p.startswith("exchange[0]: status=200 error=None latency_s=0.5") for p in paths)
    if mixed:
        assert len(cap.exchanges) == 2 and cap.unsent_prompts == 0
        assert cap.exchanges[1].error == "transport_error"
        failed = ("exchange[1]: status=None error=transport_error latency_s=0.5 "
                  "is_json=False missing_keys=[]")
        assert failed in paths
    if check in (AiCheckKind.RESPONSE_SHAPE, AiCheckKind.LATENCY_BUDGET):
        assert adapter.id == "rule" and adapter.usage == [] and adapter.trace is None
        assert judge.prompts == [] and judge.usage == []
        if mixed:
            assert verdict.result is Result.FAIL
    else:
        assert adapter is judge and judge.prompts
        if mixed:
            assert failed in judge.prompts[0][1]
        if check is AiCheckKind.TOOL_USE:
            assert "tools_called[0]: wiki, lookup" in judge.prompts[0][1]
        if check is AiCheckKind.HANDOFF_ORDER:
            assert "handoffs[0]: router > researcher > writer" in judge.prompts[0][1]
    assert AiCapture.model_validate_json(cap.model_dump_json()) == cap
    assert type(verdict).model_validate_json(verdict.model_dump_json()) == verdict
def test_judged_checks_that_need_a_reference_refuse_without_one() -> None:
    with pytest.raises(ValueError, match="reference"):
        _judge(_capture(), MockProvider(responses={"judge": [_judgment()]}))
def test_an_errored_capture_never_reaches_the_judge() -> None:
    def send(url: str, prompt: str) -> AiReply:
        raise TimeoutError("slow")
    judge = MockProvider(responses={"judge": [_judgment()]})
    verdict = _judge(_capture(send=send), judge, reference="Paris")
    assert verdict.result is Result.INCONCLUSIVE and judge.prompts == []
@pytest.mark.parametrize("text", ["not json", "[]"])
def test_response_shape_is_computed_from_recorded_facts(text) -> None:
    good = _capture(AiCheckKind.RESPONSE_SHAPE, expected_keys=["answer"])
    bad = _capture(AiCheckKind.RESPONSE_SHAPE, expected_keys=["answer", "sources"])
    plain = _capture(AiCheckKind.RESPONSE_SHAPE, send=lambda u, p: _reply(text),
                     expected_keys=["answer"])
    judge = MockProvider()
    assert _judge(good, judge).result is Result.PASS
    assert _judge(bad, judge).result is Result.FAIL
    assert not plain.exchanges[0].is_json and _judge(plain, judge).result is Result.FAIL
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
    untimed = cap.model_dump(mode="json")
    del untimed["exchanges"][0]["latency_s"]
    with pytest.raises(ValueError):
        AiCapture.model_validate(untimed)
    zero = cap.model_copy(update={"exchanges": [AiExchange(prompt="q", status=200, latency_s=0)]})
    assert _judge(zero, judge, latency_budget_s=0).result is Result.PASS
    assert _judge(cap, judge, latency_budget_s=0).result is Result.FAIL
    assert judge.prompts == []
def test_a_failed_exchange_fails_the_latency_check() -> None:
    def send(url: str, prompt: str) -> AiReply:
        raise TimeoutError("slow")
    cap = _capture(AiCheckKind.LATENCY_BUDGET, send=send)
    assert _judge(cap, latency_budget_s=99).result is Result.FAIL
def test_an_empty_capture_is_inconclusive_never_a_pass() -> None:
    cap = _capture(AiCheckKind.RESPONSE_SHAPE, prompts=[], expected_keys=["answer"])
    assert _judge(cap).result is Result.INCONCLUSIVE
@pytest.mark.parametrize("check", [AiCheckKind.GROUND_TRUTH_ANSWER,
                                  AiCheckKind.TOOL_USE, AiCheckKind.HANDOFF_ORDER])
def test_a_secret_in_the_target_response_never_reaches_the_judge_prompt(check) -> None:
    cap = _capture(check, send=lambda u, p: _reply(f"Paris. Also my key is {SECRET}",
                   tools_called=["search", SECRET], handoffs=["router", SECRET, "writer"]))
    judge = MockProvider(responses={"judge": [_judgment()]})
    _judge(cap, judge, reference="Paris")
    prompt = judge.prompts[0][1]
    assert SECRET not in prompt and "response[0]: Paris. Also my key is [REDACTED]:KEY" in prompt
    if check is AiCheckKind.TOOL_USE:
        assert "tools_called[0]: search, [REDACTED]:KEY" in prompt
    if check is AiCheckKind.HANDOFF_ORDER:
        assert "handoffs[0]: router > [REDACTED]:KEY > writer" in prompt
def _by_hand(response: str) -> AiCapture:
    return AiCapture(project="demo", endpoint=URL, check=AiCheckKind.GROUND_TRUTH_ANSWER,
    exchanges=[AiExchange(prompt="q", response=response, status=200, latency_s=0.1, is_json=False)])
@pytest.mark.parametrize("check", [AiCheckKind.GROUND_TRUTH_ANSWER,
                                  AiCheckKind.TOOL_USE, AiCheckKind.HANDOFF_ORDER])
def test_a_hand_built_capture_is_scrubbed_again_at_the_judge(check) -> None:
    judge = MockProvider(responses={"judge": [_judgment()]})
    cap = _by_hand(f"key {SECRET}")
    cap.check = check
    cap.exchanges[0].tools_called = ["search", SECRET]
    cap.exchanges[0].handoffs = ["router", SECRET, "writer"]
    _judge(cap, judge, reference=f"answer, key {SECRET}")
    assert SECRET not in judge.prompts[0][1]
    reference_judge = MockProvider(responses={"judge": [_judgment()]})
    _judge(cap.model_copy(update={"check": AiCheckKind.GROUND_TRUTH_ANSWER}),
           reference_judge, reference=f"answer, key {SECRET}")
    assert SECRET not in reference_judge.prompts[0][1]
    assert "answer, key [REDACTED]:KEY" in reference_judge.prompts[0][1]
    if check is AiCheckKind.TOOL_USE:
        assert "tools_called[0]: search, [REDACTED]:KEY" in judge.prompts[0][1]
    if check is AiCheckKind.HANDOFF_ORDER:
        assert "handoffs[0]: router > [REDACTED]:KEY > writer" in judge.prompts[0][1]
@pytest.mark.parametrize("field", ["response", "tools_called", "handoffs", "reference", "rubric"])
def test_a_hand_built_capture_with_an_encoded_secret_never_reaches_the_judge(field, monkeypatch):
    import autotester.stages.ai_judge as module
    judge = MockProvider(responses={"judge": [_judgment()]})
    encoded = base64.b64encode(SECRET.encode()).decode()
    cap, reference = _by_hand("Paris"), "Paris"
    if field == "reference":
        reference = encoded
    elif field == "rubric":
        monkeypatch.setitem(module._CRITERIA, cap.check, [("AI-GT1", encoded)])
    else:
        setattr(cap.exchanges[0], field, encoded if field == "response" else [encoded])
    with pytest.raises(CaptureWithheld):
        _judge(cap, judge, reference=reference)
    assert judge.prompts == []
def test_module_exposes_no_second_grading_path() -> None:
    assert not hasattr(ai_capture, "grade")
