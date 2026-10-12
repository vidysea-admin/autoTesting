"""Checker B probe (run from a git-archive copy, placed in tests/): a secret-free RawResult of N evidence
rows through tools.dispatch. At c489e201 all 9 rows store the result; at 86d240a9 rows with >20 evidence
rows or long labels are withheld as SECRET and nothing is stored."""
from __future__ import annotations
import pytest
from test_agent_read_only import A, _one
from test_agent_tools import _case, _ctx, _grant, spies, Spies  # noqa
from autotester.agents import tools
from autotester.schema.enums import ApprovalKind, EvidenceKind, Outcome, WritePolicy
from autotester.schema.run import Evidence, RawResult

@pytest.mark.parametrize("n,label_len", [(5, 10), (15, 10), (20, 10), (21, 10), (25, 10), (40, 10), (5, 5000), (5, 12000), (5, 20000)])
def test_legit_result_not_withheld(tmp_path, spies, monkeypatch, n, label_len):
    ctx = _ctx(tmp_path / "data", spies, WritePolicy.ALLOW_WRITES)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    case = ctx.store.add_case(_case(_one(A.WAIT, "x")))
    ev = [Evidence(kind=EvidenceKind.DOM, path=f"p{i}", step_order=i, label="L" * label_len) for i in range(n)]
    monkeypatch.setattr(tools.execute, "run_case", lambda c, s: RawResult(case_id=case.id, outcome=Outcome.COMPLETED, evidence=ev))
    out = tools.dispatch(ctx, "run_case", {"case_id": case.id})
    assert out.ok, (out.refusal, out.summary)
