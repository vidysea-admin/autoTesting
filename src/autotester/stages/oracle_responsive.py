"""The responsive sweep oracle (MP26).

One job: check every visited screen at each declared viewport and report horizontal overflow or a
control that is off-screen as a `RESPONSIVE_LAYOUT` finding, with a masked screenshot beside it.
The sizes come from the port's `LayoutSurface` capability (it resizes each role's page, the way
`browser/conditions.py::enact` does for a VIEWPORT_MOBILE case, measures, and restores); the
decision is made here from the numbers, so it is deterministic and makes no model call. With no
viewport declared the sweep uses the mobile viewport the executor already enacts for
`CaseClass.VIEWPORT_MOBILE`.

A screenshot is written only through `stages/leak_evidence.py::store_masked_screenshot`: the raw
image touches a temporary directory outside the run directory, and when masking is unavailable the
screenshot is withheld with a fixed reason code, never stored raw. A finding names the viewport,
the page width and the count of off-screen controls, never a control's text, which may be
another person's data (MPI1). `MultiRoleFinding` has no screenshot field, so the masked file is
`responsive/<finding_id>.png` and the finding title says so (CORE-REQUEST in the T-216 manifest).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from autotester.browser.conditions import MOBILE_VIEWPORT
from autotester.schema.enums import CaseClass
from autotester.schema.lint_rule import (
    LayoutSurface,
    ScreenLayout,
    SurfaceUnavailable,
    Viewport,
    load_surface_checks,
)
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext
from autotester.stages.leak_evidence import store_masked_screenshot, templatise_url

__all__ = ["case_class_for", "run", "run_responsive"]

TOLERANCE_PX = 1.0
MAX_SCREENSHOTS = 20
SHOT_DIR = "responsive"
_SLUG = re.compile(r"[^a-z0-9_-]+")


def case_class_for(viewport: Viewport) -> CaseClass | None:
    """`VIEWPORT_MOBILE` for a viewport no wider than the mobile one the executor enacts."""
    return CaseClass.VIEWPORT_MOBILE if viewport.width <= MOBILE_VIEWPORT["width"] else None


def _problems(viewport: Viewport, layout: ScreenLayout) -> tuple[bool, int]:
    """(page wider than the viewport, number of controls beyond the left or right edge)."""
    limit = viewport.width + TOLERANCE_PX
    off = sum(1 for c in layout.controls if c.right > limit or c.left < -TOLERANCE_PX)
    return layout.content_width > limit, off


def _screenshot_note(port: LayoutSurface, run_dir: Path, finding_id: str, layout: ScreenLayout,
                     viewport: Viewport, taken: int) -> str:
    """Write the masked screenshot, or say in fixed words why it was withheld."""
    if taken >= MAX_SCREENSHOTS:
        return "screenshot withheld (screenshot_cap)"
    try:
        png = port.screenshot(layout.role_id, layout.screen, viewport)
    except Exception:
        return "screenshot withheld (screenshot_failed)"
    dest = run_dir / SHOT_DIR / f"{finding_id}.png"
    stored, reason = store_masked_screenshot(png, dest)
    if stored is None:
        return f"screenshot withheld ({_SLUG.sub('_', reason or 'sanitation_failed')[:40]})"
    return f"masked screenshot {SHOT_DIR}/{finding_id}.png"


def _finding(viewport: Viewport, layout: ScreenLayout, overflow: bool, off: int, note: str,
             finding_id: str) -> MultiRoleFinding:
    kind = "mobile" if case_class_for(viewport) is CaseClass.VIEWPORT_MOBILE else "desktop"
    parts = []
    if overflow:
        parts.append(f"page {layout.content_width:.0f}px wide")
    if off:
        parts.append(f"{off} control(s) off-screen")
    slug = _SLUG.sub("-", layout.screen.lower()).strip("-")[:40] or "screen"
    template = templatise_url(layout.url) if layout.url else "/"
    return MultiRoleFinding(
        finding_id=finding_id, finding_class=FindingClass.RESPONSIVE_LAYOUT,
        oracle=OracleName.RESPONSIVE, role=layout.role_id, platform_id=layout.platform_id,
        title=f"{viewport.width}px {kind} viewport: {', '.join(parts)} on {slug}; {note}",
        url_template=template, steps=[f"login {layout.role_id}", f"goto {template}"],
        count=off or 1)


def _check(context: OracleContext, port: LayoutSurface, viewport: Viewport,
           layout: ScreenLayout, taken: int) -> MultiRoleFinding | None:
    overflow, off = _problems(viewport, layout)
    if not overflow and not off:
        return None
    ident = f"{layout.role_id}|{layout.platform_id}|{layout.screen}|{viewport.width}"
    finding_id = "rl-" + hashlib.sha1(ident.encode("utf-8")).hexdigest()[:12]
    note = _screenshot_note(port, Path(context.run_dir), finding_id, layout, viewport, taken)
    return _finding(viewport, layout, overflow, off, note, finding_id)


def run_responsive(context: OracleContext) -> list[MultiRoleFinding]:
    """The oracle entry point named by `schema/oracle_context.py`."""
    declared = load_surface_checks(Path(context.run_dir)).viewports
    viewports = declared or [Viewport(**MOBILE_VIEWPORT)]
    port = context.port
    if not isinstance(port, LayoutSurface):
        raise SurfaceUnavailable("the port cannot resize pages or measure layouts")
    found: list[MultiRoleFinding] = []
    for viewport in viewports:
        for layout in port.layouts(viewport):
            finding = _check(context, port, viewport, layout, len(found))
            if finding is not None:
                found.append(finding)
    return found

# The name the oracle registry imports. An alias, so each concept has one definition name.
run = run_responsive
