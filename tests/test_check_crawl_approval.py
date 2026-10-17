"""AT-999: `scripts/check_crawl_approval.py` judges a named crawl, and only a committed summary.

T-145's close judged an untracked leftover (`crawl_01M4XTRF...`) instead of the reviewed crawl
(`crawl_01M4XRTH...`), because the script took the newest file on disk. These tests build a
throwaway git repo (`AUTOTESTER_ROOT`) with one committed, approved crawl summary and one newer
untracked leftover, run the real script as a subprocess, and read its PASS/FAIL line.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from autotester.core.ids import APPROVAL_KEY_ENV
from autotester.schema.approval import RunApproval
from autotester.schema.crawl import CrawlBounds
from autotester.schema.crawl_summary import CrawlSummary
from autotester.schema.enums import ApprovalKind, CrawlStatus
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_crawl_approval.py"
SLUG = "demo"
TARGET = "https://demo.test"
REVIEWED = "crawl_01REVIEWED"
LEFTOVER = "crawl_09LEFTOVER"
KEY = "unit-test-key-not-a-secret"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


def _summary(crawl_id: str, approval_id: str | None) -> CrawlSummary:
    return CrawlSummary(
        crawl_id=crawl_id, project=SLUG, status=CrawlStatus.COMPLETED, approval_id=approval_id,
        bounds=CrawlBounds(), started_at="2026-10-15T10:00:00", finished_at="2026-10-15T10:05:00")


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, ProjectStore, str]:
    monkeypatch.setenv(APPROVAL_KEY_ENV, KEY)
    store = ProjectStore(SLUG, tmp_path)
    store.save_project(
        Project(slug=SLUG, name="Demo", base_url=TARGET, allowed_domains=["demo.test"]))
    approval = RunApproval(
        project=SLUG, run_kind=ApprovalKind.CRAWL, target=TARGET, scope="fixture crawl",
        max_actions=10_000, wall_clock_s=100_000.0, granted_by="test",
        granted_at="2026-10-14", expires_at="2099-01-01").sign()
    store.add_approval(approval)
    _git(tmp_path, "init")
    return tmp_path, store, approval.id


def _run(root: Path, *args: str) -> tuple[int, str]:
    env = {**os.environ, "AUTOTESTER_ROOT": str(root), APPROVAL_KEY_ENV: KEY}
    done = subprocess.run([sys.executable, str(SCRIPT), SLUG, *args], env=env, text=True,
                          capture_output=True)
    return done.returncode, done.stdout + done.stderr


def _commit_all(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "reviewed crawl")


def test_untracked_newer_leftover_summary_is_not_judged_instead_of_the_reviewed_crawl(repo):
    root, store, approval_id = repo
    store.save_crawl_summary(_summary(REVIEWED, approval_id))
    _commit_all(root)
    store.save_crawl_summary(_summary(LEFTOVER, None))  # newer, never committed
    code, out = _run(root)
    assert code == 0 and REVIEWED in out and LEFTOVER not in out, out


def test_a_crawl_id_argument_judges_that_committed_summary_not_the_newest(repo):
    root, store, approval_id = repo
    store.save_crawl_summary(_summary(REVIEWED, approval_id))
    store.save_crawl_summary(_summary(LEFTOVER, None))  # newer AND committed, but unapproved
    _commit_all(root)
    code_newest, out_newest = _run(root)
    assert code_newest == 1 and LEFTOVER in out_newest, out_newest
    code, out = _run(root, REVIEWED)
    assert code == 0 and REVIEWED in out, out


def test_a_crawl_id_naming_an_untracked_summary_is_refused_not_judged(repo):
    root, store, approval_id = repo
    store.save_crawl_summary(_summary(REVIEWED, approval_id))
    _commit_all(root)
    store.save_crawl_summary(_summary(LEFTOVER, approval_id))  # would pass if it were judged
    code, out = _run(root, LEFTOVER)
    assert code == 1 and "not tracked" in out and "PASS" not in out, out


def test_only_untracked_summaries_fail_closed(repo):
    root, store, approval_id = repo
    _commit_all(root)  # project + approvals committed, no summary
    store.save_crawl_summary(_summary(LEFTOVER, approval_id))
    code, out = _run(root)
    assert code == 1 and "no tracked crawl summary" in out, out
