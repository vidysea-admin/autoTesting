"""T-216 (multi-role-platform.md MP26): the responsive sweep.

Synthetic fixture (MPI2): a screen whose page is 520 px wide inside a 375 px viewport, a clean
screen, a screen whose controls sit past the edge while the page itself does not scroll. The OCR
engine is faked so masking is exercised without Tesseract; with the engine missing the screenshot
is withheld and nothing raw is written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from surface_fakes import PNG, PlainPort, SurfacePort, context

from autotester.browser.conditions import MOBILE_VIEWPORT
from autotester.core import image_privacy as privacy
from autotester.schema.enums import CaseClass
from autotester.schema.lint_rule import ControlBox, ScreenLayout, SurfaceChecks, Viewport
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.oracle_context import OracleState
from autotester.stages import oracle_responsive as responsive
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_registry import run_oracles

OCR_ROW = "5\t1\t1\t1\t1\t1\t5\t5\t30\t10\t95\tword\n"
OCR_HEADER = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
              "left\ttop\twidth\theight\tconf\ttext\n")


def box(name: str, left: float, right: float) -> ControlBox:
    return ControlBox(name=name, left=left, right=right)


def layout(screen: str, width: float, controls: list[ControlBox] | None = None) -> ScreenLayout:
    return ScreenLayout(role_id="parent", platform_id="parent", screen=screen, url="/grades",
                        content_width=width, controls=controls or [])


def declare(run_dir: Path, *widths: int) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    checks = SurfaceChecks(viewports=[Viewport(width=w, height=800) for w in widths])
    (run_dir / "surface_checks.json").write_text(checks.model_dump_json(), encoding="utf-8")


@pytest.fixture
def masked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(privacy, "_local_ocr", lambda path: OCR_HEADER + OCR_ROW)


def sweep(run_dir: Path, port: SurfacePort, *widths: int) -> list:
    declare(run_dir, *widths)
    return responsive.run(context(run_dir, port))


def test_overflow_at_375_is_a_finding_with_a_masked_screenshot(tmp_path: Path,
                                                               masked: None) -> None:
    port = SurfacePort(layouts={375: [layout("grades", 520), layout("home", 375)]})
    found = sweep(tmp_path, port, 375)
    assert len(found) == 1
    f = found[0]
    assert f.finding_class is FindingClass.RESPONSIVE_LAYOUT
    assert f.oracle is OracleName.RESPONSIVE
    assert priority_for(f.finding_class).value == "P2"
    assert "375px" in f.title and "520px" in f.title and "grades" in f.title
    shot = tmp_path / "responsive" / f"{f.finding_id}.png"
    assert shot.is_file() and f"responsive/{f.finding_id}.png" in f.title
    assert shot.read_bytes() != PNG  # the masked copy, never the raw capture
    assert port.shots == [("parent", "grades", 375)]


def test_a_clean_screen_is_not_a_finding(tmp_path: Path) -> None:
    clean = layout("home", 375, [box("#menu", 8, 120), box("#go", 250, 367)])
    assert sweep(tmp_path, SurfacePort(layouts={375: [clean]}), 375) == []
    assert not (tmp_path / "responsive").exists()


def test_a_control_past_the_edge_is_a_finding_even_when_the_page_does_not_scroll(
        tmp_path: Path, masked: None) -> None:
    hidden = layout("pay", 375, [box("#ok", 10, 100), box("#a", 380, 460), box("#b", -90, -10)])
    found = sweep(tmp_path, SurfacePort(layouts={375: [hidden]}), 375)
    assert [f.count for f in found] == [2]
    assert "2 control(s) off-screen" in found[0].title and "wide" not in found[0].title


def test_every_declared_viewport_is_swept(tmp_path: Path, masked: None) -> None:
    port = SurfacePort(layouts={375: [layout("grades", 520)], 768: [layout("grades", 768)]})
    found = sweep(tmp_path, port, 375, 768)
    assert port.asked == [375, 768]
    assert len(found) == 1 and "375px" in found[0].title


def test_the_default_viewport_is_the_mobile_one(tmp_path: Path, masked: None) -> None:
    width = MOBILE_VIEWPORT["width"]
    port = SurfacePort(layouts={width: [layout("grades", width + 200)]})
    declare(tmp_path)
    found = responsive.run(context(tmp_path, port))
    assert port.asked == [width] and len(found) == 1
    assert responsive.case_class_for(Viewport(width=width, height=800)) is CaseClass.VIEWPORT_MOBILE
    assert responsive.case_class_for(Viewport(width=1366, height=850)) is None
    assert "mobile" in found[0].title


def test_without_a_masking_engine_the_screenshot_is_withheld_not_written_raw(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(privacy.shutil, "which", lambda name: None)
    found = sweep(tmp_path, SurfacePort(layouts={375: [layout("grades", 520)]}), 375)
    assert len(found) == 1 and "screenshot withheld (local_ocr_unavailable)" in found[0].title
    assert not list(tmp_path.rglob("*.png"))


def test_a_failing_screenshot_does_not_lose_the_finding_or_leak_its_error(
        tmp_path: Path) -> None:
    port = SurfacePort(layouts={375: [layout("grades", 520)]}, shot_error=True)
    found = sweep(tmp_path, port, 375)
    assert len(found) == 1 and "screenshot withheld (screenshot_failed)" in found[0].title
    assert "page text" not in json.dumps([f.model_dump(mode="json") for f in found])


def test_screenshots_are_bounded(tmp_path: Path, masked: None) -> None:
    many = [layout(f"screen-{n}", 520) for n in range(responsive.MAX_SCREENSHOTS + 3)]
    found = sweep(tmp_path, SurfacePort(layouts={375: many}), 375)
    assert len(found) == len(many)
    assert sum("masked screenshot" in f.title for f in found) == responsive.MAX_SCREENSHOTS
    assert sum("screenshot_cap" in f.title for f in found) == 3


def test_a_port_that_cannot_measure_is_reported_errored_not_clean(tmp_path: Path) -> None:
    declare(tmp_path, 375)
    summary, found = run_oracles(context(tmp_path, PlainPort()), [OracleName.RESPONSIVE])
    status = next(s for s in summary.statuses if s.oracle is OracleName.RESPONSIVE)
    assert (status.state, status.reason) == (OracleState.ERRORED, "SurfaceUnavailable")
    assert found == []


def test_the_registry_runs_the_oracle_end_to_end(tmp_path: Path, masked: None) -> None:
    declare(tmp_path, 375)
    port = SurfacePort(layouts={375: [layout("grades", 520)]})
    summary, found = run_oracles(context(tmp_path, port), [OracleName.RESPONSIVE])
    status = next(s for s in summary.statuses if s.oracle is OracleName.RESPONSIVE)
    assert (status.state, status.finding_count) == (OracleState.RAN, 1) and len(found) == 1
