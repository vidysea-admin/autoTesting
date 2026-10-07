"""A crawl stuck at the login wall reads as non-success on every surface (X18 c/d, AT-458).

The judged status (`stages.explore_status`) is only half the fix: the three crawls on disk
that stopped at the login page were shown as a green "completed" on the crawls table, the
crawl page, the workbook and the CLI line. X16 lists those surfaces; each is checked here,
for a new LOGIN_WALL crawl and for a legacy `completed` crawl that did nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from autotester.cli_crawl import echo_crawl_summary
from autotester.schema.crawl import CoverageHole, Crawl, CrawlCoverage
from autotester.schema.enums import CrawlStatus
from autotester.schema.project import Project
from autotester.stages.crawl_report import export_crawl_excel
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

_POSITIVE = "badge-pass"
_ERROR_REASON = "crawl incomplete: recorded controls were not exercised because of errors"

_STUCK = {
    "login_wall": dict(status=CrawlStatus.LOGIN_WALL, actions=2, denied=2, screens=2,
                       stop_reason="stopped at a login wall: every screen reached only offers "
                                   "a form submit denied by read_only"),
    "legacy_completed_no_op": dict(status=CrawlStatus.COMPLETED, actions=0, denied=3, screens=1,
                                   stop_reason="frontier empty"),
    "legacy_error_holes": dict(status=CrawlStatus.COMPLETED, actions=0, screens=1,
                               stop_reason="frontier empty", coverage=CrawlCoverage(holes=[
                                   CoverageHole(node_id="n", url_template="/", selector="#x",
                                                reason="error")])),
}


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    ProjectStore("demo", tmp_path).save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test/", allowed_domains=["demo.test"]))
    return tmp_path


def _saved(root: Path, **fields: object) -> Crawl:
    crawl = Crawl(project="demo", id="crawl_stuck", finished_at="2026-09-17T00:00:00Z", **fields)
    ProjectStore("demo", root).save_crawl(crawl)
    return crawl


@pytest.mark.parametrize("shape", sorted(_STUCK))
def test_the_crawls_table_does_not_show_a_stuck_crawl_as_success(root: Path, shape: str) -> None:
    crawl = _saved(root, **_STUCK[shape])
    before = ProjectStore("demo", root).paths.crawl_manifest(crawl.id).read_bytes()

    text = TestClient(app).get("/projects/demo/crawls").text

    row = text[text.index("crawl_stuck"):]
    row = row[:row.index("</tr>")]
    assert "completed" not in row, "the status word itself must not say completed"
    assert _POSITIVE not in row, "and nothing in the row may be coloured success"
    if shape == "legacy_error_holes":
        assert _ERROR_REASON in row and "frontier empty" not in row
    assert ProjectStore("demo", root).paths.crawl_manifest(crawl.id).read_bytes() == before


@pytest.mark.parametrize("shape", sorted(_STUCK))
def test_the_crawl_page_does_not_colour_a_stuck_crawl_as_success(root: Path, shape: str) -> None:
    _saved(root, **_STUCK[shape])

    text = TestClient(app).get("/projects/demo/crawls/crawl_stuck").text

    summary = text[text.index("<div class='stat-row'>"):text.index("Download Excel report")]
    assert _POSITIVE not in summary
    assert ">completed<" not in text
    if shape == "legacy_error_holes":
        assert _ERROR_REASON in summary and "frontier empty" not in text


@pytest.mark.parametrize("shape", sorted(_STUCK))
def test_the_workbook_summary_does_not_say_completed(
    root: Path, shape: str, tmp_path: Path,
) -> None:
    _saved(root, **_STUCK[shape])

    out = export_crawl_excel("demo", "crawl_stuck", tmp_path / "crawl.xlsx")
    rows = {r[0]: r[1] for r in load_workbook(out).worksheets[0].iter_rows(values_only=True)}

    assert rows["Status"] != "completed"
    if shape == "legacy_error_holes":
        assert rows["Stopped because"] == _ERROR_REASON


@pytest.mark.parametrize("shape", sorted(_STUCK))
def test_the_cli_line_does_not_say_completed_or_print_green(
    shape: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, object]] = []
    monkeypatch.setattr("typer.secho", lambda text, fg=None, **_k: seen.append((text, fg)))

    echo_crawl_summary(Crawl(project="demo", id="crawl_stuck", **_STUCK[shape]))

    text, colour = seen[0]
    assert ": completed " not in text
    assert colour != "green"
    if shape == "legacy_error_holes":
        assert _ERROR_REASON in text and "frontier empty" not in text


def test_a_really_completed_crawl_is_still_green_everywhere(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard must be able to say yes."""
    _saved(root, status=CrawlStatus.COMPLETED, actions=6, denied=1, screens=4,
           stop_reason="frontier empty")
    seen: list[tuple[str, object]] = []
    monkeypatch.setattr("typer.secho", lambda text, fg=None, **_k: seen.append((text, fg)))

    table = TestClient(app).get("/projects/demo/crawls").text
    echo_crawl_summary(ProjectStore("demo", root).load_crawl("crawl_stuck"))

    row = table[table.index("crawl_stuck"):]
    assert _POSITIVE in row[:row.index("</tr>")]
    assert seen[0][1] == "green"
