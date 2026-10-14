"""The T-206 acceptance rig (qa/contracts/team-loop-acceptance.md "The rig"), used by tests only.

One job: stand up the REAL `autotester.ui.app:app` over a fresh data root with the login gate ON,
one HTTP client per user (own cookie jar, browser-style Origin), the AutoTester test accounts
(admin, subadmin, dev, tester, pending), a stub product on loopback with one switchable defect,
and an egress guard. State enters through the repo's own account/group/access functions and the
app's routes; the only direct writes are the `.env` fixture values and the stub project (via
`tests/team_run_fakes.runnable_project`). Reuses `auth_harness`, `team_run_fakes`,
`delivery_fakes`, `drive_fakes`, `video_review_fakes` -- defines no second copy of any of them.
"""

from __future__ import annotations

import hashlib
import socket
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, login, user_id
from delivery_fakes import CANARY_PAGE, CANARY_SECRET, forbid_real_smtp
from drive_fakes import FakeDrive
from fastapi.testclient import TestClient
from team_run_fakes import Counters, listing, patch_run_world, runnable_project
from video_review_fakes import RecordingProvider

from autotester.auth.access import set_owner, set_relation
from autotester.schema.auth import ProjectRelation
from autotester.schema.enums import Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Failure, Verdict
from autotester.store.bug_store import BugStore
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_intake, run_execution

SLUG = "stub"
OTHER = "other"
CRED_KEY = "STUB_USER_PW"
DEFECT_MARK = "STUB-DEFECT-ON"
ORIGIN = {"origin": "http://testserver"}
HTML = {"accept": "text/html"}
LOOPBACK = {"127.0.0.1", "::1", "localhost"}
ROLE_SEEDS = {"subadmin": "sub-admin", "dev": "developer", "tester": "tester"}


def email(role: str) -> str:
    return ADMIN if role == "admin" else f"{role}@team.test"


def with_origin(c: TestClient) -> TestClient:
    """A browser sends `Origin` on every POST; the rig's clients do the same."""
    c.headers.update(ORIGIN)
    return c


class EgressGuard:
    """Every socket connect is logged; a non-loopback one raises (TA1 e, TA13)."""

    def __init__(self) -> None:
        self.attempts: list[str] = []
        self.blocked: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        real = socket.socket.connect

        def guarded(sock: socket.socket, address: object) -> None:
            host = str(address[0]) if isinstance(address, tuple) else str(address)
            self.attempts.append(host)
            if host not in LOOPBACK:
                self.blocked.append(host)
                raise OSError(f"egress guard: non-loopback connect to {host} refused")
            return real(sock, address)  # type: ignore[arg-type]

        monkeypatch.setattr(socket.socket, "connect", guarded)


@dataclass
class World:
    root: Path
    stub_dir: Path
    stub_url: str
    egress: EgressGuard
    counters: type[Counters]
    provider: RecordingProvider
    drive: FakeDrive
    smtp_attempts: list[str]
    outbox: Path
    mode: str = "defect"
    users: dict[str, TestClient] = field(default_factory=dict)
    graded_log: list[str] = field(default_factory=list)

    def set_stub(self, mode: str) -> None:
        """`defect` (the failing page), `ok` (the fixed page) or `inconclusive`."""
        self.mode = mode
        body = f"<h1>Stub shop</h1><p>{CANARY_PAGE}</p>" + (
            f"<p>{DEFECT_MARK}</p>" if mode == "defect" else "")
        (self.stub_dir / "index.html").write_text(body, encoding="utf-8")

    def store(self, slug: str = SLUG) -> ProjectStore:
        return ProjectStore(slug, self.root)

    def bugs(self, slug: str = SLUG) -> BugStore:
        return BugStore(self.store(slug).paths.dir)

    def anonymous(self) -> TestClient:
        return with_origin(client())

    def snapshot(self) -> str:
        """A canonical hash of the data root (the login store and audit trail excluded)."""
        digest = hashlib.sha256()
        for name, data in listing(self.root).items():
            digest.update(name.encode() + b"\0" + hashlib.sha256(data).digest())
        return digest.hexdigest()

    def seam_calls(self) -> dict[str, object]:
        return {"provider": self.provider.calls, "drive": list(self.drive.opened),
                "sessions": self.counters.sessions, "graded": self.counters.graded,
                "outbox": sorted(p.name for p in self.outbox.glob("*")),
                "smtp": list(self.smtp_attempts), "blocked": list(self.egress.blocked)}


