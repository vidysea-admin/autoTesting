"""One guarded execution path, metadata preservation and revoked-worker refusal (TF1/TF2)."""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval
from test_ui_runs_live_case_approval import _ready, _target

from autotester.schema.enums import Trigger
from autotester.schema.run_queue import QueueEntry
from autotester.schema.team_enums import RunVia
from autotester.stages.run_launcher import RunLaunchRefused, launch_run
from autotester.ui.app import app
from autotester.ui.routes_runs import _run_queued
from autotester.ui.run_queue import RunRefused


def _side_effect_counters(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    import httpx

    from autotester.browser.session import BrowserSession

    counts = {"browser": 0, "transport": 0}
    original = BrowserSession.__init__

    def browser(self, *args, **kwargs):
        counts["browser"] += 1
        original(self, *args, **kwargs)

    def transport(*args, **kwargs):
        counts["transport"] += 1
        pytest.fail("fixture execution reached outbound HTTP transport")

    monkeypatch.setattr(BrowserSession, "__init__", browser)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", transport)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", transport)
    return counts


@pytest.mark.parametrize("trigger,via", [(Trigger.MANUAL, RunVia.BUTTON),
                                        (Trigger.SCHEDULE, RunVia.SCHEDULE),
                                        (Trigger.CI, RunVia.API)])
@pytest.mark.parametrize("approved", [False, True])
def test_every_launcher_trigger_inherits_covering_approval_and_records_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trigger, via, approved: bool,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _ready(TestClient(app), tmp_path, monkeypatch)
    if approved:
        grant_live_case_approval(store, target=_target(store))
    counts = _side_effect_counters(monkeypatch)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    if not approved:
        with pytest.raises(RunLaunchRefused, match="no approval exists"):
            launch_run("demo", trigger=trigger, requested_by="fixture@team.test",
                       slot_key="fixture-slot", via=via)
        assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
        assert not list(store.paths.runs_dir.glob("*/run.json"))
        assert counts == {"browser": 0, "transport": 0}
    else:
        run = launch_run("demo", trigger=trigger, requested_by="fixture@team.test",
                         slot_key="fixture-slot", via=via)
        saved = store.load_run(run.id)
        assert saved == run
        assert (saved.trigger, saved.requested_by, saved.slot_key, saved.via) == (
            trigger, "fixture@team.test", "fixture-slot", via)
        assert saved.catalog_runnable_counts is not None
        assert counts["browser"] > 0 and counts["transport"] == 0


def test_only_launcher_constructs_and_executes_a_run() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    calls = {"Run": [], "_execute_with_trace": []}
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in calls):
                calls[node.func.id].append(path.relative_to(root).as_posix())
    assert calls == {"Run": ["autotester/stages/run_launcher.py"],
                     "_execute_with_trace": ["autotester/stages/run_launcher.py"]}
    tree = ast.parse((root / "autotester/stages/run_launcher.py").read_text(encoding="utf-8"))
    assert not any(isinstance(n, ast.ImportFrom) and n.module and
                   (n.module.startswith("fastapi") or "run_queue" in n.module or
                    n.module.startswith("autotester.auth")) for n in ast.walk(tree))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "launch_run")
    assert not any("skip" in a.arg for a in function.args.kwonlyargs)


@pytest.mark.parametrize("revoke", ["disable", "permission"])
def test_worker_rechecks_current_requester_before_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, revoke: str,
) -> None:
    from auth_harness import gate_on, group_id, team

    from autotester.auth import accounts, groups

    root = gate_on(tmp_path, monkeypatch)
    team()
    user = accounts.find_user("dev@team.test")
    assert user is not None
    if revoke == "disable":
        accounts.set_disabled(user.id, True)
    else:
        group = groups.get_group(group_id("developer"))
        groups.update_group(group.id, group.name, [p for p in group.permissions
                                                 if not p.startswith("project.run@")])
    monkeypatch.setattr("autotester.ui.routes_runs.launch_run",
                        lambda *a, **k: pytest.fail("revoked requester reached launcher"))
    counts = _side_effect_counters(monkeypatch)
    before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(RunRefused, match=r"project\.run"):
        _run_queued(QueueEntry(id="run-fixture", project="demo",
                               requested_by="dev@team.test"))
    assert {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    assert counts == {"browser": 0, "transport": 0}


@pytest.mark.parametrize("gate", ["provider", "credential", "approval"])
def test_waiting_worker_rechecks_all_execution_gates_without_browser_or_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gate: str,
) -> None:
    from autotester.schema.project import SecretRef

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _ready(TestClient(app), tmp_path, monkeypatch)
    monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")
    if gate != "approval":
        grant_live_case_approval(store, target=_target(store))
    if gate == "provider":
        monkeypatch.setattr("autotester.stages.run_launcher.for_role",
                            lambda *a, **k: type("Unavailable", (),
                                                {"available": lambda _: False})())
    elif gate == "credential":
        project = store.load_project()
        project.secrets.append(SecretRef(key="DEMO_PASSWORD", domains=["demo.test"]))
        store.save_project(project)
        case = store.list_cases()[0]
        case.steps[0].value = "{{SECRET:DEMO_PASSWORD}}"
        store.update_case(case)
    counts = _side_effect_counters(monkeypatch)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    reason = {"provider": "no AI provider", "credential": "has no value yet",
              "approval": "no approval exists"}[gate]
    with pytest.raises(RunRefused, match=reason):
        _run_queued(QueueEntry(id="run-waiting", project="demo", requested_by="local"))
    assert counts == {"browser": 0, "transport": 0}
    assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("entry", ["direct", "ui", "worker"])
def test_no_cases_refuses_before_even_constructing_an_unavailable_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    client = TestClient(app)
    store = _ready(client, tmp_path, monkeypatch)
    store.delete_case(store.list_cases()[0].id)
    monkeypatch.setattr("autotester.stages.run_launcher.for_role",
                        lambda *a, **k: pytest.fail("provider checked before the no-cases gate"))
    counts = _side_effect_counters(monkeypatch)
    if entry == "ui":
        response = client.post("/projects/demo/run", follow_redirects=False)
        assert response.status_code == 400 and "no cases to run" in response.text
    elif entry == "worker":
        monkeypatch.setenv("AUTOTESTER_AUTH_DISABLED", "1")
        with pytest.raises(RunRefused, match="no cases to run"):
            _run_queued(QueueEntry(id="run-empty", project="demo", requested_by="local"))
    else:
        with pytest.raises(RunLaunchRefused, match="no cases to run"):
            launch_run("demo")
    assert counts == {"browser": 0, "transport": 0}
    assert not store.paths.runs_dir.exists()
