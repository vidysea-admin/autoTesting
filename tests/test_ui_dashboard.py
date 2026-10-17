"""The home-page dashboard. Contract: qa/contracts/ui.md U2 (real persisted
state, never recomputed/cached). Split out of test_ui.py (AT doctor's 300-line
file cap) once the home page grew from a bare project grid into a portfolio
health view.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.enums import Result
from autotester.schema.run import Run
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore
from autotester.ui import theme
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_index_shows_portfolio_stats_across_projects(
    client: TestClient, scratch_root: Path
) -> None:
    """Feedback 2026-09-06: the home page showed project names and case
    counts only, nothing about what's actually passing or failing across the
    portfolio -- a non-technical user had to click into every project one by
    one. The dashboard must surface aggregate health without doing so."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    run = Run(project="demo", case_ids=["case-1"])
    store.save_run(run)
    store.save_verdict(run.id, Verdict(run_id=run.id, case_id="case-1",
                                        result=Result.FAIL, grader_provider="mock"))

    response = client.get("/")

    assert response.status_code == 200
    assert "projects" in response.text
    assert "latest run failing" in response.text
    assert theme.badge("FAIL", count=1) in response.text


def test_index_project_never_run_shows_that_state(
    client: TestClient, scratch_root: Path
) -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    synthetic = ProjectStore("demo", scratch_root).paths.runs_dir / "crawl_attempt"
    synthetic.mkdir(parents=True)

    response = client.get("/")

    assert response.status_code == 200
    assert "never run" in response.text


def test_favicon_is_an_intentional_empty_response(
    client: TestClient, scratch_root: Path
) -> None:
    response = client.get("/favicon.ico")

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.parametrize("path", [
    "/onboard", "/projects/demo", "/projects/demo/env", "/projects/demo/report",
    "/projects/demo/flow-diagram", "/settings/providers", "/live",
])
def test_every_non_home_page_has_a_real_back_button(
    client: TestClient, scratch_root: Path, path: str
) -> None:
    """Umesh, 2026-09-07: "there is no back button for easy navigation" — the
    breadcrumb trail alone was a muted 0.78rem uppercase line that read as a
    location label, not a control. Every page a user can navigate INTO must
    offer a visible way back out."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })

    response = client.get(path)

    assert response.status_code == 200
    assert "<a class='btn btn-back'" in response.text, f"{path} has no back button"
    assert "&larr; Back" in response.text


def test_back_button_targets_the_parent_not_always_home(
    client: TestClient, scratch_root: Path
) -> None:
    """A nested page goes back one level (to its project), not all the way
    home — otherwise "back" silently loses the user's place."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })

    response = client.get("/projects/demo/env")

    assert "<a class='btn btn-back' href='/projects/demo'>" in response.text


def test_home_page_has_no_back_button(client: TestClient, scratch_root: Path) -> None:
    """Home is the root — a back button there would point at itself. Asserts on
    the rendered anchor, not the class name: `.btn-back`'s CSS rule ships in the
    shared stylesheet on every page, so a bare substring check always matches."""
    response = client.get("/")

    assert response.status_code == 200
    assert "<a class='btn btn-back'" not in response.text


def test_index_project_with_clean_latest_run_counts_as_healthy(
    client: TestClient, scratch_root: Path
) -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    run = Run(project="demo", case_ids=["case-1"])
    store.save_run(run)
    store.save_verdict(run.id, Verdict(run_id=run.id, case_id="case-1",
                                        result=Result.PASS, grader_provider="mock"))

    response = client.get("/")

    assert response.status_code == 200
    assert "latest run clean" in response.text
    assert "latest run failing" not in response.text


def _onboard(client: TestClient, slug: str) -> ProjectStore:
    client.post("/onboard", data={
        "slug": slug, "name": slug.title(), "base_url": f"https://{slug}.test",
        "allowed_domains": f"{slug}.test",
    })
    return ProjectStore(slug)


def _run_with(store: ProjectStore, result: Result, created_at: datetime | None = None) -> Run:
    run = Run(project=store.paths.slug, case_ids=["case-1"])
    if created_at is not None:
        run = run.model_copy(update={"created_at": created_at})
    store.save_run(run)
    store.save_verdict(run.id, Verdict(run_id=run.id, case_id="case-1",
                                       result=result, grader_provider="mock"))
    return run


def _card(html: str, slug: str) -> str:
    """The one project card for `slug`, so an assertion cannot pass on a neighbour."""
    start = html.index(f"class='project-card' href='/projects/{slug}'")
    return html[start:html.index("</a>", start)]


def test_u15_home_shows_latest_outcome_and_age_per_project_and_no_runs_for_the_idle_one(
    client: TestClient, scratch_root: Path
) -> None:
    """U15 / AT-664, Umesh 2026-09-06: with one project never run and one with a failed
    run, `/` must say what happened last and how long ago for the second, `no runs` for
    the first, and invent a `0` for neither."""
    _onboard(client, "idle")
    failed = _onboard(client, "broken")
    _run_with(failed, Result.FAIL, datetime.now(UTC) - timedelta(hours=3))

    html = client.get("/").text

    assert "no runs" in _card(html, "idle")
    assert "0 fail" not in _card(html, "idle").lower()
    assert theme.badge("FAIL", count=1) in _card(html, "broken")
    assert "3 hours ago" in _card(html, "broken")
    assert "no runs" not in _card(html, "broken")


def test_u15_home_counts_how_many_projects_have_ever_had_a_run(
    client: TestClient, scratch_root: Path
) -> None:
    _onboard(client, "idle")
    _run_with(_onboard(client, "busy"), Result.PASS)

    html = client.get("/").text

    assert theme.stat("1", "have run") in html
    assert theme.stat("2", "projects") in html


def test_u15_home_names_a_project_with_unreadable_run_evidence_and_counts_it_skipped(
    client: TestClient, scratch_root: Path
) -> None:
    """A corrupt run.json used to make the project look `never run` (the run was dropped
    silently). It must read `unreadable`, be named, and be counted as skipped."""
    _run_with(_onboard(client, "healthy"), Result.PASS)
    rotten = _onboard(client, "rotten")
    run = _run_with(rotten, Result.PASS)
    (rotten.paths.run_dir(run.id) / "run.json").write_text("{not json", encoding="utf-8")

    html = client.get("/").text

    assert "unreadable" in _card(html, "rotten")
    assert "no runs" not in _card(html, "rotten")
    assert theme.stat("1", "skipped (unreadable): rotten") in html
    assert theme.stat("1", "have run") in html


def test_u15_home_labels_a_run_older_than_the_projects_last_change_as_stale(
    client: TestClient, scratch_root: Path
) -> None:
    old = _onboard(client, "aging")
    _run_with(old, Result.PASS, datetime.now(UTC) - timedelta(days=2))
    fresh = _onboard(client, "fresh")
    _run_with(fresh, Result.PASS)

    html = client.get("/").text

    assert "stale" in _card(html, "aging")
    assert "2 days ago" in _card(html, "aging")
    assert "stale" not in _card(html, "fresh")
