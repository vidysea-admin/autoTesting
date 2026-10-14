"""A test case — one falsifiable claim about the product, plus how to check it."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.core.ids import content_id
from autotester.schema.base import Artifact
from autotester.schema.enums import Action, CaseClass, CaseKind, CaseStatus, Severity
from autotester.schema.flowspec import FlowSpec, Step
from autotester.schema.user_persona import PERSONA_ID_PATTERN

CasePriority = Literal["p0", "p1", "p2", "p3"]


class Case(Artifact):
    """One generated or hand-written test case.

    Cases are content-addressed: the same flow + class + steps always produces
    the same id, so regenerating a flowspec does not duplicate the suite.
    """

    id: str = ""
    project: str
    flow_id: str
    kind: CaseKind
    case_class: CaseClass
    title: str
    rationale: str | None = Field(default=None, description="why this case is worth running")
    preconditions: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    severity: Severity = Severity.S2
    rubric_ref: str | None = None
    script_ref: str | None = None
    user_persona_ref: str | None = Field(
        default=None, pattern=PERSONA_ID_PATTERN,
        description="T-190/PU1: advisory UserPersona override for this case, by id. By-reference "
                    "like rubric_ref; not in compute_id and never read by grading (PU4)",
    )
    provenance: str | None = Field(
        default=None,
        description="D-097: set when the case came from an unreviewed DRAFT flow "
                    "(source_id + 'from unreviewed DRAFT flow'); not in compute_id",
    )
    status: CaseStatus = CaseStatus.PROPOSED
    priority: CasePriority = Field(default="p2", description="Legacy defaults to p2; pinned is p0")
    pinned: bool = Field(
        default=False,
        description="AT-585: confirmed-issue regression, always p0 and included in every "
                    "priority selection. ProjectStore.delete_case refuses to prune it.",
    )
    pinned_issue_id: str | None = Field(
        default=None,
        description="Traceability to the Issue this case was pinned from. "
                     "Never a new CaseClass member -- D-005/D-014 keep "
                     "CaseClass closed; Issue stays a separate artifact.",
    )

    @model_validator(mode="after")
    def _pinned_issue_id_needs_the_flag(self) -> Case:
        if self.pinned_issue_id and not self.pinned:
            raise ValueError("pinned_issue_id is set but pinned is False")
        if self.pinned:
            object.__setattr__(self, "priority", "p0")
        return self

    def model_post_init(self, _context: object) -> None:
        if not self.id:
            object.__setattr__(self, "id", self.compute_id())

    def compute_id(self) -> str:
        payload = {
            "project": self.project,
            "flow_id": self.flow_id,
            "case_class": str(self.case_class),
            "steps": [s.model_dump(mode="json") for s in self.steps],
        }
        return content_id("case", payload)

    def with_fixed_step(self, order: int, fix: AgentFix) -> Case:
        """A new `Case` with the step at `order` replaced by `fix`. Content-addressed,
        so the same fix applied twice never produces two rows (`ProjectStore.add_case`)."""
        new_steps = [
            Step(order=order, action=fix.action, target=fix.target, value=fix.value,
                 expected=s.expected, source_ref=s.source_ref, note=f"agent fix: {fix.reasoning}")
            if s.order == order else s
            for s in self.steps
        ]
        return Case(
            project=self.project, flow_id=self.flow_id, kind=self.kind,
            case_class=self.case_class, title=self.title, rationale=self.rationale,
            preconditions=self.preconditions, steps=new_steps, severity=self.severity,
            rubric_ref=self.rubric_ref, script_ref=self.script_ref, status=self.status,
            user_persona_ref=self.user_persona_ref,
            priority=self.priority, pinned=self.pinned, pinned_issue_id=self.pinned_issue_id,
            provenance=self.provenance,
        )


class CaseProposal(Artifact):
    """A step-less candidate, bound to an exact FlowSpec snapshot and human review."""

    id: str = ""
    project: str
    flow_id: str
    spec_fingerprint: str
    case_class: CaseClass
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    status: Literal["proposed", "approved", "pruned"] = "proposed"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None

    def compute_id(self) -> str:
        return content_id("proposal", self.model_dump(mode="json", include={
            "project", "flow_id", "spec_fingerprint", "case_class", "title", "rationale",
        }))

    @property
    def slot_id(self) -> str:
        """Logical candidate slot; changed content replaces this slot with a fresh review."""
        return content_id("proposal_slot", {"project": self.project, "flow": self.flow_id,
                                           "class": self.case_class.value})

    @model_validator(mode="after")
    def _proposal_identity_and_review(self) -> CaseProposal:
        expected = self.compute_id()
        if self.id and self.id != expected:
            raise ValueError("proposal content changed: stage it for fresh review")
        object.__setattr__(self, "id", expected)
        if self.status != "proposed" and (
            not self.reviewed_by or not self.reviewed_by.strip() or self.reviewed_at is None
        ):
            raise ValueError("proposal review requires human attribution and time")
        if self.status == "proposed" and (self.reviewed_by or self.reviewed_at):
            raise ValueError("pending proposal cannot carry an earlier approval")
        return self

    @staticmethod
    def fingerprint_for(spec: FlowSpec) -> str:
        """Includes version, review and metadata; an edited saved spec invalidates approval."""
        return content_id("proposal_spec", spec.model_dump(mode="json"))

    def require_current(self, spec: FlowSpec) -> None:
        if (self.project != spec.project or spec.flow(self.flow_id) is None
                or self.spec_fingerprint != self.fingerprint_for(spec)):
            raise ValueError("proposal belongs to another or stale FlowSpec")

    def reviewed(self, by: str, approved: bool) -> CaseProposal:
        if not by.strip():
            raise ValueError("proposal review requires a human name")
        update = {"status": "approved" if approved else "pruned",
                  "reviewed_by": by.strip(), "reviewed_at": datetime.now(UTC)}
        if not approved and self.case_class is CaseClass.HAPPY:
            update = {"status": "proposed", "reviewed_by": None, "reviewed_at": None}
        return CaseProposal.model_validate({**self.model_dump(), **update})

    @classmethod
    def approved_batch(cls, spec: FlowSpec, rows: list[CaseProposal],
                       proposal_ids: list[str] | None, flow_id: str | None) -> list[CaseProposal]:
        """Validate all selected saved records, then return only human-approved proposals."""
        current = [p for p in rows if p.spec_fingerprint == cls.fingerprint_for(spec)]
        if len({p.id for p in current}) != len(current):
            raise ValueError("duplicate saved proposal identity")
        selected = set(proposal_ids) if proposal_ids is not None else {p.id for p in current}
        if not selected.issubset({p.id for p in current}):
            raise ValueError("selected proposal is absent or stale")
        batch = [p for p in current if p.id in selected]
        for proposal in batch:
            proposal.require_current(spec)
        batch = [p for p in batch if flow_id is None or p.flow_id == flow_id]
        for flow in (f for f in spec.flows if flow_id is None or f.id == flow_id):
            happy = [p for p in batch if p.flow_id == flow.id and p.case_class is CaseClass.HAPPY]
            if len(happy) != 1 or happy[0].status != "approved":
                raise ValueError("human approval of HAPPY proposal required; flow is pending")
        return [p for p in batch if p.status == "approved"]


class AgentFix(BaseModel):
    """The agent's proposed correction for one failing step."""

    model_config = ConfigDict(extra="forbid")

    action: Action
    target: str
    value: str | None = None
    reasoning: str = Field(min_length=1, description="why this should fix the observed error")


