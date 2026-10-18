"""Test doubles for the T-216 surface oracles: a scripted page source, no browser, no network.

`SurfacePort` plays the role-session port plus the two optional surface capabilities
(`TextSurface`, `LayoutSurface`): it hands back the texts and measured layouts it was given and
records which viewports it was asked for. Everything is synthetic (MPI2): the copy matrix covers
each rule class once, and none of it reproduces a benchmark finding's case.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.lint_rule import ScreenLayout, SurfaceText, TextOrigin, Viewport
from autotester.schema.oracle_context import OracleContext
from autotester.schema.role_step import RoleStep


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 60), "white").save(buf, format="PNG")
    return buf.getvalue()


PNG = _png()


class SurfacePort:
    """Implements `RoleSessionPort` plus `surface_texts`, `layouts` and `screenshot`."""

    def __init__(self, texts: list[SurfaceText] | None = None,
                 layouts: dict[int, list[ScreenLayout]] | None = None,
                 *, shot_error: bool = False) -> None:
        self.texts = texts or []
        self.by_width = layouts or {}
        self.shot_error = shot_error
        self.asked: list[int] = []
        self.shots: list[tuple[str, str, int]] = []

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        return Observation(matched=False)

    def surface_texts(self) -> list[SurfaceText]:
        return list(self.texts)

    def layouts(self, viewport: Viewport) -> list[ScreenLayout]:
        self.asked.append(viewport.width)
        return list(self.by_width.get(viewport.width, []))

    def screenshot(self, role_id: str, screen: str, viewport: Viewport) -> bytes:
        self.shots.append((role_id, screen, viewport.width))
        if self.shot_error:
            raise OSError("page text that must not be copied")
        return PNG


class PlainPort:
    """A port with no surface capability: the oracle must say so, not report a clean page."""

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        return Observation(matched=False)


def text(label: str, body: str, *, kind: TextOrigin = TextOrigin.SCREEN, role: str = "parent",
         url: str | None = "/dashboard") -> SurfaceText:
    return SurfaceText(kind=kind, label=label, role_id=role, url=url, text=body,
                       platform_id="parent")


def context(run_dir: Path, port: object | None) -> OracleContext:
    return OracleContext(project_slug="demo", run_dir=str(run_dir), scenario_id="scn-1",
                         role_ids=["parent"], platform_ids=["parent"], port=port)
