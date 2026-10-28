"""ephemeral-storage-warning: the detector, the admin banner and the entrypoint log line.

The detector must never stop the service: every unknown answers "no warning", never an error.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from autotester.core import env
from autotester.ui import admin_view

ROOT = Path(__file__).resolve().parents[1]
HOSTED, OK = "AUTOTESTER_HOSTED", env.EPHEMERAL_OK_ENV


def mounts_file(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "mounts"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


ROOTFS = "overlay / overlay rw 0 0"


def test_same_device_as_root_filesystem_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "_device", lambda p: 7)
    msg = env.storage_warning(tmp_path, mounts_file(tmp_path, ROOTFS))
    assert msg == (f"Storage is not persistent: accounts and projects are lost on every "
                   f"deploy. Mount a volume at {tmp_path}.")


def test_mounted_root_is_quiet(tmp_path, monkeypatch):
    devices = {str(tmp_path): 9}
    monkeypatch.setattr(env, "_device", lambda p: devices.get(str(p), 7))
    mounts = mounts_file(tmp_path, ROOTFS, f"gcsfuse {tmp_path.as_posix()} fuse rw 0 0")
    assert env.storage_warning(tmp_path, mounts) is None


def test_ancestor_mount_counts(tmp_path, monkeypatch):
    root = tmp_path / "data" / "at"
    root.mkdir(parents=True)
    devices = {str(root): 9}
    monkeypatch.setattr(env, "_device", lambda p: devices.get(str(p), 7))
    mounts = mounts_file(tmp_path, ROOTFS, f"gcsfuse {(tmp_path / 'data').as_posix()} fuse rw 0 0")
    assert env.storage_warning(root, mounts) is None


def test_not_listed_in_mounts_warns_even_on_another_device(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "_device", lambda p: 9 if p == tmp_path else 7)
    assert env.storage_warning(tmp_path, mounts_file(tmp_path, ROOTFS))


def test_memory_backed_mount_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "_device", lambda p: 9 if p == tmp_path else 7)
    mounts = mounts_file(tmp_path, ROOTFS, f"tmpfs {tmp_path.as_posix()} tmpfs rw 0 0")
    assert env.storage_warning(tmp_path, mounts)


def test_opt_out_env_is_quiet(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "_device", lambda p: 7)
    monkeypatch.setenv(OK, "1")
    assert env.storage_warning(tmp_path, mounts_file(tmp_path, ROOTFS)) is None


MAKERS = [lambda p: p / "absent", lambda p: mounts_file(p, "\x00\xff garbage")]


@pytest.mark.parametrize("make", MAKERS)
def test_unknowable_never_raises(tmp_path, monkeypatch, make):
    monkeypatch.setattr(env, "_device", lambda p: 7)
    assert env.storage_warning(tmp_path, make(tmp_path)) is None


def test_device_error_never_raises(tmp_path, monkeypatch):
    def boom(_p):
        raise PermissionError("x")
    monkeypatch.setattr(env, "_device", boom)
    mounts = mounts_file(tmp_path, ROOTFS, f"gcsfuse {tmp_path.as_posix()} fuse rw 0 0")
    assert env.storage_warning(tmp_path, mounts) is None


def _ephemeral(monkeypatch):
    monkeypatch.setattr(env, "storage_warning", lambda *a, **k: "Storage is not persistent: X")


def test_banner_on_hosted_when_ephemeral(monkeypatch):
    monkeypatch.setenv(HOSTED, "1")
    _ephemeral(monkeypatch)
    assert "Storage is not persistent" in admin_view.users_body([], [])
    assert "Storage is not persistent" in admin_view.groups_body([])


def test_no_banner_when_not_hosted(monkeypatch):
    monkeypatch.delenv(HOSTED, raising=False)
    _ephemeral(monkeypatch)
    assert "Storage is not persistent" not in admin_view.users_body([], [])


def test_no_banner_when_persistent_or_opted_out(monkeypatch):
    monkeypatch.setenv(HOSTED, "1")
    monkeypatch.setattr(env, "storage_warning", lambda *a, **k: None)
    assert "Storage is not persistent" not in admin_view.users_body([], [])


def test_opt_out_env_drops_banner_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv(HOSTED, "1")
    monkeypatch.setenv(OK, "1")
    monkeypatch.setattr(env, "_device", lambda p: 7)
    assert "Storage is not persistent" not in admin_view.users_body([], [])


# --- entrypoint.sh -----------------------------------------------------------------------

BASH = shutil.which("bash")
SCRIPT = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8").replace("\r\n", "\n")


def _function() -> str:
    start = SCRIPT.index("warn_if_ephemeral() {")
    return SCRIPT[start:SCRIPT.index("\n}\n", start) + 3]


def test_entrypoint_syntax_and_function_never_exits():
    assert "warn_if_ephemeral || true" in SCRIPT
    body = _function()
    assert "exit " not in body
    if BASH:
        out = subprocess.run([BASH, "-n"], input=SCRIPT, text=True, capture_output=True)
        assert out.returncode == 0, out.stderr


def _run_fn(tmp_path, mount_line, same_dev, **extra):
    """Run only warn_if_ephemeral with a fake /proc/mounts and a fake `stat` (device of / is 5)."""
    (tmp_path / "mounts").write_text(mount_line + "\n", encoding="utf-8")
    fake_stat = f'stat() {{ [ "$3" = / ] && echo 5 || echo {5 if same_dev else 6}; }}'
    snippet = f"{fake_stat}\n{_function()}\nwarn_if_ephemeral\necho rc=$?"
    env_ = {k: v for k, v in os.environ.items() if k != "AUTOTESTER_EPHEMERAL_OK"}
    env_.update(AUTOTESTER_ROOT=tmp_path.as_posix(),
                AUTOTESTER_MOUNTS_FILE=str(tmp_path / "mounts"))
    env_.update(extra)
    out = subprocess.run([BASH, "-c", snippet], capture_output=True, text=True, env=env_)
    return out.stdout.strip(), out.stderr


@pytest.mark.skipif(BASH is None, reason="bash not available")
def test_entrypoint_warns_on_same_device_and_still_returns_zero(tmp_path):
    out, err = _run_fn(tmp_path, "overlay / overlay rw 0 0", same_dev=True)
    assert out == "rc=0" and "WARNING: storage is not persistent" in err
    assert tmp_path.as_posix() in err


@pytest.mark.skipif(BASH is None, reason="bash not available")
def test_entrypoint_warns_when_root_not_in_mounts(tmp_path):
    out, err = _run_fn(tmp_path, "overlay / overlay rw 0 0", same_dev=False)
    assert out == "rc=0" and "WARNING" in err


@pytest.mark.skipif(BASH is None, reason="bash not available")
def test_entrypoint_quiet_on_mounted_root(tmp_path):
    out, err = _run_fn(tmp_path, f"gcsfuse {tmp_path.as_posix()} fuse rw 0 0", same_dev=False)
    assert out == "rc=0" and "WARNING" not in err


@pytest.mark.skipif(BASH is None, reason="bash not available")
def test_entrypoint_quiet_with_opt_out_and_survives_missing_mounts(tmp_path):
    out, err = _run_fn(tmp_path, "overlay / overlay rw 0 0", same_dev=True,
                       AUTOTESTER_EPHEMERAL_OK="1")
    assert out == "rc=0" and "WARNING" not in err
    out, err = _run_fn(tmp_path, "x", same_dev=True, AUTOTESTER_MOUNTS_FILE=str(tmp_path / "nope"))
    assert out == "rc=0" and "WARNING" not in err
