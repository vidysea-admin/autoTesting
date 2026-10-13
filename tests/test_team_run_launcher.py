"""TT4: the button reuses the one launcher, and the existing run behaviour is unchanged.

Scenarios: a teammate presses Test and the queue's worker calls `launch_run` once with the
manual trigger and that teammate; the button's modules contain no second way to build a `Run`,
start a browser or call the pipeline (AST check); a project with no cases, and one with no
AI provider, are refused with 400 before any browser exists (RU2); a finished press saves every
result, verdict and the `Run` exactly as the old Run button does (RU3).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from auth_harness import gate_on, team, user_id
from team_run_fakes import listing, patch_run_world, runnable_project

from autotester.auth.access import set_owner
from autotester.schema.enums import Trigger
from autotester.schema.project import Project
from autotester.schema.team_enums import RunVia
from autotester.stages import run_launcher
from autotester.store.project_store import ProjectStore

HTML = {"accept": "text/html"}
SRC = Path(__file__).resolve().parents[1] / "src" / "autotester" / "ui"
FORBIDDEN = {"BrowserSession", "_execute_with_trace", "run_case_pipeline",
             "run_cases_traced", "launch_run", "_run_queued", "default_session_factory"}


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    counters = patch_run_world(monkeypatch)
    users = team()
    store = runnable_project(root, "alpha", approved=True)
    set_owner("alpha", user_id("dev@team.test"))
    return root, users, counters, store, monkeypatch


def test_the_worker_calls_the_one_launcher_once_with_the_manual_trigger_and_the_user(world) -> None:
    _root, users, _counters, _store, monkeypatch = world
    calls: list[dict] = []
    real = inspect.signature(run_launcher.launch_run)

    def spy(*args, **kwargs):
        bound = real.bind(*args, **kwargs)
        bound.apply_defaults()
        calls.append(dict(bound.arguments))

    monkeypatch.setattr(run_launcher, "launch_run", spy)
    assert users["dev"].post("/projects/alpha/test", headers=HTML).status_code == 303
    assert len(calls) == 1
    assert calls[0]["slug"] == "alpha"
    assert calls[0]["trigger"] is Trigger.MANUAL
    assert calls[0]["requested_by"] == "dev@team.test" and calls[0]["via"] is RunVia.TEAM_BUTTON


@pytest.mark.parametrize("name", ["routes_team_run.py", "team_run_view.py"])
def test_the_button_modules_build_no_run_and_start_no_browser(name: str) -> None:
    tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    used |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom | ast.Import)
             for a in n.names}
    assert not used & FORBIDDEN, sorted(used & FORBIDDEN)
    built = {(n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", ""))
             for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "Run" not in built             # naming the type for a hint is fine; building is not
    assert "prepare_run" in used or name == "team_run_view.py"    # the gates are the launcher's


def test_a_project_with_no_cases_is_400_before_any_browser(world) -> None:
    root, users, counters, _store, _mp = world
    ProjectStore("empty", root).save_project(Project(
        slug="empty", name="Empty", base_url="https://empty.test", allowed_domains=["empty.test"]))
    set_owner("empty", user_id("dev@team.test"))
    before = listing(root)
    resp = users["dev"].post("/projects/empty/test", headers=HTML)
    assert resp.status_code == 400 and "no cases" in resp.text
    assert counters.sessions == 0 and listing(root) == before


def test_no_ai_provider_is_400_before_any_browser(world) -> None:
    root, users, counters, _store, monkeypatch = world
    import autotester.ui.routes_runs as routes_runs

    class Unavailable:
        def available(self) -> bool:
            return False

    monkeypatch.setattr(routes_runs, "for_role", lambda project, role: Unavailable())
    before = listing(root)
    resp = users["dev"].post("/projects/alpha/test", headers=HTML)
    assert resp.status_code == 400 and "no AI provider" in resp.text
    assert counters.sessions == 0 and listing(root) == before


def test_a_finished_press_saves_every_result_and_the_run_like_the_old_path(world) -> None:
    _root, users, counters, store, _mp = world
    location = users["dev"].post("/projects/alpha/test", headers=HTML).headers["location"]
    run = store.load_run(location.rsplit("/", 1)[1])
    assert run is not None and counters.graded == 1 and counters.sessions >= 1
    assert len(store.load_results(run.id)) == 1 and len(store.load_verdicts(run.id)) == 1  # RU3
