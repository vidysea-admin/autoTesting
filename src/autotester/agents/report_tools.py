"""The two remaining read tools of the lead tester (T-179, AL2): `report` and `capture_network`.

Each is a thin call into an existing stage (C3): `report` wraps `stages/unified_report.py::
build_report`; `capture_network` re-reads one executed case's stored network evidence through
`stages/network_capture.py::first_party_evidence`, the one first-party filter (T-170). Neither
opens a browser, writes, or assigns a verdict. Registered into the one dispatcher
(`agents/tools.py`), so the secret gate and the scrub apply to what they return.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from autotester.agents.context import AgentContext
from autotester.schema.agent_layer import (
    AgentToolName as Name,
)
from autotester.schema.agent_layer import (
    EmptyArgs,
    ReadCaseArgs,
    RefusalClass,
    ToolEffect,
    ToolOutcome,
    ToolSpec,
)
from autotester.schema.enums import EvidenceKind
from autotester.stages import explore_safety, network_capture, unified_report

SPECS: dict[Name, ToolSpec] = {
    Name.REPORT: ToolSpec(
        name=Name.REPORT, effect=ToolEffect.READ,
        wraps="autotester.stages.unified_report.build_report",
        description="Summarise this run's unified report: flows, issues, coverage."),
    Name.CAPTURE_NETWORK: ToolSpec(
        name=Name.CAPTURE_NETWORK, effect=ToolEffect.READ,
        wraps="autotester.stages.network_capture.first_party_evidence",
        description="List the first-party network calls stored for one executed case."),
}
ARGS: dict[Name, type[BaseModel]] = {Name.REPORT: EmptyArgs, Name.CAPTURE_NETWORK: ReadCaseArgs}
_CALL = re.compile(r"^(\S+) (\S+) -> (\d{3})$")


def _report(ctx: AgentContext, _args: EmptyArgs) -> ToolOutcome:
    try:
        rep = unified_report.build_report(ctx.store, ctx.run_id)
    except unified_report.ReportUnavailable:
        return ToolOutcome(tool="report", ok=False, refusal=RefusalClass.NOTHING_TO_DO,
                           summary="no run to report on yet")
    return ToolOutcome(tool="report", ok=True, artifact_ref=f"report:{rep.run_id}",
                       summary=f"{len(rep.regression.flows)} flows, "
                               f"{len(rep.regression.issues)} release issues")


def _capture_network(ctx: AgentContext, args: ReadCaseArgs) -> ToolOutcome:
    result = next((r for r in ctx.store.load_results(ctx.run_id) if r.case_id == args.case_id),
                  None)
    if result is None:
        return ToolOutcome(tool="capture_network", ok=False, refusal=RefusalClass.NOTHING_TO_DO,
                           summary="no stored result for that case")
    seen = [m.groups() for e in result.evidence if e.kind is EvidenceKind.NETWORK
            if (m := _CALL.match(e.path))]
    calls = [(a, b, int(c)) for a, b, c in seen]
    kept = network_capture.first_party_evidence(
        calls, ctx.project, explore_safety.policy_for(ctx.project), ctx.secrets.redactor())
    bad = sum(1 for _, _, status in calls if status >= 400)
    return ToolOutcome(tool="capture_network", ok=True, artifact_ref=f"network:{args.case_id}",
                       summary=f"{len(kept)} first-party calls, {bad} with status >= 400")


HANDLERS: dict[Name, Callable[[AgentContext, Any], ToolOutcome]] = {
    Name.REPORT: _report, Name.CAPTURE_NETWORK: _capture_network,
}