class ExpandedSteps(BaseModel):
    """One taxonomy class's proposed steps for a flow — `stages/expand.py`'s raw
    model answer, turned into a `Case` by the stage (never trusted verbatim as a
    finished artifact: an empty `steps` list means "not applicable here")."""

    model_config = ConfigDict(extra="forbid")

    steps: list[Step] = Field(default_factory=list)
    rationale: str = Field(min_length=1, description="why these steps test this class, or why "
                            "the class doesn't apply (when steps is empty)")


class ScriptStep(BaseModel):
    """One recorded step's locator: what replay uses in place of the case step's own target."""

    model_config = ConfigDict(extra="forbid")

    order: int
    locator: str = Field(description="browser/locators.py target grammar")
    strategy: str = Field(description="testid | role | label | css")
    brittle: bool = Field(default=False, description="css only: named in the run's report (SR3)")
    source_target: str = Field(description="the case step's own target at record time")


class ScriptInputs(BaseModel):
    """Everything that determines a script (SR2). Any difference makes it stale."""

    model_config = ConfigDict(extra="forbid")

    steps_hash: str
    flowspec_version: int | None = None
    test_id_attributes: list[str] = Field(default_factory=list)

    def differences(self, current: ScriptInputs) -> list[str]:
        """Human-readable names of what changed from `self` (the script's) to `current`."""
        found = []
        if self.steps_hash != current.steps_hash:
            found.append("case steps changed")
        if self.flowspec_version != current.flowspec_version:
            found.append(f"flowspec version {self.flowspec_version} -> {current.flowspec_version}")
        if self.test_id_attributes != current.test_id_attributes:
            found.append(f"locator priority {self.test_id_attributes} -> "
                         f"{current.test_id_attributes}")
        return found


class Script(Artifact):
    """A durable, versioned record of how one case runs, produced by a live run that worked.

    The point of the whole execution model: after the first successful run, a case replays
    its recorded locators and costs zero model calls to execute. A script is never edited in
    place; a changed input records a new `version` (T-176, D-041).
    """

    id: str = ""
    case_id: str
    path: str = Field(description="repo-relative path under projects/<slug>/scripts/")
    generated_by: str = Field(description="provider id, or 'human'")
    iterations: int = Field(default=1, description="agent attempts before it worked")
    stable_runs: int = Field(default=0, description="consecutive passes since last edit")
    version: int = Field(default=1, ge=1)
    inputs: ScriptInputs | None = None
    steps: list[ScriptStep] = Field(default_factory=list)

    @property
    def brittle_steps(self) -> list[int]:
        return [s.order for s in self.steps if s.brittle]

    def model_post_init(self, _context: object) -> None:
        if not self.id:
            payload = {"case": self.case_id, "p": self.path}
            object.__setattr__(self, "id", content_id("scr", payload))
