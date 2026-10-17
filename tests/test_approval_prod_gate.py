"""Production approval gate, approval traceability, crawl redaction, and the tracked crawl
summary + `scripts/check_crawl_approval.py` (T-145 blind-checker findings D1-D3).

Gate: D-088 (a production target needs a signed human-granted `production: true` row);
D-068 account-derived rows never cover a project declared `production`.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from crawl_fake import grant_crawl_approval, make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.consent import ApprovalRequired
from autotester.core.paths import ProjectPaths
from autotester.schema.approval import RunApproval
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project, SecretRef
from autotester.schema.screen_graph import ElementRef, ScreenNode
from autotester.stages import explore_summary
from autotester.stages.explore import run_crawl
from autotester.stages.explore_consent import covering_approval
from autotester.store.project_store import ProjectStore

BOUNDS = CrawlBounds()


def _row(project: Project, *, production: bool, by: str = "Umesh",
         kind: ApprovalKind = ApprovalKind.CRAWL, target: str | None = None,
         granted_at: str = "2026-10-13") -> RunApproval:
    return RunApproval(
        project=project.slug, run_kind=kind, target=target or project.base_url,
        scope="t", max_actions=BOUNDS.max_actions, wall_clock_s=BOUNDS.wall_clock_s,
        granted_by=by, granted_at=granted_at, expires_at="2099-01-01", production=production,
    ).sign()


def _prod_project() -> Project:
    return make_project().model_copy(update={"production": True})


def test_production_project_refuses_a_non_production_row_with_a_named_reason(
        tmp_path: Path) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    bad = store.add_approval(_row(project, production=False))
    with pytest.raises(ApprovalRequired) as why:
        covering_approval(project, store, BOUNDS)
    assert bad.id in str(why.value)
    assert "production" in str(why.value) and "D-088" in str(why.value)


def test_production_project_refuses_an_account_derived_row_even_if_production_true(
        tmp_path: Path) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    derived = store.add_approval(_row(project, production=True, by="account-derived:DEMO"))
    with pytest.raises(ApprovalRequired, match="account-derived") as why:
        covering_approval(project, store, BOUNDS)
    assert derived.id in str(why.value)


def test_production_project_refuses_wrong_target_or_run_kind(tmp_path: Path) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    store.add_approval(_row(project, production=True, target="https://app.test/other"))
    store.add_approval(_row(project, production=True, kind=ApprovalKind.LIVE_CASE))
    with pytest.raises(ApprovalRequired):
        covering_approval(project, store, BOUNDS)


def test_production_project_accepts_a_human_production_row_among_decoys(
        tmp_path: Path) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    store.add_approval(_row(project, production=False, granted_at="2026-10-12"))
    good = store.add_approval(_row(project, production=True))
    assert covering_approval(project, store, BOUNDS).id == good.id


def test_non_production_project_is_unchanged(tmp_path: Path) -> None:
    project = make_project()
    store = ProjectStore("demo", tmp_path)
    row = store.add_approval(_row(project, production=False))
    assert covering_approval(project, store, BOUNDS).id == row.id


def test_pathlynks_declares_production_and_prepod_does_not() -> None:
    root = Path(__file__).resolve().parents[1] / "projects"
    live = json.loads((root / "pathlynks" / "project.json").read_text(encoding="utf-8"))
    pre = json.loads((root / "pathlynks-prepod" / "project.json").read_text(encoding="utf-8"))
    assert live["production"] is True
    assert pre.get("production", False) is False


def _crawl(tmp_path: Path, project: Project, store: ProjectStore):
    session, _page = make_session(tmp_path, project)
    return run_crawl(project, session, store, observer=PageObserver(), bounds=BOUNDS)


def test_crawl_records_the_gating_approval_and_writes_a_summary(tmp_path: Path) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    store.add_approval(_row(project, production=False, granted_at="2026-10-12"))
    good = store.add_approval(_row(project, production=True))
    crawl = _crawl(tmp_path, project, store)
    on_disk = store.load_crawl(crawl.id)
    assert on_disk.approval_id == good.id and on_disk.approval_production is True
    [summary] = store.list_crawl_summaries()
    assert summary.crawl_id == crawl.id and summary.approval_id == good.id
    assert summary.project_production is True
    text = store.paths.crawl_summary(crawl.id).read_text(encoding="utf-8")
    assert "http" not in text  # no URLs / page content


def test_production_crawl_without_a_production_row_never_starts(tmp_path: Path) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    store.add_approval(_row(project, production=False))
    with pytest.raises(ApprovalRequired):
        _crawl(tmp_path, project, store)
    assert store.list_crawl_ids() == []


def test_crawl_artifacts_mask_the_test_account_email(tmp_path: Path) -> None:
    email = "tester.account@example.org"
    project = Project(slug="demo", name="Demo", base_url="https://app.test",
                      allowed_domains=["app.test"],
                      secrets=[SecretRef(key="DEMO_EMAIL", domains=["app.test"])])
    env = tmp_path / ".env"
    env.write_text(f"DEMO_EMAIL={email}\n", encoding="utf-8")
    session = BrowserSession(project, SecretStore.load(project, env),
                             tmp_path / "shots", ProjectPaths("demo", tmp_path))
    node = ScreenNode(
        crawl_id="c1", project="demo", url_template="/p", url_example="https://app.test/p",
        signature="sig", title=f"Hi {email}",
        elements=[ElementRef(role="textbox", name=email,
                             selector=f'role=textbox[name="{email}"]')],
    )
    clean = explore_summary.scrubbed(SimpleNamespace(session=session), node)
    assert email not in clean.model_dump_json()
    assert clean.id == node.id  # identity unchanged by masking


# -- D3: check_crawl_approval.py from a clean checkout ----------------------------------

def _load_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_crawl_approval.py"
    spec = importlib.util.spec_from_file_location("check_crawl_approval_t", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ProjectStore", lambda s: ProjectStore(s, tmp_path))
    monkeypatch.setattr(mod, "load_repo_env", lambda: None)
    monkeypatch.setattr(sys, "argv", ["check_crawl_approval.py", "demo"])
    return mod


def _track_summaries(root: Path) -> None:
    """Make `root` a git repo with every crawl summary COMMITTED: the done_check judges only
    git-tracked summaries (AT-999), as in a real checkout."""
    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                        *args], check=True, capture_output=True)
    git("init")
    git("add", "-A", "--", "projects")
    git("commit", "-m", "reviewed crawl")


def test_done_check_passes_from_summary_alone_for_a_production_row(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    store.add_approval(_row(project, production=True))
    _crawl(tmp_path, project, store)
    store.save_project(project)
    shutil.rmtree(store.paths.crawls_dir)  # clean checkout: the crawl dir is gitignored
    _track_summaries(tmp_path)
    assert _load_script(tmp_path, monkeypatch).main() == 0
    assert "production=True" in capsys.readouterr().out


def test_done_check_fails_when_a_production_project_was_gated_by_a_non_production_row(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    plain = make_project()
    store = ProjectStore("demo", tmp_path)
    store.add_approval(_row(plain, production=False))
    _crawl(tmp_path, plain, store)  # legitimately allowed while undeclared
    store.save_project(_prod_project())  # D-088 now declares it production
    _track_summaries(tmp_path)
    assert _load_script(tmp_path, monkeypatch).main() == 1
    assert "not production:true" in capsys.readouterr().out


def test_done_check_fails_without_a_recorded_approval_id(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    project = make_project()
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = _crawl(tmp_path, project, store)
    path = store.paths.crawl_summary(crawl.id)
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["approval_id"]
    path.write_text(json.dumps(data), encoding="utf-8")
    store.save_project(project)
    _track_summaries(tmp_path)
    assert _load_script(tmp_path, monkeypatch).main() == 1
    assert "no gating approval id" in capsys.readouterr().out
