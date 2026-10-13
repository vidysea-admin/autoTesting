"""The declared limits of an agent run and the rule that says whether it beat the pipeline
(T-181, AL11/AL13). One job: hold the configurable numbers, so no code carries a magic one.

Umesh has set NEITHER the budget number NOR the win rule yet (awaiting him): the defaults below
are conservative placeholders, overridable per run, and are named as such in the T-181 manifest.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.lead_loop import TokenBudget


class WinRule(BaseModel):
    """When the agent counts as a gain over the pipeline. Default (awaiting Umesh): the agent
    finds at least as many bugs at a false-positive rate no higher than the pipeline's, and
    stays inside its budget. `require_strict_gain` additionally demands a strict improvement on
    one axis (a tie is then no gain)."""

    model_config = ConfigDict(extra="forbid")

    min_bugs_delta: int = 0
    """Agent bugs minus pipeline bugs must be at least this."""
    max_fp_rate_delta: float = Field(default=0.0, ge=0)
    """Agent FP rate minus pipeline FP rate may be at most this."""
    require_strict_gain: bool = False


class AgentGuardrails(BaseModel):
    """Per-run ceilings: the token/cost budget (D-042) and the step cap. Domains and the write
    policy come from the project (`allowed_domains`, `write_policy`), never from here."""

    model_config = ConfigDict(extra="forbid")

    budget: TokenBudget = Field(default_factory=lambda: TokenBudget(
        max_tokens=200_000, max_cost_usd=2.0, usd_per_million_tokens=15.0))
    max_steps: int = Field(default=60, ge=1)
    """Graph steps before the run halts as `step_cap`."""
    win_rule: WinRule = Field(default_factory=WinRule)
