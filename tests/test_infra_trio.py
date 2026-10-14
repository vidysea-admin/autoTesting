"""Infra guards: own-PID-only kills (AT-820) and exit-code-preserving verify pipes (AT-692)."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOST_WIDE = re.compile(r"/IM\s|Stop-Process\s+-Name|\bpkill\b|\bkillall\b|Get-Process\s+(python|uv)",
                       re.IGNORECASE)


def test_no_host_wide_kill_in_shipped_code():
    offenders = []
    for folder, pattern in (("src", "*.py"), ("scripts", "*.py"), ("scripts", "*.ps1"),
                            ("scripts", "*.sh")):
        for path in (ROOT / folder).rglob(pattern):
            text = path.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if HOST_WIDE.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{n}")
    assert offenders == []


def test_kill_tree_targets_only_its_own_pid(monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import mutation_check
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    calls: list[list[str]] = []
    monkeypatch.setattr(mutation_check.subprocess, "run",
                        lambda argv, **kw: calls.append(list(argv)))

    class FakeProc:
        pid = 4242

        def wait(self, timeout=None):
            return 0

    mutation_check.kill_tree(FakeProc(), posix=False)  # type: ignore[arg-type]
    assert calls == [["taskkill", "/F", "/T", "/PID", "4242"]]


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize("code", [0, 3])
def test_verify_gates_keeps_exit_code(tmp_path, code):
    script = (ROOT / "scripts" / "verify_gates.sh").as_posix()
    result = subprocess.run(["bash", script, (tmp_path / "log.txt").as_posix(),
                             "bash", "-c", f"echo out; exit {code}"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == code
    assert f"[verify exit code: {code}]" in result.stdout