def _grader(world: World) -> Callable[..., tuple[RawResult, Verdict]]:
    def graded(case, session, judge, run_id, store_):
        Counters.graded += 1
        with urllib.request.urlopen(world.stub_url, timeout=5) as page:   # loopback only
            defect = DEFECT_MARK in page.read().decode()
        result = Result.FAIL if defect else Result.PASS
        if world.mode == "inconclusive":
            result = Result.INCONCLUSIVE
        world.graded_log.append(f"{run_id}:{result.value}")
        fails = [Failure(criterion_id="C1", reason="stub page shows the defect")] if defect else []
        return (RawResult(case_id=case.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case.id, result=result, grader_provider="mock",
                        criteria_total=1, criteria_met=0 if defect else 1, failures=fails))
    return graded


def build_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                serve_dir: Callable[[Path], str]) -> World:
    """The COLD world: the admin (first sign-up, AU7) and `pending` (no group); no stub project
    yet and nobody assigned. `add_team` warms it."""
    root = gate_on(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTOTESTER_ALLOWED_ORIGINS", ORIGIN["origin"])   # the browser's own origin
    monkeypatch.setattr("autotester.auth.passwords._HASHER",
                        PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
    egress = EgressGuard()
    egress.install(monkeypatch)
    stub_dir = tmp_path / "stub_product"
    stub_dir.mkdir()
    provider, drive = RecordingProvider(), FakeDrive()
    monkeypatch.setattr(routes_intake, "drive_factory", lambda _store: drive)
    world = World(root=root, stub_dir=stub_dir, stub_url=serve_dir(stub_dir), egress=egress,
                  counters=patch_run_world(monkeypatch), provider=provider, drive=drive,
                  smtp_attempts=forbid_real_smtp(monkeypatch), outbox=root / "outbox")
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", _grader(world))
    world.set_stub("defect")
    account(ADMIN)
    account(email("pending"))
    for role in ("admin", "pending"):
        world.users[role] = with_origin(login(email(role)))
    return world


def add_team(world: World) -> World:
    """Warm the world: `accounts.set_user_groups` (what the admin group screen calls) puts
    subadmin, dev and tester in their default groups; the stub project is owned by dev, assigned
    to subadmin; `other` belongs to nobody. `tester` has no relation to it until a video is
    shared and approved (TA10). The credential is declared
    and provisioned with the canary (TT6, D-068), so a press mints no second approval prompt."""
    for role, seed in ROLE_SEEDS.items():
        account(email(role), seed)
        world.users[role] = with_origin(login(email(role)))
    runnable_project(world.root, SLUG, credential=CRED_KEY, value=CANARY_SECRET)
    _point_at_stub(world)
    runnable_project(world.root, OTHER)
    set_owner(SLUG, user_id(email("dev")))
    set_relation(SLUG, user_id(email("subadmin")), ProjectRelation.ASSIGNED, True)
    return world


def _point_at_stub(world: World) -> None:
    """The stub project's base URL, allowed domain, credential scope and case target are the
    loopback stub product (the only target any scenario touches)."""
    store = world.store()
    project = store.load_project()
    assert project is not None
    for ref in project.secrets:
        ref.domains = ["127.0.0.1"]
    store.save_project(Project.model_validate(project.model_dump() | {
        "base_url": world.stub_url, "allowed_domains": ["127.0.0.1"]}))
    for case in store.list_cases():
        case.steps[0].target = world.stub_url + "/"
        store.update_case(case)


def press(world: World, who: str = "dev", slug: str = SLUG) -> str:
    """Press Test as `who`; returns the run id from the redirect (303 or the test fails)."""
    resp = world.users[who].post(f"/projects/{slug}/test", headers=HTML)
    assert resp.status_code == 303, (resp.status_code, resp.text[:300])
    return resp.headers["location"].rsplit("/", 1)[1]


__all__ = ["ADMIN", "CANARY_PAGE", "CANARY_SECRET", "CRED_KEY", "DEFECT_MARK", "HTML", "ORIGIN",
           "OTHER", "PASSWORD", "SLUG", "EgressGuard", "World", "add_team", "build_world",
           "email", "press", "with_origin"]
