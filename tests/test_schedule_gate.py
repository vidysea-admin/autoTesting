"""TS5: a scheduled run needs the credential-derived approval; a missing one is a blocked slot
with no trace (R53). Drives the REAL `tick_project` with the REAL gate over a real
`ProjectStore`, counting what must stay at zero: queue entries, run directories, network
connects and browser sessions."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from schedule_fakes import daily, make_deps, utc

from autotester.core.consent import ApprovalRequired
from autotester.schema.project import Project, SecretRef
from autotester.schema.schedule import CredentialState, SlotOutcome
from autotester.stages import schedule_gate
from autotester.stages.schedule_gate import credential_gate, credential_state
from autotester.stages.scheduler import tick_project
from autotester.store.project_store import ProjectStore

SINCE = utc(2026, 10, 7, 12)
NOW = utc(2026, 10, 8, 9, 0, 10)
SECRET = "synthetic-account-value"


def _project(*, declared: bool = True, domains: tuple[str, ...] = ("demo.test",)) -> Project:
    refs = [SecretRef(key="DEMO_USER", domains=list(domains))] if declared else []
    return Project(slug="demo", name="Demo", base_url="https://demo.test/app",
                   allowed_domains=["demo.test"], secrets=refs)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path / "root"))
    root = tmp_path / "root"
    root.mkdir()
    counters = {"connect": 0, "browser": 0}

    def _connect(self, *a, **k):  # the transport: any outbound connect is counted, then refused
        counters["connect"] += 1
        raise OSError("blocked by test")

    def _browser(self, *a, **k):
        counters["browser"] += 1

    monkeypatch.setattr(socket.socket, "connect", _connect)
    from autotester.browser.session import BrowserSession
    monkeypatch.setattr(BrowserSession, "__init__", _browser)

    def make(project: Project, *, value: bool = True):
        store = ProjectStore("demo", root)
        store.save_project(project)
        (root / ".env").write_text(f"DEMO_USER={SECRET}\n" if value else "", encoding="utf-8")
        return store

    return make, counters, tmp_path


def _tick(project: Project, store: ProjectStore, tmp_path: Path, owner: str = "u1"):
    gate = credential_gate(project, store)
    deps, q = make_deps(tmp_path / "sched", "demo", gate=gate)
    sched = daily().model_copy(update={"owner": owner})
    return tick_project("demo", sched, NOW, deps, since=SINCE), q


def _runs(store: ProjectStore) -> list[str]:
    runs = store.paths.dir / "runs"
    return sorted(p.name for p in runs.iterdir()) if runs.exists() else []


@pytest.mark.parametrize(("declared", "value", "state"), [
    (False, False, "no_secretref"),
    (True, False, "secretref_without_value"),
])
def test_a_refused_credential_state_is_a_blocked_slot_with_no_trace(
    world, declared: bool, value: bool, state: str,
) -> None:
    make, counters, tmp_path = world
    project = _project(declared=declared)
    store = make(project, value=value)
    out, q = _tick(project, store, tmp_path)
    assert [r.outcome for r in out] == [SlotOutcome.BLOCKED_NO_CREDENTIALS]
    assert state in (out[0].detail or "")
    assert len(q) == 0 and _runs(store) == [] and store.list_approvals() == []
    assert counters == {"connect": 0, "browser": 0}


def test_a_value_outside_the_declared_domains_names_that_state(world) -> None:
    make, counters, tmp_path = world
    project = _project(domains=("elsewhere.test",))
    store = make(project)
    out, q = _tick(project, store, tmp_path)
    assert [r.outcome for r in out] == [SlotOutcome.BLOCKED_NO_CREDENTIALS]
    assert "target_outside_domains" in (out[0].detail or "")
    assert len(q) == 0 and store.list_approvals() == [] and counters["connect"] == 0


def test_an_admin_owned_schedule_on_an_uncredentialed_project_is_still_blocked(world) -> None:
    """AU15: no role skips an approval; the owner's rights are a different check."""
    make, _, tmp_path = world
    project = _project(declared=False)
    out, q = _tick(project, make(project, value=False), tmp_path, owner="admin")
    assert [r.outcome for r in out] == [SlotOutcome.BLOCKED_NO_CREDENTIALS] and len(q) == 0


def test_a_fully_provisioned_project_enqueues_exactly_one_entry(world) -> None:
    make, counters, tmp_path = world
    project = _project()
    store = make(project)
    out, q = _tick(project, store, tmp_path)
    assert [r.outcome for r in out] == [SlotOutcome.ENQUEUED] and len(q) == 1
    assert len(store.list_approvals()) == 1  # the D-068 audit row, minted by the real gate
    assert SECRET not in out[0].model_dump_json()
    assert counters == {"connect": 0, "browser": 0}  # the tick itself never touches the network


def test_a_missing_approval_after_the_state_check_is_blocked_with_the_reason(
    world, monkeypatch: pytest.MonkeyPatch,
) -> None:
    make, _, tmp_path = world
    project = _project()
    store = make(project)

    def _refuse(*a, **k):
        raise ApprovalRequired("approval is not available for this run")

    monkeypatch.setattr(schedule_gate, "covering_approval", _refuse)
    out, q = _tick(project, store, tmp_path)
    assert [r.outcome for r in out] == [SlotOutcome.BLOCKED_NO_CREDENTIALS]
    assert "approval" in (out[0].detail or "") and len(q) == 0


def test_a_gate_that_raises_fails_closed_and_enqueues_nothing(world, tmp_path: Path) -> None:
    _, _, scratch = world

    def _boom(slot):
        raise RuntimeError("gate crashed")

    deps, q = make_deps(scratch / "sched", "demo", gate=_boom)
    out = tick_project("demo", daily(), NOW, deps, since=SINCE)
    assert [r.outcome for r in out] == [SlotOutcome.FAILED] and len(q) == 0


def test_credential_state_is_read_only_and_never_returns_a_value(world) -> None:
    make, _, _ = world
    project = _project()
    store = make(project)
    assert credential_state(project, store) is CredentialState.PROVISIONED
    assert store.list_approvals() == []  # classifying mints nothing
    bare = _project(declared=False)
    assert credential_state(bare, make(bare, value=False)) is CredentialState.NO_SECRETREF
