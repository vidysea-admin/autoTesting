"""Falsification runner (checker B): one throwaway copy per item; green before, red after.
usage: falsify.py <label> <venv python> <scratch dir> <outfile>"""
from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import io
from pathlib import Path

label, py, scratch, outfile = sys.argv[1:5]
ITEMS = {
    "F1": dict(
        file="src/autotester/stages/explore_merge.py",
        old="    alias = _rediscovered_ids(spec, nodes)\n",
        new="    alias: dict[str, str] = {}\n",
        tests=["tests/test_explore_flows.py::test_a_rediscovered_screen_is_referenced_by_the_existing_id_and_the_flow_id_is_stable",
               "tests/test_explore_flows_doors.py::test_the_cli_door_points_a_rediscovered_screen_at_the_existing_one",
               "tests/test_explore_flows_doors.py::test_the_ui_door_points_a_rediscovered_screen_at_the_existing_one"]),
    "F2": dict(
        file="src/autotester/ui/routes_learn.py",
        old="    except (ProviderError, ValueError) as exc:\n",
        new="    except ProviderError as exc:\n",
        tests=["tests/test_ui_learn_guard.py::test_a_guard_refusal_is_a_themed_400_with_nothing_written_sent_or_echoed"]),
    "F3": dict(
        file="src/autotester/stages/expand.py",
        old=('        mask_pii(f"{s.order}. {s.action.value} {s.target}" + (f" = {s.value}" if s.value else ""))\n',
             '.replace("{{ORIGINAL_STEPS}}", steps_text)\n'),
        new=('        f"{s.order}. {s.action.value} {s.target}" + (f" = {s.value}" if s.value else "")\n',
             '.replace("{{ORIGINAL_STEPS}}", mask_pii(steps_text))\n'),
        tests=["tests/test_expand_redaction.py::test_a_phone_at_the_end_of_a_step_does_not_swallow_the_next_step_number"]),
}
it = ITEMS[label]
root = Path(scratch) / f"fz-{label}-b3a365a1-r1b"
if root.exists():
    raise SystemExit(f"{root} exists")
root.mkdir(parents=True)
blob = subprocess.run(["git", "-C", "D:/autoTesting", "archive", "b3a365a1"], capture_output=True, check=True).stdout
tarfile.open(fileobj=io.BytesIO(blob)).extractall(root)
env = dict(os.environ, PYTHONPATH=str(root / "src"), AUTOTESTER_ROOT="")
env.pop("AUTOTESTER_ROOT")
log = []


def run(tag):
    chk = subprocess.run([py, "-c", "import autotester,sys;print(autotester.__file__)"], cwd=root, env=env,
                         capture_output=True, text=True)
    r = subprocess.run([py, "-m", "pytest", "-p", "no:xdist", "-o", "addopts=", "-p", "no:cacheprovider",
                        "-q", "--no-header", *it["tests"]], cwd=root, env=env, capture_output=True, text=True)
    tail = "\n".join(r.stdout.strip().splitlines()[-12:])
    log.append(f"## {label} {tag}: exit={r.returncode}\nimport path: {chk.stdout.strip()}\n{tail}\n")
    return r.returncode, r.stdout


green_rc, _ = run("GREEN BEFORE (copy, unmodified)")
path = root / it["file"]
text = path.read_text(encoding="utf-8")
olds, news = (it["old"], it["new"]) if isinstance(it["old"], tuple) else ((it["old"],), (it["new"],))
for o, n in zip(olds, news):
    assert text.count(o) == 1, f"mutation anchor not unique/absent: {o!r}"
    text = text.replace(o, n)
path.write_text(text, encoding="utf-8")
red_rc, red_out = run(f"RED AFTER mutation in {it['file']}")
log.append(f"RESULT {label}: green_before={green_rc == 0} red_after={red_rc != 0} (red exit {red_rc}); "
           f"import error in red output: {'ImportError' in red_out or 'SyntaxError' in red_out}\n")
Path(outfile).write_text("\n".join(log), encoding="utf-8")
print("\n".join(log))
