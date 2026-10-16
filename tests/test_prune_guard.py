"""AT-735: the video prune runs after the O5 ask and can never fail a saved run."""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.stages import run_launcher, video_retention
from autotester.stages.video_retention import prune_old_videos_safely
from autotester.store.project_store import ProjectStore


def _patch(monkeypatch: pytest.MonkeyPatch, calls: list[str], prune) -> None:
    monkeypatch.setattr(run_launcher, "advise_after_run", lambda *a: calls.append("advise"))
    monkeypatch.setattr(run_launcher, "ask_for_what_it_did_not_recognise",
                        lambda *a: calls.append("ask"))
    monkeypatch.setattr(run_launcher, "prune_old_videos_safely", prune)


def test_prune_runs_after_the_ask_step(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch(monkeypatch, calls, lambda *a: calls.append("prune"))
    run_launcher.run_follow_ups(object(), "run-1", None)  # type: ignore[arg-type]
    assert calls == ["advise", "ask", "prune"]


def test_a_raising_prune_is_skipped_and_the_ask_already_happened(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(*a, **k):
        raise OSError("disk")
    monkeypatch.setattr(video_retention, "prune_old_videos", boom)
    assert prune_old_videos_safely(ProjectStore("demo", tmp_path)) == []


def test_follow_ups_do_not_raise_when_prune_errors(monkeypatch: pytest.MonkeyPatch,
                                                   tmp_path: Path) -> None:
    calls: list[str] = []
    _patch(monkeypatch, calls, prune_old_videos_safely)
    def boom(*a, **k):
        raise OSError("disk")
    monkeypatch.setattr(video_retention, "prune_old_videos", boom)
    run_launcher.run_follow_ups(ProjectStore("demo", tmp_path), "run-1", None)
    assert calls == ["advise", "ask"]
