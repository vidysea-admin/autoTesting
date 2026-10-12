"""T-179a fix cycle 2, FAILED-2 (AL6): the credential gate runs over DECODED string values, not
over JSON text (where a TAB or LF is the two characters `\\t`, and a control character is
`\\uXXXX`, so the fold never saw the separator). Also: a blank FILL is not a credential entry, and
an encoded or cut-off secret in an error text is withheld. Offline; fake canary secrets only."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest
from test_agent_read_only import RO, A, _one, _run
from test_agent_tools import (
    RAW,
    Spies,
    _case,
    _ctx,
    _go,
    _grant,
    spies,  # noqa: F401  (the fixture the `spy` wrapper below asks for)
)

from autotester.agents import tools
from autotester.schema.agent_layer import AgentToolName, RefusalClass, ToolOutcome
from autotester.schema.enums import ApprovalKind, EvidenceKind, Outcome, Result, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.run import Evidence, RawResult
from autotester.schema.verdict import Verdict

BS = chr(92)
HEAD, TAIL = RAW[:6], RAW[6:]
_SEPS = ["\t", "\n", "\r", "\r\n", "\x0b", "\x00", BS + "u0009", BS + "u000a"]
_WHERE = ["error", "hitl_prompt", "evidence.label", "stage_error", "summary"]


@pytest.fixture
def spy(spies: Spies) -> Spies:  # noqa: F811
    return spies


def disk_hits(root: Path, *needles: str) -> list[Path]:
    """Every file under `root` whose bytes contain any needle."""
    found = [n.encode() for n in needles]
    return [p for p in root.rglob("*") if p.is_file()
            and any(n in p.read_bytes() for n in found)]


def _stage(where: str, text: str, case_id: str) -> Any:
    if where == "error":
        return RawResult(case_id=case_id, outcome=Outcome.ERRORED, error=text)
    if where == "hitl_prompt":
        return RawResult(case_id=case_id, outcome=Outcome.ERRORED, hitl_prompt=text)
    return RawResult(case_id=case_id, outcome=Outcome.COMPLETED, evidence=[
        Evidence(kind=EvidenceKind.URL, path="u", label=text)])


def _arm(tmp: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch, where: str, text: str) -> Any:
    ctx = _ctx(tmp / "data", spy, WritePolicy.ALLOW_WRITES)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    case = ctx.store.add_case(_case(_one(A.WAIT, "x")))
    if where == "stage_error":
        def boom(c: Any, s: Any) -> Any:
            raise RuntimeError(text)
        monkeypatch.setattr(tools.execute, "run_case", boom)
    elif where == "summary":
        monkeypatch.setitem(tools._HANDLERS, AgentToolName.RUN_CASE, lambda c, a: ToolOutcome(
            tool="run_case", ok=True, summary=text))
    else:
        monkeypatch.setattr(tools.execute, "run_case", lambda c, s: _stage(where, text, case.id))
    return ctx, case


def test_the_disk_search_finds_a_planted_needle_so_an_empty_result_means_something(
        tmp_path: Path) -> None:
    (tmp_path / "control").mkdir()
    (tmp_path / "control" / "planted.json").write_bytes(f'{{"e":"{TAIL}"}}'.encode())
    (tmp_path / "control" / "clean.json").write_bytes(b'{"e":"nothing"}')
    assert [p.name for p in disk_hits(tmp_path, TAIL)] == ["planted.json"]


@pytest.mark.parametrize("sep", _SEPS, ids=[repr(s) for s in _SEPS])
@pytest.mark.parametrize("where", _WHERE)
def test_a_credential_split_by_a_separator_is_withheld_and_never_stored(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch, where: str, sep: str) -> None:
    ctx, case = _arm(tmp_path, spy, monkeypatch, where, HEAD + sep + TAIL)
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.ok is False and out.refusal is RefusalClass.SECRET
    assert HEAD not in out.model_dump_json() and TAIL not in out.model_dump_json()
    assert ctx.store.load_results("run-1") == []
    assert disk_hits(tmp_path / "data", HEAD, TAIL) == []


@pytest.mark.parametrize("where", _WHERE)
@pytest.mark.parametrize("decoy", [
    f"{HEAD}\t{TAIL[:-1]}0", f"{HEAD}\n2 raw", HEAD, f"{HEAD}x{TAIL}", "Hunter two raw value 9137",
    f"{TAIL[:-4]}\n"])
def test_a_near_miss_of_the_fold_is_not_refused(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch,
        where: str, decoy: str) -> None:
    ctx, case = _arm(tmp_path, spy, monkeypatch, where, decoy)
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.refusal is not RefusalClass.SECRET


def test_a_split_secret_in_a_verdict_is_withheld_before_the_write(
        tmp_path: Path, spy: Spies) -> None:
    ctx = _ctx(tmp_path, spy)
    leak = Verdict(run_id="run-1", case_id="c", result=Result.PASS, note=HEAD + "\t" + TAIL)
    with pytest.raises(tools._Refused) as err:
        tools._withhold_if_credential(ctx, leak)
    assert err.value.kind is RefusalClass.SECRET


@pytest.mark.parametrize("where", ["error", "evidence.label", "summary"])
def test_a_result_beyond_the_size_caps_is_withheld_not_skipped(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch, where: str) -> None:
    ctx, case = _arm(tmp_path, spy, monkeypatch, where, "a" * 20_000)
    if where == "evidence.label":  # 256 nodes: many small rows
        many = RawResult(case_id=case.id, outcome=Outcome.COMPLETED, evidence=[
            Evidence(kind=EvidenceKind.URL, path="u") for _ in range(40)])
        monkeypatch.setattr(tools.execute, "run_case", lambda c, s: many)
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.ok is False and out.refusal is RefusalClass.SECRET
    assert ctx.store.load_results("run-1") == []


# -- an encoded, transformed or cut-off secret in an error text ----------------------------------
_B64 = base64.b64encode(RAW.encode()).decode()


@pytest.mark.parametrize("text", [
    f"login failed for {_B64}", f"saw {RAW.encode().hex()}", f"saw {RAW[::-1]}",
    "x" * 270 + _B64,  # the encoded form straddles the 300-character cut of an error text
    "x" * 295 + RAW[::-1]])
def test_an_error_text_with_a_transformed_secret_is_withheld_whole(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    ctx, case = _arm(tmp_path, spy, monkeypatch, "stage_error", text)
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.refusal is RefusalClass.SECRET
    assert _B64[:12] not in out.model_dump_json() and RAW[::-1][:8] not in out.model_dump_json()


# -- a blank FILL is not a credential entry ------------------------------------------------------
@pytest.mark.parametrize("blank", ["   ", "\t", " \n "])
def test_a_blank_fill_does_not_arm_the_login_submit_at_read_only(
        tmp_path: Path, spy: Spies, blank: str) -> None:
    steps = [Step(order=1, action=A.FILL, target="Email", value=blank),
             Step(order=2, action=A.CLICK, target="Sign in")]
    _, out = _run(tmp_path, spy, RO, steps, login=True)
    assert out.refusal is RefusalClass.WRITE_POLICY and "step 1" in out.summary
    assert spy.sessions == 0 and spy.count("run_case") == 0
