"""mongo-store U8 test rig: a synthetic file-backed data root, a SQLite auth file and the
hand-written fake Mongo server, driven through the real `autotester store` Typer app.

Nothing here touches a real Mongo, a real `.env` or a real approval key. Every value is synthetic.
`Rig.tree()` hashes the source tree so a test can prove no source file changed (M42).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from fake_mongo import CANARY, FakeMongoServer, seams
from typer.testing import CliRunner

from autotester.auth import accounts, db, sessions
from autotester.auth.store_mongo import reset_auth_store
from autotester.cli_store import app
from autotester.schema.approval import RunApproval
from autotester.schema.approval_revocation import ApprovalRevocation
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project, SecretRef
from autotester.store.mongo_backend import reset_default_backend

URI = f"mongodb://user:{CANARY}@db.example/"
USER_VALUE, PASS_VALUE, STRAY_VALUE = "Qv7-synth-user-1", "Qv7-synth-pass-2", "Qv7-synth-stray-3"
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic-shot"
CEO_CANARY = "CEO-ITEM-canary-Zx9-never-in-a-report"  # the private answer list's item text (D-128)
PRIVATE_KEY = ".work/ceo-bench/demo/atomic-list.json"
DECLARED = ("DEMO_USER", "DEMO_PASS", "AUTOTESTER_APPROVAL_KEY", "PATHLYNKS_MONGO_URI")


class Rig:
    def __init__(self, tmp: Path) -> None:
        self.root, self.server, self.runner = tmp / "root", FakeMongoServer(), CliRunner()
        self.auth_dir = tmp / "auth"
        self.opened = 0  # Mongo clients the tool created: a dry run must leave this at 0

    def write(self, key: str, data: str | bytes) -> None:
        path = self.root.joinpath(*key.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def tree(self) -> str:
        """Names and bytes of every file in the source tree and the auth file."""
        digest = hashlib.sha256()
        for base in (self.root, self.auth_dir):
            for path in sorted(base.rglob("*")) if base.exists() else []:
                digest.update(path.relative_to(base).as_posix().encode())
                digest.update(path.read_bytes() if path.is_file() else b"")
        return digest.hexdigest()

    def invoke(self, *args: str) -> Any:
        reset_default_backend()
        reset_auth_store()
        with seams(client_factory=self._client):
            result = self.runner.invoke(app, list(args))
        reset_default_backend()
        reset_auth_store()
        return result

    def _client(self, _uri: str) -> Any:
        self.opened += 1
        return self.server.client()

    def docs(self, name: str) -> list[dict[str, Any]]:
        return [d for db_ in self.server.databases.values() for c in [db_.collections.get(name)]
                if c is not None for d in c.docs]

    def everywhere(self) -> str:
        return repr([(d.name, n, c.docs) for d in self.server.databases.values()
                     for n, c in d.collections.items()])


def approval(target: str, *, sign: bool = True) -> RunApproval:
    row = RunApproval(project="demo", run_kind=ApprovalKind.CRAWL, target=target, scope="t",
                      max_actions=9, wall_clock_s=60.0, granted_by="Umesh",
                      granted_at="2026-10-13", expires_at="2099-01-01")
    return row.sign() if sign else row


def seed_state(rig: Rig) -> list[str]:
    """A small project: documents, a row set, signed approvals, a screenshot and every
    M25 family that must stay out. Returns the two approval rows exactly as written."""
    project = Project(slug="demo", name="Demo", base_url="https://demo.test",
                      allowed_domains=["demo.test"],
                      secrets=[SecretRef(key=k) for k in DECLARED])
    rig.write("projects/demo/project.json", project.model_dump_json(exclude_none=True))
    rig.write("projects/demo/cases.jsonl", '{"id": "c1", "title": "one"}\n{"id": "c2"}\n')
    first = approval("https://a.demo.test/")
    rows = [first.model_dump_json(exclude_none=True),
            approval("https://b.demo.test/").model_dump_json(exclude_none=True)]
    rig.write("projects/demo/approvals.jsonl", "\n".join(rows) + "\n")
    revoke = ApprovalRevocation(approval_id=first.id, revoked_by="u", reason="r",
                                revoked_at="2026-10-14T00:00:00+00:00").sign()
    rig.write("projects/demo/approval_revocations.jsonl",
              revoke.model_dump_json(exclude_none=True) + "\n")
    rig.write("projects/demo/runs/r1/run.json", '{"id": "r1", "status": "done"}')
    rig.write("projects/demo/runs/r1/shot.png", PNG)
    rig.write(".work/audit.jsonl", '{"event": "x"}\n')
    for key in ("projects/demo/profiles/p1/Cookies", "projects/demo/exports/report.xlsx",
                "projects/demo/chunks/c1.json", "projects/demo/crawl_summaries/s.json",
                ".work/scratch/log.txt"):
        rig.write(key, "private" if key.endswith(".json") else b"\x00\x01")
    rig.write("projects/demo/loose.xlsx", b"sheet")
    rig.write(PRIVATE_KEY, f'{{"items": [{{"text": "{CEO_CANARY}"}}]}}')
    rig.write(".env", f"DEMO_USER={USER_VALUE}\nDEMO_PASS={PASS_VALUE}\nSTRAY_KEY={STRAY_VALUE}\n"
                      "AUTOTESTER_APPROVAL_KEY=test-only-signing-key-never-a-real-secret\n")
    return rows


def seed_auth(rig: Rig) -> dict[str, int]:
    """Three accounts (the first becomes admin), one project grant-free session each."""
    ids = {}
    for name in ("a", "b", "c"):
        ids[name] = accounts.signup(f"{name}@team.test", "correct-horse-battery").id
        sessions.create_session(ids[name])
    return ids


def make_rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Rig:
    r = Rig(tmp_path)
    r.root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(r.root))
    monkeypatch.setenv("AUTOTESTER_AUTH_DIR", str(r.auth_dir))
    monkeypatch.setenv("AUTOTESTER_TEST_NO_AUTO_LOGIN", "1")
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS", "AUTOTESTER_MONGO_URI",
                 "AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_HOSTED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PATHLYNKS_MONGO_URI", URI)
    db._READY.clear()
    return r
