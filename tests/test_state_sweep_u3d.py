"""mongo-store U3d: the swept stages/ and sources/ sites go through the store, not around it.

The backend is swapped for the in-memory double, so a read that bypasses `filestore` sees the
disk and not the double, and a write or delete that bypasses it touches the disk and fails the
tree check. `sweep_orphans` keeps one raw `.tmp-*` glob (M53-gated row); its own test runs in
file mode and pins that leg.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from state_backends import InMemoryBackend

import autotester.store.filestore as filestore
from autotester.core.redact import Redactor
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.video_review import VideoReview
from autotester.sources.intake_commit import RECORDING_STEM, staging_root, sweep_orphans
from autotester.stages.explore_consent import _approval_history
from autotester.stages.unified_report_findings import load_run_findings
from autotester.stages.video_review_store import stored_reviews
from autotester.store.filestore import (
    delete_path,
    exists_path,
    list_children,
    mtime_path,
    write_bytes,
    write_json,
)
from autotester.store.project_store import ProjectStore


@pytest.fixture
def memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    backend = InMemoryBackend()
    monkeypatch.setattr(filestore, "_backend", lambda name: backend)
    return backend


def _tree(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def _review(review_id: str, source_id: str) -> VideoReview:
    return VideoReview(id=review_id, source_id=source_id, status="ok", summary="flow", items=[],
                       duration_s=10, not_reviewed=[], calls=0, cost_usd=0.0)


def test_the_path_verbs_read_and_delete_through_the_store(memory: InMemoryBackend,
                                                          tmp_path: Path) -> None:
    folder = tmp_path / "projects" / "p" / "runs"
    write_bytes(folder / "a.json", b"{}")
    write_bytes(folder / "b.txt", b"x")
    assert exists_path(folder / "a.json") and not exists_path(folder / "zzz.json")
    assert list_children(folder) == ["a.json", "b.txt"]
    assert list_children(folder, suffix=".json") == ["a.json"]
    assert mtime_path(folder / "a.json") is not None and mtime_path(folder / "zzz.json") is None
    delete_path(folder / "a.json")
    delete_path(folder / "a.json")  # missing_ok by default, like unlink(missing_ok=True)
    assert list_children(folder) == ["b.txt"]
    assert _tree(tmp_path) == []


def test_stored_reviews_lists_orders_and_filters_from_the_store(memory: InMemoryBackend,
                                                                tmp_path: Path) -> None:
    store = ProjectStore("p", tmp_path)
    for review_id, source in (("rv1", "src_a"), ("rv2", "src_b"), ("rv3", "src_a")):
        write_json(store.paths.review_path(review_id), _review(review_id, source))
    found = stored_reviews(store.paths, "src_a")
    assert sorted(r.id for r in found) == ["rv1", "rv3"]
    assert _tree(tmp_path) == []


def test_load_run_findings_of_an_empty_run_reads_the_store(memory: InMemoryBackend,
                                                           tmp_path: Path) -> None:
    store = ProjectStore("p", tmp_path)
    assert load_run_findings(store, "r1", Redactor({})) == []
    assert _tree(tmp_path) == []


def test_the_approval_history_spans_projects_in_the_store(memory: InMemoryBackend,
                                                          tmp_path: Path) -> None:
    for slug in ("one", "two"):
        ProjectStore(slug, tmp_path).add_approval(RunApproval(
            project=slug, run_kind=ApprovalKind.CRAWL, target="https://x.example",
            scope="fixture", max_actions=5, wall_clock_s=60, granted_by="test",
            granted_at="2026-09-08", expires_at="2099-01-01").sign())
    history = _approval_history(ProjectStore("one", tmp_path))
    assert sorted(a.project for a in history) == ["one", "two"]
    assert _tree(tmp_path) == []


def test_sweep_orphans_lists_and_deletes_through_the_store(memory: InMemoryBackend,
                                                           tmp_path: Path) -> None:
    store = ProjectStore("p", tmp_path)
    base = store.paths.sources_dir
    write_bytes(base / "orphan" / f"{RECORDING_STEM}.mp4", b"v")
    write_bytes(base / "orphan" / "transcript.json", b"{}")  # derived data: left alone
    assert sweep_orphans(store) == 1
    assert list_children(base / "orphan") == ["transcript.json"]
    assert not (tmp_path / "projects").exists()  # `.work/intake` scratch stays raw (M53-gated)


def test_sweep_orphans_in_file_mode_removes_recordings_and_atomic_temps(tmp_path: Path,
                                                                        monkeypatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("p", tmp_path)
    base = store.paths.sources_dir
    orphan, bare = base / "orphan", base / "bare"
    orphan.mkdir(parents=True)
    bare.mkdir()
    (orphan / f"{RECORDING_STEM}.mp4").write_bytes(b"v")
    (orphan / ".tmp-abc").write_bytes(b"t")  # an atomic-write temp: hidden from list_children
    (orphan / "transcript.json").write_text("{}")
    (bare / ".tmp-def.mp4").write_bytes(b"t")
    (base / "stray.txt").write_text("not a folder")
    leftover = staging_root(store) / "old"
    leftover.mkdir(parents=True)
    assert sweep_orphans(store) == 4  # leftover staging, recording, two .tmp-*
    assert not leftover.exists() and not bare.exists()  # an emptied folder is removed
    assert sorted(p.name for p in orphan.iterdir()) == ["transcript.json"]
    assert (base / "stray.txt").exists()
