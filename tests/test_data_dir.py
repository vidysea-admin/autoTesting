"""AUTOTESTER_DATA_DIR: mutable state lands under it, never the repo root; unset is unchanged."""

import re
from pathlib import Path

from autotester.core import paths
from autotester.core.paths import ProjectPaths, data_root, projects_root, repo_root, work_dir
from autotester.ui import run_queue

ROOT = Path(__file__).resolve().parents[1]


def test_unset_paths_unchanged(monkeypatch, tmp_path):
    monkeypatch.delenv("AUTOTESTER_DATA_DIR", raising=False)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    assert data_root() == tmp_path.resolve() == repo_root()
    assert projects_root() == tmp_path.resolve() / "projects"
    pp = ProjectPaths("demo")
    assert pp.dir == tmp_path.resolve() / "projects" / "demo"
    assert pp.profile_dir == tmp_path.resolve() / "profiles" / "demo"
    assert pp.env_file == tmp_path.resolve() / ".env"
    assert work_dir() == tmp_path.resolve() / ".work"
    assert run_queue._queue_file() == tmp_path.resolve() / ".work" / "run_queue.json"


def test_env_var_redirects_state_but_not_env_file(monkeypatch, tmp_path):
    repo, data = tmp_path / "repo", tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(repo))
    monkeypatch.setenv("AUTOTESTER_DATA_DIR", str(data))
    pp = ProjectPaths("demo")
    assert pp.env_file == repo.resolve() / ".env"
    assert pp.run_dir("r1").is_relative_to(data.resolve())
    assert pp.profile_dir.is_relative_to(data.resolve())
    assert work_dir().is_relative_to(data.resolve())
    assert paths.team_path("a", root=None).is_relative_to(data.resolve())
    assert ProjectPaths("demo", root=repo).dir.is_relative_to(repo.resolve())  # explicit root wins


def test_queue_filestore_evidence_land_under_data_dir(monkeypatch, tmp_path):
    repo, data = tmp_path / "repo", tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(repo))
    monkeypatch.setenv("AUTOTESTER_DATA_DIR", str(data))
    q = run_queue.RunQueue(path=run_queue._queue_file, spawn=lambda fn: None,
                           runner=lambda e: None)
    qf = run_queue._queue_file()
    q._save()
    pp = ProjectPaths("demo")
    pp.ensure()
    evidence = pp.bundles_dir("r1") / "shot.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("x", encoding="utf-8")
    from autotester.auth import audit
    audit._append({"action": "t"})
    assert list(repo.iterdir()) == []
    assert qf.is_relative_to(data.resolve()) and qf.exists()
    assert evidence.exists() and (data / ".work" / "audit.jsonl").exists()


def test_container_config_sets_data_dir_to_data():
    text = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")
    assert re.search(r'^export AUTOTESTER_DATA_DIR="\$\{AUTOTESTER_DATA_DIR:-/data\}"$', text, re.M)
    assert "/data" in (ROOT / "Dockerfile").read_text(encoding="utf-8")
