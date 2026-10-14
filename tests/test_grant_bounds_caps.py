"""One cap on a new grant's bounds, shared by the UI route and CLI `approve`:
max actions 2000, wall clock 24h, expiry 30 days. UI answers 400, CLI exits 1."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from auth_harness import account, gate_on, login
from test_approve_cli import BASE_URL, runner
from test_ui_production_approval import FORM, _prod

from autotester.cli import app
from autotester.core.consent import validate_grant_bounds
from autotester.store.project_store import ProjectStore


def _cli(*extra: str, days: int = 1) -> object:
    return runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL, "--scope", "s",
        "--granted-by", "umesh", "--expires", (date.today() + timedelta(days=days)).isoformat(),
        *extra])


def test_validator_boundaries() -> None:
    now = datetime(2030, 1, 1)
    validate_grant_bounds(2000, 86400.0, now + timedelta(days=30), now)
    for args in ((2001, 1.0, now), (1, 86400.1, now), (1, 1.0, now + timedelta(days=31))):
        with pytest.raises(ValueError):
            validate_grant_bounds(*args, now=now)


@pytest.mark.parametrize("extra,days,word", [
    (("--max-actions", "2001"), 1, "2000"),
    (("--wall-clock", "86401"), 1, "86400"),
    ((), 32, "30 days"),
])
def test_cli_refuses_over_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                              extra: tuple[str, ...], days: int, word: str) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    from autotester.schema.project import Project
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url=BASE_URL,
                               allowed_domains=["demo.test"]))
    result = _cli(*extra, days=days)
    assert result.exit_code == 1 and word in result.output
    assert store.list_approvals() == []


@pytest.mark.parametrize("over,word", [
    ({"max_actions": "2001"}, "2000"), ({"wall_clock_s": "86401"}, "86400"),
    ({"expires_at": "2099-09-11T12:00"}, "30 days"),
])
def test_ui_refuses_over_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                             over: dict[str, str], word: str) -> None:
    root = gate_on(tmp_path, monkeypatch)
    store = _prod(root)
    account("admin@team.test")
    admin = login("admin@team.test")
    form = {**FORM, **over}
    if "expires_at" not in over:
        form["expires_at"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    resp = admin.post("/projects/demo/crawl-approval", data=form)
    assert resp.status_code == 400 and word in resp.text
    assert store.list_approvals() == []
