"""The declared surface checks and what the surface oracles read (MP25, MP26).

One job: the shapes of the T-216 surface oracles. `LintRule` is one declared copy, branding or
display-timezone rule (MP25); `Viewport` is one declared screen size (MP26); `SurfaceChecks` is the
declaration file both oracles load from `<run_dir>/surface_checks.json`. `SurfaceText` (visible DOM
text or a mail body) and `ScreenLayout` (measured widths and control boxes) are what a role session
hands an oracle: they live in memory for one run and are never written, because page text may hold
another person's data (MPI1). `TextSurface` and `LayoutSurface` are the two optional capabilities
a `RoleSessionPort` may add; a port without them is reported errored, never a clean page.

The timezone vocabulary is closed: an offset (`+05:30`, `UTC+5:30`, `Z`) or one abbreviation of
`ZONE_OFFSETS_MIN`. A zone is compared by its offset, so `IST` and `+05:30` are the same zone.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN

DECLARATION_FILE = "surface_checks.json"
MAX_TEXT_CHARS = 200_000
RULE_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"

ZONE_OFFSETS_MIN: dict[str, int] = {
    "UTC": 0, "GMT": 0, "WET": 0, "BST": 60, "CET": 60, "CEST": 120, "EET": 120, "EEST": 180,
    "MSK": 180, "IST": 330, "PKT": 300, "NPT": 345, "BDT": 360, "ICT": 420, "WIB": 420,
    "SGT": 480, "HKT": 480, "AWST": 480, "JST": 540, "KST": 540, "ACST": 570, "AEST": 600,
    "AEDT": 660, "NZST": 720, "NZDT": 780, "SAST": 120, "EAT": 180, "WAT": 60, "CAT": 120,
    "NST": -210, "AST": -240, "ADT": -180, "EST": -300, "EDT": -240, "CST": -360, "CDT": -300,
    "MST": -420, "MDT": -360, "PST": -480, "PDT": -420, "AKST": -540, "AKDT": -480,
    "HST": -600,
}
_OFFSET = re.compile(r"^(?:UTC|GMT)?([+-])(\d{1,2})(?::?(\d{2}))?$")


def zone_key(token: str) -> str | None:
    """The comparable form of a zone designator (`+0530` style minutes), or None if unknown."""
    word = token.strip().upper()
    if word == "Z":
        return "+0000"
    if word in ZONE_OFFSETS_MIN:
        minutes = ZONE_OFFSETS_MIN[word]
    else:
        match = _OFFSET.match(word)
        if not match or int(match[2]) > 14 or int(match[3] or 0) > 59:
            return None
        minutes = (int(match[2]) * 60 + int(match[3] or 0)) * (-1 if match[1] == "-" else 1)
    sign = "-" if minutes < 0 else "+"
    return f"{sign}{abs(minutes) // 60:02d}{abs(minutes) % 60:02d}"


class LintKind(StrEnum):
    """What one lint rule checks."""

    BRAND_TERM = "brand_term"
    FORBIDDEN_STRING = "forbidden_string"
    DISPLAY_TIMEZONE = "display_timezone"


class TextOrigin(StrEnum):
    """Where a text was read: a screen's visible DOM text or a mail body."""

    SCREEN = "screen"
    MAIL = "mail"


class LintRule(BaseModel):
    """One declared rule. `value` is the brand term, the forbidden string or the display zone."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=RULE_ID_PATTERN)
    kind: LintKind
    value: str = Field(min_length=1, max_length=120)
    case_sensitive: bool | None = Field(
        default=None, description="brand terms default to exact case, forbidden strings to any")

    @property
    def is_case_sensitive(self) -> bool:
        """The declared choice, else exact case for a brand term and any case otherwise."""
        if self.case_sensitive is None:
            return self.kind is LintKind.BRAND_TERM
        return self.case_sensitive

    @model_validator(mode="after")
    def _value_fits_kind(self) -> LintRule:
        if contains_personal_shape(self.value):
            raise ValueError("a rule value looks like personal data")
        if self.kind is LintKind.DISPLAY_TIMEZONE and zone_key(self.value) is None:
            raise ValueError("display zone must be an offset or a known abbreviation")
        return self


class Viewport(BaseModel):
    """One declared viewport; `stages/oracle_responsive.py` maps narrow ones to VIEWPORT_MOBILE."""

    model_config = ConfigDict(extra="forbid")

    width: int = Field(ge=200, le=4000)
    height: int = Field(ge=200, le=4000)


class SurfaceChecks(BaseModel):
    """The declaration both surface oracles read; viewports default to the mobile one."""

    model_config = ConfigDict(extra="forbid")

    rules: list[LintRule] = Field(default_factory=list, max_length=200)
    viewports: list[Viewport] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def _rule_ids_unique(self) -> SurfaceChecks:
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("lint rule ids must be unique")
        return self


class SurfaceText(BaseModel):
    """Visible text of one screen or one mail body, as one role saw it. Never persisted."""

    model_config = ConfigDict(extra="forbid", repr=False)

    kind: TextOrigin
    label: str = Field(min_length=1, max_length=120, description="screen name or message ordinal")
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    platform_id: str = Field(default="unknown", pattern=PLATFORM_ID_PATTERN)
    url: str | None = Field(default=None, max_length=500)
    text: str = Field(max_length=MAX_TEXT_CHARS)


class ControlBox(BaseModel):
    """A visible control's horizontal extent in CSS pixels."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80, description="selector or role name")
    left: float
    right: float


class ScreenLayout(BaseModel):
    """What one role's page measured at one viewport (the viewport width is the caller's)."""

    model_config = ConfigDict(extra="forbid")

    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    platform_id: str = Field(default="unknown", pattern=PLATFORM_ID_PATTERN)
    screen: str = Field(min_length=1, max_length=120)
    url: str | None = Field(default=None, max_length=500)
    content_width: float = Field(ge=0, description="the page's scroll width")
    controls: list[ControlBox] = Field(default_factory=list, max_length=500)


@runtime_checkable
class TextSurface(Protocol):
    """A port that can read what its role contexts show (screens and received mail)."""

    def surface_texts(self) -> list[SurfaceText]:
        """Every visited screen's visible text and every received mail body, per role."""


@runtime_checkable
class LayoutSurface(Protocol):
    """A port that can resize its role contexts and measure the visited screens."""

    def layouts(self, viewport: Viewport) -> list[ScreenLayout]:
        """Set `viewport` on each role's page, measure each visited screen, then restore it."""

    def screenshot(self, role_id: str, screen: str, viewport: Viewport) -> bytes:
        """A PNG of that screen at that viewport; it is masked before it is written."""


class SurfaceUnavailable(RuntimeError):
    """The port lacks the surface capability, so the oracle cannot look. Never a clean result."""


class SurfaceDeclarationMissing(RuntimeError):
    """No usable `surface_checks.json`: with nothing declared the oracle would be vacuous."""


def load_surface_checks(run_dir: Path) -> SurfaceChecks:
    """The declaration in `run_dir`; raises `SurfaceDeclarationMissing` if absent or unreadable."""
    path = Path(run_dir) / DECLARATION_FILE
    try:
        return SurfaceChecks.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        raise SurfaceDeclarationMissing(DECLARATION_FILE) from None
