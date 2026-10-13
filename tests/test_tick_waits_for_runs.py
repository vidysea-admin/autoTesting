"""T-200 walk r3: a tick process must stay alive until the runs it started finish.

A run uses thread pools; once the tick's main thread returns, the interpreter refuses new pool
work ("cannot schedule new futures after interpreter shutdown") and the run ends INCONCLUSIVE.
The tests run a real child interpreter, because the failure only exists at process exit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = """
import sys, time
from concurrent.futures import ThreadPoolExecutor
import autotester.ui.routes_runs as rr

out = sys.argv[2]

def runner(entry):
    time.sleep(1.0)  # the tick's main thread is past its last line by now
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(lambda: 1).result()
        verdict = "ok"
    except RuntimeError as exc:
        verdict = "RuntimeError: " + str(exc)
    open(out, "w").write(verdict)

rr.tick_runner = runner
queue = rr.tick_queue()
queue.submit("demo", trigger="schedule", slot_key="demo:fixed:x")
if sys.argv[1] == "wait":
    rr.wait_for_tick_runs()
"""


def _child(tmp_path: Path, mode: str) -> str:
    out = tmp_path / f"{mode}.txt"
    subprocess.run([sys.executable, "-c", SCRIPT, mode, str(out)], check=True, timeout=60,
                   env={**__import__("os").environ, "AUTOTESTER_ROOT": str(tmp_path)})
    return out.read_text(encoding="utf-8")


def test_without_waiting_the_run_hits_interpreter_shutdown(tmp_path: Path) -> None:
    """The control: this is the defect the walk saw, so the fixture really reproduces it."""
    assert "interpreter shutdown" in _child(tmp_path, "nowait")


def test_waiting_lets_the_run_reach_a_real_result(tmp_path: Path) -> None:
    assert _child(tmp_path, "wait") == "ok"
