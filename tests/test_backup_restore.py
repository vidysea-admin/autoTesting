"""Round-trip and tamper tests for scripts/backup.sh and scripts/restore.sh (bash on a tmp dir)."""

from __future__ import annotations

import hashlib
import io
import re
import shutil
import subprocess
import sys
import tarfile
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


def _forge(archive: Path, extras: list[tuple[tarfile.TarInfo, bytes | None]]) -> None:
    """Append members and re-sign the manifest, as an attacker holding both files could."""
    raw = archive.read_bytes()
    members = []
    with tarfile.open(archive, "r:gz") as tf:
        for m in tf.getmembers():
            fh = tf.extractfile(m)
            members.append((m, fh.read() if fh else None))
    with tarfile.open(archive, "w:gz") as tf:
        for info, data in members + extras:
            tf.addfile(info, io.BytesIO(data) if data is not None else None)
    manifest = Path(str(archive) + ".manifest")
    lines = manifest.read_text().replace(
        hashlib.sha256(raw).hexdigest(), hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    manifest.write_text(lines)
    Path(str(manifest) + ".sha256").write_text(hashlib.sha256(manifest.read_bytes()).hexdigest())


def _file_member(name: str, data: bytes) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info, data


def test_relative_archive_path_works(tmp_path: Path) -> None:
    archive = _backup(tmp_path)
    r = subprocess.run(
        [BASH or "bash", str(SCRIPTS / "restore.sh"), f"out/{archive.name}", "--root", "rr"],
        capture_output=True, text=True, check=False, cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "rr" / "projects" / "demo" / "flowspec.json").exists()


def test_extra_member_not_in_manifest_is_refused(tmp_path: Path) -> None:
    archive = _backup(tmp_path)
    _forge(archive, [_file_member("evil.sh", b"rm -rf /")])
    dest = tmp_path / "restored"
    r = _run("restore.sh", str(archive), "--root", str(dest))
    assert r.returncode != 0 and "REFUSED" in r.stderr
    assert not (dest / "evil.sh").exists()


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE])
def test_link_members_are_refused(tmp_path: Path, kind: bytes) -> None:
    archive = _backup(tmp_path)
    info = tarfile.TarInfo("sneaky")
    info.type = kind
    info.linkname = "/etc/passwd"
    _forge(archive, [(info, None)])
    dest = tmp_path / "restored"
    r = _run("restore.sh", str(archive), "--root", str(dest))
    assert r.returncode != 0 and "non-regular" in r.stderr


def test_tampered_manifest_is_refused(tmp_path: Path) -> None:
    archive = _backup(tmp_path)
    manifest = Path(str(archive) + ".manifest")
    manifest.write_text(manifest.read_text() + "# edited\n")
    r = _run("restore.sh", str(archive), "--root", str(tmp_path / "restored"))
    assert r.returncode != 0 and "manifest sha256" in r.stderr


def test_nested_secrets_are_excluded(tmp_path: Path) -> None:
    src = tmp_path / "data"
    secrets = [
        "projects/x/.env", "projects/x/.env.local", "projects/x/.auth/db", "a/b/profiles/p/Cookies",
        "projects/x/credentials.json", "projects/x/id_rsa", "projects/x/id_rsa.pub", "k/key.pem",
        "k/server.key", "t/token.json", "t/my-service-account-1.json", "m/Cookies", "m/Login Data",
    ]
    for rel in [*secrets, "projects/x/keep.json", "projects/x/notes.txt"]:
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("v")
    archive = _backup(tmp_path)
    with tarfile.open(archive) as tf:
        names = {m.name for m in tf.getmembers() if m.isfile()}
    assert names == {"projects/x/keep.json", "projects/x/notes.txt"}


@pytest.mark.skipif(sys.platform == "win32", reason="backslash file names need a POSIX filesystem")
def test_backslash_name_is_verified(tmp_path: Path) -> None:
    src = tmp_path / "data"
    src.mkdir()
    (src / "we\ird.txt").write_text("one")
    archive = _backup(tmp_path)
    assert _run("restore.sh", str(archive), "--root", str(tmp_path / "ok")).returncode == 0
    _forge(archive, [])
    manifest = Path(str(archive) + ".manifest")
    manifest.write_text(re.sub(r"[0-9a-f]{64}( [ *]we)", "0" * 64 + r"\1", manifest.read_text()))
    Path(str(manifest) + ".sha256").write_text(hashlib.sha256(manifest.read_bytes()).hexdigest())
    r = _run("restore.sh", str(archive), "--root", str(tmp_path / "bad"))
    assert r.returncode != 0
