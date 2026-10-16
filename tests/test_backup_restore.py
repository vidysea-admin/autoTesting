"""Round-trip and tamper tests for scripts/backup.sh and scripts/restore.sh (bash on a tmp dir)."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

BASH = shutil.which("bash")
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
pytestmark = pytest.mark.skipif(BASH is None, reason="bash not available")


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH or "bash", str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _seed(root: Path) -> None:
    (root / "projects" / "demo").mkdir(parents=True)
    (root / "projects" / "demo" / "flowspec.json").write_text('{"a": 1}\n')
    (root / ".work").mkdir()
    (root / ".work" / "run_queue.json").write_text("[]\n")
    (root / ".cache").mkdir()
    (root / ".cache" / "big.bin").write_bytes(b"x" * 100)
    (root / "profiles" / "demo").mkdir(parents=True)
    (root / "profiles" / "demo" / "Cookies").write_text("session")
    (root / ".env").write_text("SECRET=1\n")


def _backup(tmp_path: Path, *extra: str) -> Path:
    src = tmp_path / "data"
    src.mkdir(exist_ok=True)
    if not any(src.iterdir()):
        _seed(src)
    r = _run("backup.sh", "--root", str(src), "--out", str(tmp_path / "out"), *extra)
    assert r.returncode == 0, r.stderr
    return next((tmp_path / "out").glob("*.tar.gz"))


def test_round_trip_excludes_caches_and_secrets(tmp_path: Path) -> None:
    archive = _backup(tmp_path)
    manifest = Path(str(archive) + ".manifest").read_text()
    assert "secrets_included 0" in manifest and "files 2" in manifest
    dest = tmp_path / "restored"
    r = _run("restore.sh", str(archive), "--root", str(dest))
    assert r.returncode == 0, r.stderr
    expected = _tree(tmp_path / "data")
    for skipped in (".env", ".cache/big.bin", "profiles/demo/Cookies"):
        expected.pop(skipped)
    assert _tree(dest) == expected


def test_include_secrets_round_trip_warns(tmp_path: Path) -> None:
    src = tmp_path / "data"
    src.mkdir()
    _seed(src)
    r = _run("backup.sh", "--root", str(src), "--out", str(tmp_path / "out"), "--include-secrets")
    assert r.returncode == 0 and "WARNING" in r.stderr
    archive = next((tmp_path / "out").glob("*.tar.gz"))
    dest = tmp_path / "restored"
    assert _run("restore.sh", str(archive), "--root", str(dest)).returncode == 0
    expected = _tree(src)
    expected.pop(".cache/big.bin")
    assert _tree(dest) == expected


def test_tampered_archive_is_refused(tmp_path: Path) -> None:
    archive = _backup(tmp_path)
    with archive.open("ab") as fh:
        fh.write(b"tamper")
    dest = tmp_path / "restored"
    r = _run("restore.sh", str(archive), "--root", str(dest))
    assert r.returncode != 0 and "REFUSED" in r.stderr
    assert not dest.exists() or not any(dest.iterdir())


def test_non_empty_target_needs_force(tmp_path: Path) -> None:
    archive = _backup(tmp_path)
    dest = tmp_path / "restored"
    dest.mkdir()
    (dest / "keep.txt").write_text("mine")
    r = _run("restore.sh", str(archive), "--root", str(dest))
    assert r.returncode != 0 and "--force" in r.stderr
    assert _run("restore.sh", str(archive), "--root", str(dest), "--force").returncode == 0
    assert (dest / "projects" / "demo" / "flowspec.json").exists()
