"""Run the `gws` CLI as a subprocess: an argument list, a timeout, a size watch, no shell.

Contract: team-intake.md TI7/TI8, hosting.md HO33; qa/gates/drive-identity.md (D-081): the live
fetch uses the existing `gws` CLI login and no token is copied into this repo. This module never
reads, prints or stores a credential: it passes the process's own environment through and returns
what the process printed to the caller, which classifies and drops it (`drive_errors`).

* The command is an argument LIST (never a shell string). On Windows the npm shim `gws.cmd`
  would go through `cmd.exe`, so it is resolved to the real `gws.exe` beside it; if that is not
  found the runner refuses rather than run the shim.
* `download` watches the output file while `gws` writes it and kills the process the moment the
  file passes `max_bytes` (`LimitExceeded`), or the total timeout runs out. `gws -o` only
  writes under its working directory, so the caller gives it a private folder.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple, Protocol

from autotester.sources.bounded_write import LimitExceeded
from autotester.sources.drive_errors import DriveError, DriveFailure

GWS_BIN_ENV = "AUTOTESTER_GWS_BIN"
_SHIM_SUFFIXES = {".cmd", ".bat", ".ps1"}
_SHIM_EXE = Path("node_modules") / "@googleworkspace" / "cli" / "bin" / "gws.exe"


class GwsResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str


class GwsRunner(Protocol):
    """The injectable seam over the process; a scripted fake implements it in tests."""

    def run(self, args: Sequence[str], *, cwd: Path | None, timeout_s: float) -> GwsResult: ...

    def download(self, args: Sequence[str], *, cwd: Path, out_name: str, max_bytes: int,
                 timeout_s: float) -> GwsResult: ...


def resolve_gws_command(which=shutil.which, env=os.environ) -> list[str]:
    """The `gws` executable as an argument list, or `DriveError(GWS_MISSING)`."""
    named = env.get(GWS_BIN_ENV) or which("gws")
    if not named:
        raise DriveError(DriveFailure.GWS_MISSING)
    path = Path(named)
    if path.suffix.lower() in _SHIM_SUFFIXES or (os.name == "nt" and path.suffix == ""):
        real = path.parent / _SHIM_EXE
        if not real.is_file():
            raise DriveError(DriveFailure.GWS_MISSING)
        path = real
    return [str(path)]


def _remove(path: Path, tries: int = 50) -> None:
    """Delete a file a just-killed process may still hold for a moment (Windows)."""
    for _ in range(tries):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            time.sleep(0.1)
    path.unlink(missing_ok=True)


class SubprocessGwsRunner:
    """The real runner. `command` overrides the executable (tests point it at a Python script)."""

    def __init__(self, command: Sequence[str] | None = None, *, poll_s: float = 0.1) -> None:
        self._command = list(command) if command is not None else None
        self._poll_s = poll_s

    def _argv(self, args: Sequence[str]) -> list[str]:
        return [*(self._command or resolve_gws_command()), *args]

    def run(self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: float = 60.0
            ) -> GwsResult:
        try:
            done = subprocess.run(
                self._argv(args), cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout_s, stdin=subprocess.DEVNULL, shell=False)
        except subprocess.TimeoutExpired:
            raise DriveError(DriveFailure.NETWORK_ERROR) from None
        except OSError:
            raise DriveError(DriveFailure.GWS_MISSING) from None
        return GwsResult(done.returncode, done.stdout, done.stderr)

    def download(self, args: Sequence[str], *, cwd: Path, out_name: str, max_bytes: int,
                 timeout_s: float = 3600.0) -> GwsResult:
        cwd.mkdir(parents=True, exist_ok=True)
        out_path = cwd / out_name
        deadline = time.monotonic() + timeout_s
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                proc = subprocess.Popen(
                    self._argv(args), cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                    shell=False)
            except OSError:
                raise DriveError(DriveFailure.GWS_MISSING) from None
            try:
                self._watch(proc, out_path, max_bytes, deadline)
            except BaseException:
                proc.kill()
                proc.wait()
                _remove(out_path)
                raise
            out.seek(0), err.seek(0)
            return GwsResult(proc.returncode, out.read().decode("utf-8", "replace"),
                             err.read().decode("utf-8", "replace"))

    def _watch(self, proc: subprocess.Popen, out_path: Path, max_bytes: int,
               deadline: float) -> None:
        while proc.poll() is None:
            written = out_path.stat().st_size if out_path.exists() else 0
            if written > max_bytes:
                raise LimitExceeded(max_bytes, written)
            if time.monotonic() > deadline:
                raise DriveError(DriveFailure.NETWORK_ERROR)
            time.sleep(self._poll_s)
