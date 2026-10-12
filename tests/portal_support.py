"""Shared setup for the video-portal tests (T-198b / G9, qa/contracts/team-intake.md TP1-TP6).

A scratch data root with the login gate ON, one project `demo` owned by the developer `dev`,
the sub-admin `sub` assigned to it, one real video file uploaded by `dev`, and a set of
signed-in clients: admin, sub, dev, dev2 (another developer), tester, tester2, nogroup.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from argon2 import PasswordHasher
from auth_harness import ADMIN, account, client, gate_on, login, project, user_id
from fastapi.testclient import TestClient

from autotester.auth.access import set_owner, set_relation
from autotester.schema.auth import ProjectRelation
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.store.project_store import ProjectStore

SLUG = "demo"
SENTINEL = b"SENTINEL-VIDEO-BYTES-7f3a91" * 40
DURATION = 120.0
ROLES = {"sub": "sub-admin", "dev": "developer", "dev2": "developer", "tester": "tester",
         "tester2": "tester", "nogroup": None}


def email(name: str) -> str:
    return ADMIN if name == "admin" else f"{name}@team.test"


@dataclass
class World:
    root: Path
    users: dict[str, TestClient]
    video: Source

    @property
    def vid(self) -> str:
        return self.video.id

    def page(self, vid: str | None = None) -> str:
        return f"/projects/{SLUG}/videos/{vid or self.vid}"


def add_video(root: Path, uploader: str | None, tag: str = "a", *, slug: str = SLUG,
              duration: float | None = DURATION, label: str = "Checkout demo") -> Source:
    data = SENTINEL + tag.encode()
    sha = hashlib.sha256(data).hexdigest()
    rel = f"sources/{sha[:12]}/recording.mp4"
    target = root / "projects" / slug / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return ProjectStore(slug, root).add_source(Source(
        project=slug, kind=SourceKind.VIDEO, path=rel, sha256=sha, duration_s=duration,
        label=label, uploaded_by=uploader))


def build_world(tmp_path: Path, monkeypatch) -> World:
    root = gate_on(tmp_path, monkeypatch)
    # a cheap hasher: these tests are about who may open a video, not about argon2's cost
    monkeypatch.setattr("autotester.auth.passwords._HASHER",
                        PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
    account(ADMIN)
    for name, seed in ROLES.items():
        account(email(name), seed)
    project(root, SLUG)
    set_owner(SLUG, user_id(email("dev")))
    set_relation(SLUG, user_id(email("sub")), ProjectRelation.ASSIGNED, True)
    video = add_video(root, email("dev"))
    users = {name: login(email(name)) for name in ("admin", *ROLES)}
    return World(root, users, video)


def anonymous() -> TestClient:
    return client()
