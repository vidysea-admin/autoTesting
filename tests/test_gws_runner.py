"""The real subprocess runner (team-intake.md TI7, hosting.md HO33), driven by a stand-in program.

No `gws` is ever started: the "binary" is this interpreter running a tiny script that behaves the
way `gws` could (writes the `-o` file, hangs, grows without end, fails with a message). That
exercises the real Popen, the size watch and the timeout without a network or a credential.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import pytest

from autotester.sources.bounded_write import LimitExceeded
from autotester.sources.drive_errors import DriveError, DriveFailure
from autotester.sources.gws_runner import SubprocessGwsRunner, resolve_gws_command

SCRIPT = """
import json, sys, time
mode, args = sys.argv[1], sys.argv[2:]
out = args[args.index("-o") + 1] if "-o" in args else None
if mode == "echo":
    print(json.dumps(sys.argv[1:]))
elif mode == "ok":
    open(out, "wb").write(b"v" * 100)
elif mode == "endless":
    with open(out, "wb") as handle:
        while True:
            handle.write(b"z" * 65536); handle.flush(); time.sleep(0.005)
elif mode == "hang":
    time.sleep(60)
elif mode == "fail":
    sys.stderr.write("secret CANARY-123 in the error body"); sys.exit(1)
"""


@pytest.fixture
def runner(tmp_path):
    script = tmp_path / "fake_gws.py"
    script.write_text(SCRIPT, encoding="utf-8")
    return SubprocessGwsRunner([sys.executable, str(script)], poll_s=0.02)


def test_the_command_is_an_argument_list_and_shell_metacharacters_stay_inert(runner):
    """An id or query with `& | < > ^ %` is just text: nothing is interpreted by a shell."""
    nasty = ["echo", "a&b", "c|d", "<e>", "^f%", "'x' in parents", '{"q":"1"}']
    result = runner.run(nasty, cwd=None, timeout_s=30)
    assert result.returncode == 0 and json.loads(result.stdout) == nasty


def test_run_passes_a_list_and_never_shell_true(monkeypatch, runner):
    seen = {}

    def fake_run(argv, **kwargs):
        seen.update(argv=argv, **kwargs)
        return subprocess.CompletedProcess(argv, 0, "{}", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner.run(["a"], cwd=None, timeout_s=5)
    assert isinstance(seen["argv"], list) and seen["shell"] is False and seen["timeout"] == 5


def test_download_returns_when_the_process_finishes(runner, tmp_path):
    work = tmp_path / "w"
    result = runner.download(["ok", "-o", "f.part"], cwd=work, out_name="f.part",
                             max_bytes=10_000, timeout_s=30)
    assert result.returncode == 0 and (work / "f.part").stat().st_size == 100


def test_ti9_download_that_grows_without_end_is_killed_and_removed(runner, tmp_path):
    """An endless body cannot hold a worker: it ends shortly after the limit and nothing is kept."""
    work, limit = tmp_path / "w", 200_000
    start = time.monotonic()
    with pytest.raises(LimitExceeded):
        runner.download(["endless", "-o", "f.part"], cwd=work, out_name="f.part",
                        max_bytes=limit, timeout_s=60)
    assert time.monotonic() - start < 20
    assert not (work / "f.part").exists()


def test_ho33_a_download_that_hangs_ends_at_the_total_timeout(runner, tmp_path):
    start = time.monotonic()
    with pytest.raises(DriveError) as caught:
        runner.download(["hang"], cwd=tmp_path / "w", out_name="f.part", max_bytes=1000,
                        timeout_s=0.5)
    assert caught.value.kind is DriveFailure.NETWORK_ERROR
    assert time.monotonic() - start < 15


def test_ho33_a_metadata_call_that_hangs_ends_at_the_timeout(runner):
    with pytest.raises(DriveError) as caught:
        runner.run(["hang"], cwd=None, timeout_s=0.5)
    assert caught.value.kind is DriveFailure.NETWORK_ERROR


def test_a_failing_process_hands_its_text_to_the_caller_to_classify(runner, tmp_path):
    result = runner.download(["fail", "-o", "f.part"], cwd=tmp_path / "w", out_name="f.part",
                             max_bytes=1000, timeout_s=30)
    assert result.returncode == 1 and "CANARY-123" in result.stderr


def test_a_missing_binary_is_the_gws_missing_message(tmp_path):
    missing = SubprocessGwsRunner(["definitely-not-a-real-binary-xyz"])
    with pytest.raises(DriveError) as caught:
        missing.run(["x"], cwd=None, timeout_s=5)
    assert caught.value.kind is DriveFailure.GWS_MISSING
    with pytest.raises(DriveError):
        missing.download(["x"], cwd=tmp_path / "w", out_name="f", max_bytes=1, timeout_s=5)


def test_a_cmd_shim_is_resolved_to_the_real_exe_never_run_through_cmd(tmp_path):
    shim = tmp_path / "gws.cmd"
    shim.write_text("@echo off", encoding="utf-8")
    with pytest.raises(DriveError):  # no exe beside the shim: refuse, do not run the shim
        resolve_gws_command(which=lambda _n: str(shim), env={})
    exe = tmp_path / "node_modules" / "@googleworkspace" / "cli" / "bin" / "gws.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"MZ")
    assert resolve_gws_command(which=lambda _n: str(shim), env={}) == [str(exe)]


def test_no_gws_on_the_path_is_the_gws_missing_message():
    with pytest.raises(DriveError) as caught:
        resolve_gws_command(which=lambda _n: None, env={})
    assert caught.value.kind is DriveFailure.GWS_MISSING
