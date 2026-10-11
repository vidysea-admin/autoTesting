"""`autotester ingest zip` / `ingest fetch-drive` (team-intake.md TI3, TI5, TI7): exit codes.

The CLI is what an operator runs on the server. The contract that matters here is that a partial
intake is NEVER exit 0, that JSON gives each member exactly one outcome, and that a bad link or a
missing project stops with a message and writes nothing.
"""

from __future__ import annotations

import json
import zipfile

import pytest
from drive_fakes import FakeDrive
from typer.testing import CliRunner
from zip_fixtures import add_member, build_zip, flip_data_byte, video

from autotester import cli_intake
from autotester.cli import app
from autotester.core.paths import ENV_ROOT
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

runner = CliRunner()


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    return store, tmp_path


def _invoke(*args):
    return runner.invoke(app, ["ingest", *args])


def test_ti3_zip_json_gives_every_member_one_outcome_and_exit_0_when_clean(project):
    store, tmp = project
    archive = build_zip(tmp / "ok.zip", [("a.mp4", video("a")), ("b.mp4", video("b")),
                                         ("c.mp4", video("c")), ("notes.pdf", b"%PDF"),
                                         ("readme.txt", b"hi")])
    result = _invoke("zip", "demo", str(archive), "--json")
    body = json.loads(result.stdout)
    assert result.exit_code == 0 and body["status"] == "ok" and body["exit_code"] == 0
    outcomes = [m["outcome"] for m in body["members"]]
    assert sorted(outcomes) == ["registered"] * 3 + ["skipped"] * 2
    assert len(store.list_sources()) == 3


def test_ti5_a_partial_zip_exits_2_and_the_others_still_register(project):
    store, tmp = project
    archive = build_zip(tmp / "p.zip", [("good1.mp4", video("g1", size=4096)),
                                        ("bad.mp4", video("bad", size=4096)),
                                        ("good2.mp4", video("g2"))])
    flip_data_byte(archive, "bad.mp4")
    result = _invoke("zip", "demo", str(archive))
    assert result.exit_code == 2 and "partial" in result.stdout
    assert "bad.mp4" in result.stdout and "corrupt" in result.stdout
    assert len(store.list_sources()) == 2


def test_ti5_a_file_that_is_not_a_zip_is_one_failure_and_exit_2(project):
    store, tmp = project
    fake = tmp / "notes.zip"
    fake.write_text("this is not a zip", encoding="utf-8")
    result = _invoke("zip", "demo", str(fake), "--json")
    assert result.exit_code == 2
    assert json.loads(result.stdout)["counts"]["failed"] == 1 and store.list_sources() == []


def test_a_missing_archive_or_project_stops_with_exit_1(project, tmp_path):
    assert _invoke("zip", "demo", str(tmp_path / "nope.zip")).exit_code == 1
    assert _invoke("zip", "ghost", str(tmp_path / "nope.zip")).exit_code == 1
    assert _invoke("fetch-drive", "ghost", "abcdef123").exit_code == 1


def test_ti1_the_cli_refuses_a_hostile_member_and_writes_nothing_outside(project):
    store, tmp = project
    archive = tmp / "h.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        add_member(zf, "../../outside.mp4", video("o"))
        add_member(zf, "fine.mp4", video("f"))
    result = _invoke("zip", "demo", str(archive))
    assert result.exit_code == 2 and "path traversal" in result.stdout
    assert not (tmp.parent / "outside.mp4").exists() and not (tmp / "outside.mp4").exists()
    assert len(store.list_sources()) == 1


def test_ti7_fetch_drive_registers_through_the_fake_and_exits_0(project, monkeypatch):
    store, _ = project
    drive = FakeDrive()
    drive.add("FILE000001", video("fd"))
    monkeypatch.setattr(cli_intake, "default_drive", lambda _store: drive)
    link = "https://drive.google.com/file/d/FILE000001/view?usp=sharing"
    result = _invoke("fetch-drive", "demo", link, "--uploaded-by", "dev@vidysea.test", "--json")
    assert result.exit_code == 0 and json.loads(result.stdout)["counts"]["registered"] == 1
    assert store.list_sources()[0].uploaded_by == "dev@vidysea.test"


def test_ti7_fetch_drive_refuses_a_hostile_link_before_any_fetch(project, monkeypatch):
    called = []
    monkeypatch.setattr(cli_intake, "default_drive", lambda _s: called.append(1))
    for bad in ["http://127.0.0.1/x", "file:///etc/passwd",
                "https://drive.google.com.evil.io/file/d/FILE000001"]:
        result = _invoke("fetch-drive", "demo", bad)
        assert result.exit_code == 2
        assert bad not in result.stdout + (result.stderr or "")  # the link is never echoed
    assert called == []


def test_ti7_fetch_drive_partial_folder_exits_2(project, monkeypatch):
    drive = FakeDrive()
    drive.add("GOODVID001", video("g"))
    bad = drive.add("BADVID0001", video("b"))
    drive.lie[bad] = {"md5": "f" * 32}
    drive.folder("FOLDER0001", ["GOODVID001", bad])
    monkeypatch.setattr(cli_intake, "default_drive", lambda _s: drive)
    result = _invoke("fetch-drive", "demo", "FOLDER0001")
    assert result.exit_code == 2 and "partial" in result.stdout

