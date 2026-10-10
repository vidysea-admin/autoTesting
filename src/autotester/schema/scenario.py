"""A written scenario list, and what compiling it produced (T-166, EC4/EC5).

A scenario is an INPUT CONTRACT: every branch it enumerates (yes / no, each option) must
end up with a compiled case or be listed as uncovered — never silently dropped (O4).
`CompileResult` is the compiler's whole answer: the cases, the graph that traces them,
and the branches that have no case.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.case import Case
from autotester.schema.enums import CaseKind
from autotester.schema.portal_persona import KnowledgeGraph


class Branch(BaseModel):
    """One option of a scenario (the "yes" or the "no"): the data it changes in its flow
    and what it must show at the end."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    kind: CaseKind = CaseKind.EDGE
    values: dict[str, str] = Field(
        default_factory=dict,
        description="step target -> the value this branch types there (a profile-table row)")
    expect_text: list[str] = Field(
        default_factory=list, description="text the flow must end on screen showing")


class ScenarioSpec(BaseModel):
    """One declared scenario variant of a flow. Its own graph node and case set (EC4)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    flow_id: str
    name: str
    branches: list[Branch] = Field(min_length=1)

    @model_validator(mode="after")
    def _branch_ids_are_unique(self) -> ScenarioSpec:
        ids = [b.id for b in self.branches]
        if len(set(ids)) != len(ids):
            raise ValueError(f"scenario {self.id}: branch ids must be unique, got {ids}")
        return self


class UncoveredBranch(BaseModel):
    """A scenario branch that produced no case, with the one reason why (EC5)."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    branch_id: str
    reason: str


class CompileResult(BaseModel):
    """What `stages/eval_compiler.py::compile_evals` produced."""

    model_config = ConfigDict(extra="forbid")

    cases: list[Case] = Field(default_factory=list)
    graph: KnowledgeGraph = Field(default_factory=KnowledgeGraph)
    uncovered: list[UncoveredBranch] = Field(default_factory=list)
    total_branches: int = 0
    untraced_flows: list[str] = Field(
        default_factory=list,
        description="flows that produced no case because no graph edge resolves them (EC2)")

    @property
    def coverage(self) -> float:
        """Share of declared branches that compiled to a case; 1.0 only when none are uncovered."""
        if not self.total_branches:
            return 1.0
        return (self.total_branches - len(self.uncovered)) / self.total_branches
