"""How a live role port drives one role-assign control, so MP19's escalation can be tried (MP19).

One job: `ControlBinding` -- for the control a plan names by id (`RoleAssignControl.id`), the
locator that triggers the assignment, the element that proves the app accepted it, and the locator
and proof for UNDOING it. The plan only says where a control lives; the port needs to know what to
press and how to put the account back. A control with no binding is never attempted: the revert
(MPI4: an escalation that succeeds is reverted in the same run) could not be promised. Locators
and element proofs only; no value, no credential.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.authz_probe import ID_PATTERN


class ControlBinding(BaseModel):
    """The press-and-prove recipe for one role-assign control and its undo."""

    model_config = ConfigDict(extra="forbid")

    control_id: str = Field(pattern=ID_PATTERN)
    assign_locator: str = Field(min_length=1, max_length=200,
                                description="what to press to assign the role")
    accepted_target: str = Field(min_length=1, max_length=200,
                                 description="a locator visible only once the app accepted it")
    revert_locator: str = Field(min_length=1, max_length=200,
                                description="what to press to take the role away again")
    reverted_target: str = Field(min_length=1, max_length=200,
                                 description="a locator visible only once the old role is back")
