"""Falsification rows in throwaway copies on C:. green before, red after."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SP = Path(__file__).parent.parent
W = SP / "r2b-copy"
PY = str(W / ".venv" / "Scripts" / "python.exe")
FZ = SP / "r2b-fz"
EX = "tests/test_cli_video_review_exits.py"
VP = "tests/test_video_pointers.py"

ROWS = [
    ("F2a click usage errors", "src/autotester/cli_video.py",
     'app.command("review", cls=ReviewCommand)(review_cmd)', 'app.command("review")(review_cmd)',
     [EX, "-k", "usage_error or missing_source or equals_form or without_json"]),
    ("F2b unexpected exception", "src/autotester/cli_video_review.py",
     "    except Exception as exc:\n        reason = _failure_reason",
     "    except ZeroDivisionError as exc:\n        reason = _failure_reason",
     [EX, "-k", "unexpected_provider_exception"]),
    ("F2c Ctrl-C", "src/autotester/cli_video_review.py",
     "    except KeyboardInterrupt:\n        fail = CliFail(",
     "    except ZeroDivisionError:\n        fail = CliFail(",
     [EX, "-k", "ctrl_c"]),
    ("F2d exit_code on review doc", "src/autotester/cli_video_review.py",
     '_doc({**review.model_dump(mode="json"), "exit_code": code})',
     '_doc(review.model_dump(mode="json"))',
     [EX, "-k", "carries_the_real_exit_code or envelope"]),
    ("F2d exit_code on plan doc", "src/autotester/cli_video_review.py",
     '_doc({**plan.model_dump(mode="json"), "exit_code": 0})',
     '_doc(plan.model_dump(mode="json"))',
     [EX, "-k", "carries_the_real_exit_code"]),
    ("F3 32769 boundary (>= variant)", "src/autotester/stages/video_pointers.py",
     "    if size > MAX_POINTER_FILE_BYTES:", "    if size >= MAX_POINTER_FILE_BYTES:",
     [VP, "-k", "exactly_32768"]),
    ("F3 32769 boundary (+1 variant)", "src/autotester/stages/video_pointers.py",
     "    if size > MAX_POINTER_FILE_BYTES:", "    if size > MAX_POINTER_FILE_BYTES + 1:",
     [VP, "-k", "exactly_32768"]),
]


def pytest(copy, args):
    env = dict(os.environ, PYTHONPATH=str(copy / "src") + os.pathsep + str(copy / "tests"))
    env.pop("VIRTUAL_ENV", None)
    p = subprocess.run([PY, "-m", "pytest", *args, "-p", "no:cacheprovider"], cwd=copy, env=env,
                       capture_output=True, text=True, timeout=500)
    tail = [ln for ln in p.stdout.splitlines() if ln.strip()][-1:] or ["(no output)"]
    return p.returncode, tail[0], p.stdout


def main():
    if FZ.exists():
        shutil.rmtree(FZ)
    FZ.mkdir()
    res = []
    for i, (name, rel, old, new, args) in enumerate(ROWS):
        copy = FZ / f"row{i}"
        copy.mkdir()
        for d in ("src", "tests", "scripts"):
            shutil.copytree(W / d, copy / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy(W / "pyproject.toml", copy / "pyproject.toml")
        env = dict(os.environ, PYTHONPATH=str(copy / "src"))
        env.pop("VIRTUAL_ENV", None)
        where = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"],
                               env=env, capture_output=True, text=True).stdout.strip()
        rc0, t0, _ = pytest(copy, args)
        f = copy / rel
        src = f.read_text(encoding="utf-8")
        assert src.count(old) == 1, (name, src.count(old))
        f.write_text(src.replace(old, new), encoding="utf-8")
        rc1, t1, out1 = pytest(copy, args)
        failed = [ln for ln in out1.splitlines() if ln.startswith("FAILED")][:3]
        row = dict(row=name, anchor_file=rel, autotester_file=where, green_rc=rc0, green=t0,
                   red_rc=rc1, red=t1, failed_tests=failed)
        res.append(row)
        print(json.dumps(row), flush=True)
        shutil.rmtree(copy)
    Path(SP / "r2b-out").mkdir(exist_ok=True)
    (SP / "r2b-out" / "falsification.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
