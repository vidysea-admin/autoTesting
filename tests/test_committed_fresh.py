"""AT-697: doctor's L1 committed leg -- the committed blob must equal a fresh regeneration.

Every fixture CHECKS THE FILE OUT through `git clone` (with `core.autocrlf=true` forced so the
write-out converts LF to CRLF on every machine). A write-then-commit fixture would leave LF on
disk and pass whether or not the implementation normalises line endings (AT-697 constraint 2).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from autotester import doctor
from autotester.core.paths import RepoDocs
from autotester.ledger import committed_fresh as cf
from autotester.ledger.render import apply_map, render_snapshot

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
MAP_SKELETON = (
    "# map\n\n**Purpose:** p\n**Open me when:** w\n\n"
    "<!-- generated:map -->\n<!-- /generated:map -->\n"
    "<!-- generated:schema -->\n<!-- /generated:schema -->\n"
    "<!-- generated:scripts -->\n<!-- /generated:scripts -->\n"
)


def git(cwd: Path, *args: str) -> None:
    subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True)


def write_lf(path: Path, text: str) -> None:
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def source_repo(base: Path, *, commit_fresh: bool) -> Path:
    """A repo whose committed MAP.md is fresh or stale; docs/ARCHITECTURE.md for the snapshot."""
    src = base / "origin"
    (src / "src" / "autotester").mkdir(parents=True)
    (src / "docs").mkdir()
    write_lf(src / "src" / "autotester" / "thing.py", '"""Does one thing."""\n')
    write_lf(src / "docs" / "ARCHITECTURE.md",
             "# X\n\n**Purpose:** p\n\n## What it does\n\nIt tests.\n")
    write_lf(src / "docs" / "MAP.md", MAP_SKELETON)
    docs = RepoDocs(src)
    if commit_fresh:
        write_lf(docs.map, apply_map(docs))
        write_lf(docs.snapshot, render_snapshot(docs))
    else:
        write_lf(docs.snapshot, "# stale snapshot\n")
    git(src, "init", "-b", "main")
    git(src, "add", "-A")
    git(src, "commit", "-m", "seed")
    return src


def checked_out(base: Path, src: Path) -> Path:
    """A fresh clone: git itself writes the files out, converting LF to CRLF."""
    clone = base / "clone"
    subprocess.run(["git", "clone", "-c", "core.autocrlf=true", str(src), str(clone)],
                   check=True, capture_output=True)
    return clone


def test_fixture_really_checks_out_crlf(tmp_path: Path) -> None:
    clone = checked_out(tmp_path, source_repo(tmp_path, commit_fresh=True))
    assert b"\r\n" in (clone / "docs" / "MAP.md").read_bytes()


def test_a_fresh_committed_tree_is_clean_despite_crlf_on_disk(tmp_path: Path) -> None:
    """Sabotage target: drop the LF normalisation and this goes red on the CRLF checkout."""
    clone = checked_out(tmp_path, source_repo(tmp_path, commit_fresh=True))
    assert cf.check_committed_generated_fresh(clone) == []


def test_stale_committed_map_regenerated_on_disk_is_named(tmp_path: Path) -> None:
    """The row's own story: disk regenerated clean, the committed blob every clone gets is stale.
    Sabotage target: remove the committed-blob comparison and this goes red."""
    src = source_repo(tmp_path, commit_fresh=False)
    clone = checked_out(tmp_path, src)
    docs = RepoDocs(clone)
    docs.map.write_text(apply_map(docs), encoding="utf-8")  # fresh on disk, not committed
    found = [v for v in cf.check_committed_generated_fresh(clone) if v.rule == "stale-committed"]
    assert [v.location for v in found] == ["docs/MAP.md", "docs/SNAPSHOT.md"]
    assert all("committed" in v.detail for v in found)


def test_committing_the_regeneration_clears_it(tmp_path: Path) -> None:
    clone = checked_out(tmp_path, source_repo(tmp_path, commit_fresh=False))
    docs = RepoDocs(clone)
    docs.map.write_text(apply_map(docs), encoding="utf-8")
    docs.snapshot.write_text(render_snapshot(docs), encoding="utf-8")
    git(clone, "add", "-A")
    git(clone, "commit", "-m", "regenerate")
    assert cf.check_committed_generated_fresh(clone) == []


def test_doctor_run_wires_the_committed_leg(tmp_path: Path) -> None:
    clone = checked_out(tmp_path, source_repo(tmp_path, commit_fresh=False))
    docs = RepoDocs(clone)
    docs.map.write_text(apply_map(docs), encoding="utf-8")
    found = {(v.rule, v.location) for v in doctor.run(clone)}
    assert ("stale-committed", "docs/MAP.md") in found
    assert ("stale-generated", "docs/MAP.md") not in found  # the disk leg alone is blind to it


def test_no_git_or_no_commit_is_skipped_and_named_never_passed(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    (plain / "docs").mkdir(parents=True)
    write_lf(plain / "docs" / "MAP.md", MAP_SKELETON)
    found = cf.check_committed_generated_fresh(plain)
    assert [v.rule for v in found] == ["committed-leg-skipped"]
    assert found[0].location == "docs/MAP.md" and "not checked" in found[0].detail
    git(plain, "init", "-b", "main")  # a repo with no commit yet
    found = cf.check_committed_generated_fresh(plain)
    assert [v.rule for v in found] == ["committed-leg-skipped"]
    assert "committed-leg-skipped" not in {v.rule for v in doctor.blocking(found)}


def test_untracked_generated_file_in_a_committed_repo_is_stale(tmp_path: Path) -> None:
    src = source_repo(tmp_path, commit_fresh=True)
    git(src, "rm", "-q", "docs/SNAPSHOT.md")
    git(src, "commit", "-m", "drop snapshot")
    clone = checked_out(tmp_path, src)
    docs = RepoDocs(clone)
    docs.snapshot.write_text(render_snapshot(docs), encoding="utf-8")
    found = cf.check_committed_generated_fresh(clone)
    assert [(v.rule, v.location) for v in found] == [("stale-committed", "docs/SNAPSHOT.md")]
