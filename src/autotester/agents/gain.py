"""The measured-gain harness (T-181, AL12/AL13): one corpus, two paths, one report.

It runs the plain pipeline and the guarded agent through caller-supplied runners (the live ones
are `stages/run_case_pipeline.py::run_and_grade_case` and `agents/lead_agent.py::run_lead_agent`;
tests pass fakes), times each, and hands both to `agents/comparison.py::compare` -- the one place
the four numbers and the verdict are made, scored by the one `stages/bench.py` scorer. The
agent always runs under `AgentGuardrails`; a budget or step-cap halt is carried into the verdict
as "no gain", stated, never dropped.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from autotester.agents import comparison
from autotester.schema.agent_comparison import Comparison
from autotester.schema.agent_guardrails import AgentGuardrails
from autotester.schema.bench import BenchCorpus
from autotester.schema.lead_loop import AgentRun
from autotester.schema.verdict import Verdict

PipelineRunner = Callable[[], list[Verdict]]
AgentRunner = Callable[[AgentGuardrails], tuple[AgentRun, list[Verdict]]]


def measure_gain(corpus: BenchCorpus, case_bug_map: dict[str, str], pipeline: PipelineRunner,
                 agent: AgentRunner, guardrails: AgentGuardrails | None = None, *,
                 pipeline_tokens: int | None = None, out: Path | None = None) -> Comparison:
    """Run both paths on the same corpus and return (and optionally write) the comparison."""
    rails = guardrails or AgentGuardrails()
    began = time.perf_counter()
    pipeline_verdicts = pipeline()
    pipeline_wall = time.perf_counter() - began
    began = time.perf_counter()
    agent_run, agent_verdicts = agent(rails)
    agent_wall = time.perf_counter() - began
    result = comparison.compare(
        corpus, case_bug_map, pipeline_verdicts, agent_verdicts, agent_run,
        pipeline_tokens=pipeline_tokens, pipeline_wall_s=pipeline_wall,
        agent_wall_s=agent_wall, rule=rails.win_rule)
    if out is not None:
        comparison.write_report(result, out)
    return result
