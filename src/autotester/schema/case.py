"""A test case — one falsifiable claim about the product, plus how to check it."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.core.ids import content_id
from autotester.schema.base import Artifact
from autotester.schema.enums import Action, CaseClass, CaseKind, CaseStatus, Severity
from autotester.schema.flowspec import Step
from autotester.schema.user_persona import PERSONA_ID_PATTERN


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
    status: CaseStatus = CaseStatus.PROPOSED
    pinned: bool = Field(
        default=False,
        description="AT-585: born from a confirmed Issue (stages/issues.py::"
                     "pin_issue_as_case). A pinned case is included in every "
                     "regression run (it is just another row `list_cases()` "
                     "returns — no run-time filtering exists to bypass) and "
                     "`ProjectStore.delete_case` refuses to remove it. This is "
                     "deliberately NOT a priority system: T-178 (p0-p3 + human "
                     "pruning before LLM spend) is expected to subsume `pinned` "
                     "with `priority == p0` once it lands, at which point this "
                     "flag becomes redundant and can be retired in that unit.",
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
        )


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
