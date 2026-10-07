"""A `UserPersona` and the opt-in `UXPolicy` -- WHO the advisory UX pass reads a run as.

T-190 / D-048 (gate A, `qa/contracts/persona-ux-advisory.md` PU1/PU4). A persona describes a kind
of user (role, tech comfort, locale, device). It feeds ONLY the advisory UX pass
(`stages/ux_advisory.py`); it is never an input to a rubric, a criterion or `grade()`, so it
cannot soften or stiffen a functional verdict. Personas are stored one per line in
`projects/<slug>/user_personas.jsonl`; a `Project` and/or a `Case` refers to one by id
(`user_persona_ref`), never embedding it -- the same by-reference shape as `Case.rubric_ref`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.base import Artifact
from autotester.schema.enums import TechComfort

PERSONA_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"
"""A persona id is a short slug: no path separators, dots or spaces, so a ref can never
name a file outside the project's own `user_personas.jsonl`."""


class UserPersona(Artifact):
    """One kind of user the UX pass reads a run as. Advisory input only (PU4)."""

    id: str = Field(pattern=PERSONA_ID_PATTERN, description="stable slug a ref points at")
    project: str
    role: str = Field(min_length=1, max_length=120, description="e.g. 'school counsellor'")
    tech_comfort: TechComfort
    locale: str = Field(min_length=2, max_length=35, description="BCP-47-ish, e.g. 'hi-IN'")
    device: str = Field(min_length=1, max_length=64, description="e.g. 'desktop' or 'mobile'")


class UXPolicy(BaseModel):
    """Per-project switch and cap for the UX pass. Off by default (plan decision 5)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=False, description="opt-in; nothing runs when False")
    max_calls: int = Field(
        default=20, ge=0, le=100,
        description="ceiling on UX provider calls per run, failed attempts included. A CALL "
                    "cap, not a money or token ceiling; cases past it are recorded as "
                    "skipped_budget and never touch a functional verdict (PU3)",
    )
