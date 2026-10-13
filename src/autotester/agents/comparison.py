"""Agent-vs-pipeline on one seeded corpus (T-179, AL12/AL13).

Both paths are scored by the ONE scorer (`stages/bench.py::run_autotester_trial` +
`scorecard`, never a number computed here) on the same `BenchCorpus`. The caller runs each path
(the plain pipeline: `stages/run_case_pipeline.py::run_and_grade_case`; the agent:
`agents/lead_agent.py::run_lead_agent`) and hands in what it produced plus its measured tokens
and wall time. The verdict line is always written, with both paths' four numbers: a gain is
FEWER missed bugs or fewer false positives with no more of the other, and only while the agent
run stayed inside its budget. Anything else is "no gain", stated, never dropped (AL13).
"""

from __future__ import annotations

import json
from pathlib import Path

from autotester.schema.agent_comparison import Comparison, PathMeasure
from autotester.schema.agent_guardrails import WinRule
from autotester.schema.bench import BenchCorpus
from autotester.schema.lead_loop import AgentRun
from autotester.schema.verdict import Verdict
from autotester.stages import bench


def measure(label: str, corpus: BenchCorpus, verdicts: list[Verdict], case_bug_map: dict[str, str],
            tokens: int | None, wall_s: float | None) -> PathMeasure:
    trial = bench.run_autotester_trial(f"cmp-{label}", corpus, verdicts, case_bug_map, wall_s,
                                       ordering="independent_parallel")
    card = bench.scorecard(corpus, [trial])[trial.participant_label or trial.participant.value]
    return PathMeasure(label=label, bugs_found=int(card["detected"] or 0),
                       false_positives=int(card["false_positives"] or 0),
                       false_positive_rate=float(card["false_positive_rate"] or 0.0),
                       tokens=tokens, wall_s=wall_s)


def _fmt(m: PathMeasure) -> str:
    tokens = "n/a" if m.tokens is None else str(m.tokens)
    wall = "n/a" if m.wall_s is None else f"{m.wall_s:.1f}s"
    return f"{m.label}: {m.bugs_found} bugs, {m.false_positives} false positives, " \
           f"{tokens} tokens, {wall}"


def compare(corpus: BenchCorpus, case_bug_map: dict[str, str], pipeline: list[Verdict],
            agent: list[Verdict], agent_run: AgentRun, *, pipeline_tokens: int | None = None,
            pipeline_wall_s: float | None = None, agent_wall_s: float | None = None,
            rule: WinRule | None = None) -> Comparison:
    """`rule` None is T-179's strict rule (a strict gain, no worse on the other axis); T-181
    passes the configured `WinRule` (`agents/gain.py`)."""
    base = measure("pipeline", corpus, pipeline, case_bug_map, pipeline_tokens, pipeline_wall_s)
    lead = measure("agent", corpus, agent, case_bug_map, agent_run.tokens_used, agent_wall_s)
    in_budget = agent_run.stopped != "budget_exceeded"
    better = lead.bugs_found > base.bugs_found or lead.false_positives < base.false_positives
    worse = lead.bugs_found < base.bugs_found or lead.false_positives > base.false_positives
    if rule is None:
        gain = in_budget and better and not worse
    else:
        ok = (lead.bugs_found - base.bugs_found >= rule.min_bugs_delta
              and lead.false_positive_rate - base.false_positive_rate <= rule.max_fp_rate_delta)
        worse = not ok
        gain = in_budget and ok and (better or not rule.require_strict_gain)
    if gain:
        why = "more bugs found or fewer false positives, within budget"
    elif not in_budget:
        why = "the agent run breached its budget"
    elif worse:
        why = "the agent did worse than the win rule allows on bugs found or false positives"
    else:
        why = "the agent found no more bugs and no fewer false positives"
    line = f"{'GAIN' if gain else 'NO GAIN'} ({why}) | {_fmt(base)} | {_fmt(lead)}"
    return Comparison(corpus_id=corpus.id, pipeline=base, agent=lead,
                      agent_stopped=agent_run.stopped, verdict="gain" if gain else "no_gain",
                      verdict_line=line)


def write_report(comparison: Comparison, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(comparison.model_dump(mode="json"), indent=2), encoding="utf-8")
    return out
