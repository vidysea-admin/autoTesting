"""The surface capabilities of the live role port: `TextSurface` and `LayoutSurface` (MP25, MP26).

One job: hand the copy-lint and responsive oracles what each role's browser showed. Text comes
from the screens recorded after each step (visible text in reading order, secrets scrubbed);
layouts are measured by re-visiting each recorded screen at the asked viewport on the role's own
thread, then the viewport and the page are restored. A port that has visited nothing raises
`SurfaceUnavailable`, so an oracle is reported errored instead of clean because nothing was
looked at. Text, layouts and screenshot bytes live in memory for the oracle call; nothing here
writes a file.
"""

from __future__ import annotations

from autotester.browser import role_probe
from autotester.schema.lint_rule import (
    MAX_TEXT_CHARS,
    ControlBox,
    ScreenLayout,
    SurfaceText,
    SurfaceUnavailable,
    TextOrigin,
    Viewport,
)
from autotester.stages.role_port_state import PortBase, ScreenRecord


class SurfaceMixin(PortBase):
    """`surface_texts()`, `layouts()` and `screenshot()`."""

    def _visited(self) -> list[tuple[str, ScreenRecord]]:
        self._require_every_role()
        found = [(rid, rec) for rid, st in self._states.items() for rec in st.screens.values()]
        if not found:
            raise SurfaceUnavailable("no screen has been visited, so there is nothing to read")
        return found

    def surface_texts(self) -> list[SurfaceText]:
        """Every visited screen's visible text, per role."""
        return [SurfaceText(kind=TextOrigin.SCREEN, label=rec.label, role_id=rid,
                            platform_id=self.roles.account(rid).platform_id,
                            url=rec.shown_url[:500], text=rec.text[:MAX_TEXT_CHARS])
                for rid, rec in self._visited()]

    def layouts(self, viewport: Viewport) -> list[ScreenLayout]:
        """Measure each role's visited screens at `viewport` (the page is put back afterwards)."""
        self._visited()
        out: list[ScreenLayout] = []
        for rid, state in self._states.items():
            records = list(state.screens.values())
            if not records:
                continue
            urls = [r.url for r in records]
            boxes = self.roles.run_as(
                rid, lambda s, log=state.log, urls=urls: role_probe.measure_screens(
                    s, log, urls, viewport.width, viewport.height))
            platform = self.roles.account(rid).platform_id
            out += [ScreenLayout(role_id=rid, platform_id=platform, screen=rec.label,
                                 url=rec.shown_url[:500], content_width=float(box["width"]),
                                 controls=[ControlBox(**c) for c in box["controls"]])
                    for rec, box in zip(records, boxes, strict=True)]
        return out

    def screenshot(self, role_id: str, screen: str, viewport: Viewport) -> bytes:
        """A PNG of that screen as `role_id` saw it at `viewport`; the caller masks it."""
        state = self._guard(role_id)
        record = next((r for r in state.screens.values() if r.label == screen), None)
        if record is None:
            raise SurfaceUnavailable("that role has not visited that screen")
        return self.roles.run_as(role_id, lambda s: role_probe.screenshot_png(
            s, state.log, record.url, viewport.width, viewport.height))
