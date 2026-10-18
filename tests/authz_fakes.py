"""Test doubles for the authorisation oracles (T-213): a counting fake app and the run scaffolding.

`FakeApp` plays the product AND the multi-role session at the two seams the oracles use
(`ReadTransport`, `EscalationTransport`): it answers a read per (role, path) from a table, counts
every call, and accepts or refuses a role-assign per control. Every row is synthetic (MPI2): names
and e-mails carry the marker strings in `PII_MARKERS`, so a test can scan the whole run tree for a
leaked value. No socket, no browser, no model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from autotester.schema.approval import RunApproval
from autotester.schema.authz_probe import (
    AuthzPlan,
    ProbeReply,
    RoleAssignControl,
)
from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.enums import ApprovalKind, WritePolicy
from autotester.schema.oracle_context import OracleContext
from autotester.schema.project import Project
from autotester.schema.role_step import RoleStep
from autotester.store.filestore import write_json
from autotester.store.project_store import ProjectStore

BASE = "https://app.test/"
NOW = datetime(2026, 10, 19, tzinfo=UTC)
PII_MARKERS = ("ZZNAME", "zz.leak", "ZZPHONE")
LEAK_KEY_ENV = "AUTOTESTER_LEAK_EVIDENCE_KEY"


def rows(prefix: str, count: int, start: int = 1) -> list[dict[str, object]]:
    """Synthetic student rows: an id plus two personal-looking cells that must never reach disk."""
    return [{"id": f"sid-{prefix}-{n}", "Name": f"ZZNAME {prefix}{n}",
             "Email": f"zz.leak.{prefix}{n}@school.invalid"}
            for n in range(start, start + count)]


class FakeApp:
    """Reads by (role, path+query); role-assign by control id. Counts everything."""

    def __init__(self) -> None:
        self.table: dict[tuple[str, str], ProbeReply] = {}
        self.reads: list[tuple[str, str]] = []
        self.assigns: list[tuple[str, str]] = []
        self.reverts: list[tuple[str, str]] = []
        self.reachable: dict[str, bool] = {}
        self.accepts: dict[str, bool] = {}
        self.revert_result: bool | Exception = True
        self.assign_raises = False
        self.read_raises = False

    def perform(self, step: RoleStep) -> None:  # the RoleSessionPort half the oracles never use
        raise AssertionError("the authz oracles must not drive the browser")

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        raise AssertionError("the authz oracles must not observe a channel")

    def serve(self, role: str, path: str, status: int = 200,
              data: list[dict[str, object]] | None = None) -> None:
        self.table[(role, path)] = ProbeReply(status=status, rows=data or [])

    def read(self, role_id: str, url: str) -> ProbeReply:
        parts = urlsplit(url)
        key = parts.path + (f"?{parts.query}" if parts.query else "")
        self.reads.append((role_id, key))
        if self.read_raises:
            raise OSError("boom ZZNAME must not be reported")
        return self.table.get((role_id, key), ProbeReply(status=404))

    def can_reach(self, role_id: str, control: RoleAssignControl) -> bool:
        return self.reachable.get(control.id, True)

    def assign(self, role_id: str, control: RoleAssignControl) -> bool:
        self.assigns.append((role_id, control.id))
        if self.assign_raises:
            raise RuntimeError("assign blew up")
        return self.accepts.get(control.id, False)

    def revert(self, role_id: str, control: RoleAssignControl) -> bool:
        self.reverts.append((role_id, control.id))
        if isinstance(self.revert_result, Exception):
            raise self.revert_result
        return self.revert_result

    @property
    def calls(self) -> int:
        return len(self.reads) + len(self.assigns) + len(self.reverts)


class ReadOnlyApp:
    """A port that can read but cannot escalate: no `can_reach` / `assign` / `revert`."""

    def __init__(self, inner: FakeApp) -> None:
        self._inner = inner

    def perform(self, step: RoleStep) -> None:
        raise AssertionError("not used")

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        raise AssertionError("not used")

    def read(self, role_id: str, url: str) -> ProbeReply:
        return self._inner.read(role_id, url)


class NoReadPort:
    """A session port that cannot read as a role: the oracle has nothing to probe with."""

    def perform(self, step: RoleStep) -> None:
        raise AssertionError("not used")

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        raise AssertionError("not used")


def approval(max_probes: int, *, production: bool = False, wall: float = 600.0,
             target: str = BASE) -> RunApproval:
    return RunApproval(
        project="demo", run_kind=ApprovalKind.ADVERSARIAL, target=target,
        scope="bounded authorisation probes on the fixture app", max_actions=0,
        max_probes=max_probes, wall_clock_s=wall, production=production, granted_by="umesh",
        granted_at="2026-10-10", expires_at="2026-12-01").sign()


class Scaffold:
    """One temp repo root with a saved project, optional approvals, a plan file and a context."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch, *,
                 write_policy: WritePolicy = WritePolicy.ALLOW_WRITES, production: bool = False,
                 key: bool = True) -> None:
        self.root = root
        monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
        if key:
            monkeypatch.setenv(LEAK_KEY_ENV, "synthetic-master-key-for-tests")
        else:
            monkeypatch.delenv(LEAK_KEY_ENV, raising=False)
        self.store = ProjectStore("demo", root=root)
        self.store.save_project(Project(
            slug="demo", name="Demo", base_url=BASE, allowed_domains=["app.test"],
            write_policy=write_policy, production=production))
        self.run_dir = root / "run"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.app = FakeApp()

    def grant(self, max_probes: int, **kw: object) -> None:
        self.store.add_approval(approval(max_probes, **kw))  # type: ignore[arg-type]

    def plan(self, plan: AuthzPlan) -> None:
        write_json(self.run_dir / "authz_plan.json", plan)

    def context(self, port: object | None = None) -> OracleContext:
        return OracleContext(project_slug="demo", run_dir=str(self.run_dir), scenario_id="s1",
                             role_ids=["tenant-a", "tenant-b"], platform_ids=["primary"],
                             port=port or self.app)

    def tree_text(self) -> str:
        """Every byte under the repo root as text: where a leaked value would show up."""
        return "\n".join(p.read_bytes().decode("utf-8", "replace")
                         for p in self.root.rglob("*") if p.is_file())

    def files(self, pattern: str) -> list[Path]:
        return sorted(self.root.rglob(pattern))
