"""Shared fixtures and helpers for the Add-videos route tests (test_ui_intake*.py)."""

from __future__ import annotations

from pathlib import Path

import pytest
from asgi_helpers import chunked, multipart_head, multipart_tail
from drive_fakes import FakeDrive
from fastapi.testclient import TestClient

from autotester.core.paths import ENV_ROOT
from autotester.schema.project import Project
from autotester.schema.server_settings import ServerSettings
from autotester.store.project_store import ProjectStore
from autotester.store.server_settings import save_server_settings
from autotester.ui import intake_gate, routes_intake
from autotester.ui.app import app
from autotester.ui.intake_gate import IntakeActor, IntakeRefused

MIB = 1024 * 1024
UPLOAD = "/projects/demo/sources/upload"
DRIVE = "/projects/demo/sources/drive"


class FakeGate:
    def __init__(self, email="dev@vidysea.test", refuse=None, refuse_recheck=None):
        self.email, self.refuse, self.refuse_recheck = email, refuse, refuse_recheck
        self.checks, self.rechecks = [], []

    def check(self, request, slug):
        self.checks.append(slug)
        if self.refuse:
            raise IntakeRefused(*self.refuse)
        return IntakeActor(email=self.email)

    def recheck(self, actor, slug):
        self.rechecks.append((actor.email, slug))
        if self.refuse_recheck:
            raise IntakeRefused(*self.refuse_recheck)


@pytest.fixture
def store(tmp_path, monkeypatch) -> ProjectStore:
    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    st = ProjectStore("demo", tmp_path)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                            allowed_domains=["demo.test"]))
    return st


@pytest.fixture
def client(store) -> TestClient:
    return TestClient(app)


@pytest.fixture
def gate():
    fake = FakeGate()
    previous = intake_gate.set_gate(fake)
    yield fake
    intake_gate.set_gate(previous)


@pytest.fixture
def drive(monkeypatch) -> FakeDrive:
    fake = FakeDrive()
    monkeypatch.setattr(routes_intake, "drive_factory", lambda _store: fake)
    return fake


def _limit(tmp_path: Path, value: int) -> None:
    save_server_settings(ServerSettings(max_upload_bytes=value), tmp_path)


def _body(filename: str, data: bytes, **kw) -> list[bytes]:
    return [multipart_head(filename, **kw), *chunked(data), multipart_tail()]


def _leftovers(tmp_path: Path) -> list[Path]:
    found = []
    for area in ("intake", "drive-fetch", "gws", "uploads"):
        base = tmp_path / ".work" / area
        found += [p for p in base.rglob("*") if p.is_file()] if base.exists() else []
    return found


def _recordings(store: ProjectStore) -> list[Path]:
    base = store.paths.sources_dir
    return list(base.rglob("recording.*")) if base.exists() else []


