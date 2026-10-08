"""Portable team-state path, atomic-write and exclusive-claim acceptance checks (TF7)."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from autotester.core.paths import team_component, team_path
from autotester.schema.schedule import ScheduleConfig
from autotester.store import filestore
from autotester.store.team_store import TeamStore


@pytest.mark.parametrize("name", ["..", "../x", "..\\x", "/x", "C:\\x", "C:x",
                                  "CON", "nul", "COM1", "LPT9", "x.", "x ", "x" * 121])
def test_hostile_team_components_preserve_outside_sentinel(tmp_path: Path, name: str) -> None:
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"untouched")
    for slot in (False, True):
        with pytest.raises(ValueError):
            team_component(name, slot=slot)
    with pytest.raises(ValueError):
        team_path("records", name, root=tmp_path / "data")
    assert sentinel.read_bytes() == b"untouched"


def test_team_store_uses_relocated_root_and_competing_claims_are_exclusive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = TeamStore()
    model = ScheduleConfig(timezone="IST")
    store.save("schedules", "demo", "config", model)
    assert store.load("schedules", "demo", "config", ScheduleConfig) == model
    slot = "2026-10-08T12:30:00+05:30"
    with ThreadPoolExecutor(max_workers=8) as pool:
        claimed = list(pool.map(lambda _: store.claim_slot("demo", slot), range(8)))
    assert claimed.count(True) == 1
    assert team_path("slots", "demo", team_component(slot, slot=True)).exists()
    assert team_component(slot, slot=True) != team_component(slot + "Z", slot=True)


def test_interrupted_team_record_write_keeps_previous_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TeamStore(tmp_path)
    old = ScheduleConfig(timezone="IST")
    store.save("schedules", "demo", "config", old)

    def interrupted(*args) -> None:
        raise KeyboardInterrupt("fixture interruption before atomic replace")

    monkeypatch.setattr(filestore.os, "replace", interrupted)
    with pytest.raises(KeyboardInterrupt):
        store.save("schedules", "demo", "config", ScheduleConfig(timezone="UTC"))
    assert store.load("schedules", "demo", "config", ScheduleConfig) == old
    assert not list(team_path("schedules", "demo", root=tmp_path).glob(".tmp-*"))


def test_team_state_is_excluded_from_git_and_docker() -> None:
    import subprocess

    root = Path(__file__).resolve().parents[1]
    ignored = subprocess.run(["git", "check-ignore", ".work/team/slots/demo/marker"],
                             cwd=root, capture_output=True, text=True)
    assert ignored.returncode == 0
    assert ".work/" in (root / ".dockerignore").read_text(encoding="utf-8").splitlines()


@pytest.mark.skipif(os.name != "nt", reason="real Windows final-path error transition")
def test_windows_parent_creation_during_resolve_keeps_valid_team_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create the real parent between OS calls; never fabricate final-path results."""
    import ntpath

    root = tmp_path.resolve()
    encoded = team_component("2026-10-08T12:30:00+05:30", slot=True)
    candidate = root / ".work" / "team" / "slots" / "demo" / encoded
    original_final = ntpath._getfinalpathname
    original_resolve = Path.resolve
    errors, resolved_candidates = [], []

    def timed_creation(path):
        matches = ntpath.normcase(str(path)) == ntpath.normcase(str(candidate))
        if matches and len(errors) == 2:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        try:
            return original_final(path)
        except OSError as exc:
            if matches:
                errors.append(exc.winerror)
            raise

    def observed_resolve(path, *args, **kwargs):
        result = original_resolve(path, *args, **kwargs)
        if path == candidate:
            resolved_candidates.append(result)
        return result

    assert not candidate.parent.exists()
    monkeypatch.setattr(ntpath, "_getfinalpathname", timed_creation)
    monkeypatch.setattr(Path, "resolve", observed_resolve)
    result, failure = None, None
    try:
        result = team_path("slots", "demo", encoded, root=root)
    except ValueError as exc:
        failure = exc
    assert errors == [3, 3, 2]
    assert candidate.parent.is_dir() and not candidate.exists()
    assert len(resolved_candidates) == 1
    assert str(resolved_candidates[0]).startswith("\\\\?\\")
    assert failure is None, f"valid team path refused after real OS transition: {failure}"
    assert result == candidate


