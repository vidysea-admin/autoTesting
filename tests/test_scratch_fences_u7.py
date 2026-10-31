"""mongo-store U7 (M25, M49): the scratch and evidence fences resolve the path before judging it.

`scratch_*` act on the local disk under `<root>/.work/{intake,drive-fetch,gws}` only and
`evidence_mkdir` under `<root>/qa/evidence`. A name that merely looks right (`..`, a link or
junction, a look-alike prefix, a nested `qa/evidence`) and Mongo-routed `.work` state
(`team/`, `run_queue.json`, `audit.jsonl`, `drive-jobs/`) are refused.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_filestore_paths_u7 import root as _backend_root

from autotester.core.safe_names import UnsafeName
from autotester.store.filestore_paths import (
    evidence_mkdir,
    scratch_children,
    scratch_mkdir,
    scratch_mtime,
    scratch_rmtree,
    scratch_unlink,
)

root = _backend_root  # the per-backend data-root fixture, shared with its sibling file


def test_scratch_verbs_work_on_the_local_disk_under_work_and_touch_no_backend(root: Path) -> None:
    for sub in ("intake", "drive-fetch", "gws"):
        stage = root / ".work" / sub / "p" / "one"
        scratch_mkdir(stage)
        (stage / "f.bin").write_bytes(b"x")
        assert [c.name for c in scratch_children(stage.parent)] == ["one"]
        assert scratch_mtime(stage) is not None and scratch_mtime(stage / "nope") is None
        scratch_unlink(stage / "f.bin")
        scratch_unlink(stage / "f.bin")  # missing_ok
        scratch_rmtree(stage)
        assert not stage.exists() and scratch_children(stage) == []


def test_a_store_rooted_elsewhere_stages_in_its_own_work_dir_and_nowhere_else(
        root: Path, tmp_path: Path) -> None:
    export = tmp_path / "export" / "teaching"
    stage = export / ".work" / "intake" / "p"
    scratch_mkdir(stage, base=export)
    assert stage.is_dir() and [c.name for c in scratch_children(stage.parent, base=export)] == ["p"]
    scratch_rmtree(stage, base=export)
    assert not stage.exists()
    for target in (export / ".work" / "team" / "x", export / "projects" / "p", stage):
        with pytest.raises(UnsafeName):  # another root's scratch is not this root's
            scratch_mkdir(target)
    with pytest.raises(UnsafeName):
        scratch_mkdir(export / ".work" / "team" / "x", base=export)
    assert not (export / ".work" / "team").exists()


def _link(link: Path, target: Path) -> None:
    """A directory symlink, or a junction on a Windows account that may not create symlinks."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            raise
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                              capture_output=True, check=False)
        if done.returncode != 0:
            pytest.skip("no symlink or junction can be made here")


_NOT_SCRATCH = [
    "projects/p/x", "state.json", ".env",
    ".work/../projects/p",                 # `..` out of .work into state
    ".work/intake/../../projects/p",
    ".work/team/x", ".work/team/schedule/s.json",   # Mongo-routed state under .work
    ".work/run_queue.json", ".work/audit.jsonl", ".work/drive-jobs/j.json",
    ".work/intakeX/y",                     # look-alike prefix
    "projects/p/.work/intake/x",           # a .work that is not the repo's
    ".work",                               # the scratch parent itself is not a subtree
]


@pytest.mark.parametrize("where", _NOT_SCRATCH)
def test_scratch_verbs_refuse_anything_that_does_not_resolve_into_a_scratch_subtree(
        root: Path, where: str) -> None:
    target = root / where
    for verb in (scratch_mkdir, scratch_rmtree, scratch_unlink):
        with pytest.raises(UnsafeName):
            verb(target)
    with pytest.raises(UnsafeName):
        scratch_children(target)
    with pytest.raises(UnsafeName):
        scratch_mtime(target)
    assert not (root / "projects" / "p").exists()


def test_scratch_verbs_refuse_a_path_outside_the_repo_that_is_not_work_scratch(
        root: Path, tmp_path: Path) -> None:
    for target in (tmp_path / "elsewhere" / "x", tmp_path / ".work" / "team" / "x",
                   tmp_path / ".work" / "intake" / "x", tmp_path / "projects" / "p"):
        with pytest.raises(UnsafeName):
            scratch_mkdir(target)
        assert not target.exists()


def test_scratch_verbs_refuse_a_link_inside_work_that_points_at_state(root: Path) -> None:
    state = root / "projects" / "p"
    state.mkdir(parents=True)
    (state / "keep.json").write_text("{}", encoding="utf-8")
    _link(root / ".work" / "intake" / "evil", state)
    for verb in (scratch_rmtree, scratch_unlink):
        with pytest.raises(UnsafeName):
            verb(root / ".work" / "intake" / "evil" / "keep.json")
    with pytest.raises(UnsafeName):
        scratch_mkdir(root / ".work" / "intake" / "evil" / "new")
    assert (state / "keep.json").exists() and not (state / "new").exists()


def test_evidence_mkdir_creates_below_the_repos_qa_evidence_only(root: Path) -> None:
    evidence_mkdir(root / "qa" / "evidence" / "u7" / "run")
    assert (root / "qa" / "evidence" / "u7" / "run").is_dir()


@pytest.mark.parametrize("where", [
    "qa/evidence/../../projects/e",        # `..` out of the evidence dir
    "projects/p/qa/evidence/z",            # a nested look-alike inside state
    "xqa/evidence/y",                      # a look-alike prefix
    "qa/evidence_extra/y", "projects/e", "state.json",
])
def test_evidence_mkdir_refuses_a_path_that_does_not_resolve_below_qa_evidence(
        root: Path, where: str) -> None:
    with pytest.raises(UnsafeName):
        evidence_mkdir(root / where)
    assert not (root / "projects").exists() and not (root / "xqa").exists()


def test_evidence_mkdir_refuses_a_path_outside_the_repo_and_follows_a_declared_base(
        root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "export" / "qa" / "evidence" / "m"
    with pytest.raises(UnsafeName):
        evidence_mkdir(outside)
    evidence_mkdir(outside, base=tmp_path / "export")  # an export dir names its own anchor
    assert outside.is_dir()
    with pytest.raises(UnsafeName):
        evidence_mkdir(tmp_path / "export" / "projects" / "e", base=tmp_path / "export")


def test_evidence_mkdir_refuses_a_link_under_qa_evidence_that_points_at_state(root: Path) -> None:
    (root / "projects").mkdir()
    _link(root / "qa" / "evidence" / "evil", root / "projects")
    with pytest.raises(UnsafeName):
        evidence_mkdir(root / "qa" / "evidence" / "evil" / "made")
    assert not (root / "projects" / "made").exists()
