"""Checker B probe (placed in tests/ of a git-archive copy): separator-split fake canary RAW in 9 result
locations x 37 separators x 6 cut points = 1,998 dispatches; oracle = ctx.secrets.guard_prompt(text).
Result at 86d240a9: 0 leaks, 0 over-withholds (also reversed/b64/hex forms, 4 Verdict fields)."""
from __future__ import annotations
import pytest
from test_agent_read_only import A, _one
from test_agent_tools import RAW, _case, _ctx, _grant, spies, Spies  # noqa
from autotester.agents import tools
from autotester.schema.agent_layer import AgentToolName, RefusalClass, ToolOutcome
from autotester.schema.enums import ApprovalKind, EvidenceKind, Outcome, WritePolicy
from autotester.schema.run import Evidence, RawResult

SEPS = ["\t", "\n", "\r", "\r\n", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x1f", "\x85", "\xa0", "\u1680", "\u2000", "\u2003", "\u2028",
        "\u2029", "\u202f", "\u205f", "\u3000", "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad", "\x00", "\x7f", " ", "  ",
        " \t\n ", "\t", "\n", "\u0009", "\u000a", "\u00ad", "\u200b"]
WHERE = ["error", "hitl_prompt", "not_run_reason", "log_ref", "ev.label", "ev.path", "ev.label.manyrows", "stage_error", "summary"]

def mk(where, text, cid):
    if where == "error": return RawResult(case_id=cid, outcome=Outcome.ERRORED, error=text)
    if where == "hitl_prompt": return RawResult(case_id=cid, outcome=Outcome.ERRORED, hitl_prompt=text)
    if where == "not_run_reason": return RawResult(case_id=cid, outcome=Outcome.NOT_RUN, not_run_reason=text)
    if where == "log_ref": return RawResult(case_id=cid, outcome=Outcome.COMPLETED, log_ref=text)
    if where == "ev.path": return RawResult(case_id=cid, outcome=Outcome.COMPLETED, evidence=[Evidence(kind=EvidenceKind.URL, path=text)])
    if where == "ev.label.manyrows":
        ev = [Evidence(kind=EvidenceKind.URL, path="u%d" % i) for i in range(5)] + [Evidence(kind=EvidenceKind.URL, path="u", label=text)]
        return RawResult(case_id=cid, outcome=Outcome.COMPLETED, evidence=ev)
    return RawResult(case_id=cid, outcome=Outcome.COMPLETED, evidence=[Evidence(kind=EvidenceKind.URL, path="u", label=text)])

def arm(tmp, spy, mp, where, text):
    ctx = _ctx(tmp / "data", spy, WritePolicy.ALLOW_WRITES)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    case = ctx.store.add_case(_case(_one(A.WAIT, "x")))
    if where == "stage_error":
        def boom(c, s): raise RuntimeError(text)
        mp.setattr(tools.execute, "run_case", boom)
    elif where == "summary":
        mp.setitem(tools._HANDLERS, AgentToolName.RUN_CASE, lambda c, a: ToolOutcome(tool="run_case", ok=True, summary=text))
    else:
        mp.setattr(tools.execute, "run_case", lambda c, s: mk(where, text, case.id))
    return ctx, case

@pytest.mark.parametrize("where", WHERE)
def test_split_matrix(tmp_path, spies, monkeypatch, where):
    bad = []
    for i, sep in enumerate(SEPS):
        for cut in [1, 3, 6, 11, 16, 21]:
            text = "see " + RAW[:cut] + sep + RAW[cut:] + " end"
            ctx, case = arm(tmp_path / f"{i}-{cut}", spies, monkeypatch, where, text)
            try:
                ctx.secrets.guard_prompt(text); caught = False
            except ValueError:
                caught = True
            out = tools.dispatch(ctx, "run_case", {"case_id": case.id})
            blob = out.model_dump_json()
            leaked = (RAW[:cut] in blob and cut > 3) or (RAW[cut:] in blob and len(RAW[cut:]) > 3)
            if caught and (out.refusal is not RefusalClass.SECRET or ctx.store.load_results("run-1") or leaked):
                bad.append(("LEAK", repr(sep), cut))
            if not caught and out.refusal is RefusalClass.SECRET:
                bad.append(("OVER-WITHHOLD", repr(sep), cut))
    assert not bad, bad[:6]