@pytest.mark.skipif(os.name != "nt", reason="synthetic native Windows namespace comparison")
@pytest.mark.parametrize("data,destination", [
    (r"D:\tf7-root", r"\\?\D:\tf7-root\.work\team\records\entry"),
    (r"\\?\D:\tf7-root", r"D:\tf7-root\.work\team\records\entry"),
    (r"D:\TF7-root", r"\\?\d:\tf7-ROOT\.WORK\TEAM\records\entry"),
    (r"\\server\share\tf7-root", r"\\?\UNC\server\share\tf7-root\.work\team\records\entry"),
    (r"\\?\UNC\server\share\tf7-root", r"\\server\share\tf7-root\.work\team\records\entry"),
    (r"\\SERVER\share\tf7-root", r"\\?\unc\server\SHARE\TF7-root\.WORK\team\records\entry"),
    (r"\\?\D:\tf7-root", r"\\?\D:\tf7-root\.work\team\records\entry"),
    (r"D:\tf7-root", r"D:\tf7-root\.work\team\records\entry"),
])
def test_windows_namespace_aliases_compare_without_rewriting_returned_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: str, destination: str,
) -> None:
    """Synthetic resolve results isolate comparison; no drive/share I/O occurs."""
    root = Path(data)
    base = root / ".work" / "team"
    candidate = base / "records" / "entry"
    values = iter([root, base, root, Path(destination)])
    calls = []
    sentinel = tmp_path / "outside"
    sentinel.write_bytes(b"untouched")

    def synthetic_resolve(path, *args, **kwargs):
        calls.append(path)
        return next(values)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "resolve", synthetic_resolve)
        result = team_path("records", "entry", root=root)
    assert calls == [root, root / ".work" / "team", root, candidate]
    assert str(result) == str(candidate)
    assert sentinel.read_bytes() == b"untouched"


@pytest.mark.skipif(os.name != "nt", reason="synthetic native Windows namespace comparison")
@pytest.mark.parametrize("invalid", [
    r"E:\tf7-root\.work\team\records\entry",
    r"D:\outside\records\entry",
    r"D:\tf7-root\.work\teammate\records\entry",
    r"\\other\share\tf7-root\.work\team\records\entry",
    r"\\server\other\tf7-root\.work\team\records\entry",
    r"\\?\GLOBALROOT\Device\HarddiskVolume1\entry",
    r"\\?\Volume{00000000-0000-0000-0000-000000000000}\entry",
    r"\\.\D:\tf7-root\.work\team\records\entry",
    r"\\?\D:relative",
    r"D:relative",
    r"\relative",
    r"\\?\UNC\server",
    r"\\server",
    r"\\?\UNC\server\..\entry",
    r"\\?\UNC\?\share\entry",
    r"\\?\UNC\.\share\entry",
])
@pytest.mark.parametrize("operand", ["resolved", "boundary"])
def test_windows_invalid_or_outside_namespaces_refuse_without_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str, operand: str,
) -> None:
    """Refuse invalid anchors on either operand and real outside comparison targets."""
    root = Path(invalid if operand == "boundary" else r"D:\tf7-root")
    base = root / ".work" / "team"
    destination = Path(invalid) if operand == "resolved" else Path(
        r"D:\tf7-root\.work\team\records\entry")
    values = iter([root, base, root, destination])
    sentinel = tmp_path / "outside"
    sentinel.write_bytes(b"untouched")
    with monkeypatch.context() as patch:
        patch.setattr(Path, "resolve", lambda *args, **kwargs: next(values))
        with pytest.raises(ValueError, match="team path escapes the data root"):
            team_path("records", "entry", root=root)
    assert sentinel.read_bytes() == b"untouched"


@pytest.mark.skipif(os.name != "nt", reason="synthetic native Windows namespace comparison")
@pytest.mark.parametrize("invalid", [
    r"\\?\GLOBALROOT\Device\HarddiskVolume1\entry",
    r"\\?\Volume{00000000-0000-0000-0000-000000000000}\entry",
    r"\\.\D:\tf7-root",
    r"\\?\D:relative",
    r"D:relative",
    r"\relative",
    r"\\?\UNC\server\..\entry",
    r"\\?\UNC\?\share\entry",
    r"\\?\UNC\.\share\entry",
])
def test_matching_invalid_windows_anchors_still_refuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str,
) -> None:
    """Matching lexical invalid paths must not make an unsupported namespace safe."""
    root = Path(invalid)
    base = root / ".work" / "team"
    candidate = base / "records" / "entry"
    values = iter([root, base, root, candidate])
    sentinel = tmp_path / "outside"
    sentinel.write_bytes(b"untouched")
    with monkeypatch.context() as patch:
        patch.setattr(Path, "resolve", lambda *args, **kwargs: next(values))
        with pytest.raises(ValueError, match="team path escapes the data root"):
            team_path("records", "entry", root=root)
    assert sentinel.read_bytes() == b"untouched"


@pytest.mark.parametrize("location", ["team", "descendant"])
def test_team_path_refuses_real_symlink_escape(
    tmp_path: Path, location: str,
) -> None:
    """A resolved team-directory link cannot authorize itself as the boundary."""
    import errno

    root, outside = tmp_path / "data", tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "entry"
    sentinel.write_bytes(b"untouched")
    team = root / ".work" / "team"
    link = team if location == "team" else team / "records"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in {
            errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP,
        }:
            pytest.skip("platform cannot create the real directory symlink")
        raise
    assert link.is_symlink()
    with pytest.raises(ValueError, match="team path escapes the data root"):
        team_path(*(("entry",) if location == "team" else ("records", "entry")), root=root)
    assert sentinel.read_bytes() == b"untouched"
    assert list(outside.iterdir()) == [sentinel]
