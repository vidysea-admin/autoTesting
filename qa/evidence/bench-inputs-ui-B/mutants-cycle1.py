import json, os, shutil, subprocess, sys, time
from pathlib import Path
BASE = Path(r"D:\autoTesting\.work\tmp\bi-chkB2\mut\base")
PY = r"D:\autoTesting\.worktrees\bench-inputs-ui\.venv\Scripts\python.exe"
env = dict(os.environ, TMP=r"D:\autoTesting\.work\tmp", TEMP=r"D:\autoTesting\.work\tmp")
T_MARK = ["tests/test_bench_marks.py::test_simultaneous_set_mark_calls_lose_no_ruling",
          "tests/test_ui_bench_inputs.py::test_c1_simultaneous_marks_over_http_all_stored_and_none_errors"]
T_UP_LOCK = ["tests/test_bench_inputs_stage.py::test_simultaneous_uploads_leave_the_list_matching_its_pin_and_record_every_hash"]
T_UP_HTTP = ["tests/test_ui_bench_inputs.py::test_c2_an_oversize_list_is_refused_413_without_the_body_being_spooled"]
T_CAP = ["tests/test_bench_inputs_stage.py::test_a_list_of_exactly_the_cap_is_accepted_and_one_byte_more_is_refused"]
MUTS = [
 ("control", None, None, T_MARK + T_UP_LOCK + T_UP_HTTP + T_CAP),
 ("M1-C1 set_mark lock -> nullcontext", "src/autotester/stages/bench_marks.py",
  ('with file_lock(path.with_name(path.name + ".lock"), timeout_s=30.0, what="bench marks"):', 'with __import__("contextlib").nullcontext():'), T_MARK),
 ("M2-C2 atomic-list lock -> nullcontext", "src/autotester/stages/bench_inputs.py",
  ('with file_lock(folder / "atomic-list.lock", timeout_s=30.0, what="atomic list"):', 'with __import__("contextlib").nullcontext():'), T_UP_LOCK),
 ("M3-C2 .json name check removed", "src/autotester/ui/routes_bench_inputs.py",
  ('    if not filename.replace', '    return False\n    if not filename.replace'), T_UP_HTTP),
 ("M4-C2 route stream cap x100", "src/autotester/ui/routes_bench_inputs.py",
  ('stream_upload(request, staging, bench_inputs.MAX_BYTES, _vet_json)', 'stream_upload(request, staging, bench_inputs.MAX_BYTES * 100, _vet_json)'), T_UP_HTTP),
 ("M5-C2 stage size check `>` -> `>=`", "src/autotester/stages/bench_inputs.py", None, T_CAP),
]
res = []
for i, (name, rel, rep, tests) in enumerate(MUTS):
    d = BASE.parent / f"m{i}"
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(BASE, d)
    if rel:
        p = d / rel; s = p.read_text(encoding="utf-8")
        if rep is None:
            import re
            assert "> MAX_BYTES" in s, "pattern"
            s2 = s.replace("> MAX_BYTES", ">= MAX_BYTES", 1)
        else:
            assert rep[0] in s, (name, "pattern absent")
            s2 = s.replace(rep[0], rep[1], 1)
        assert s2 != s; p.write_text(s2, encoding="utf-8")
    e = dict(env, PYTHONPATH=str(d / "src"))
    t = time.time()
    r = subprocess.run([PY, "-m", "pytest", *tests, "-p", "no:cacheprovider", "--no-header"], cwd=d, env=e, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l][-1:]
    res.append({"mutant": name, "rc": r.returncode, "summary": tail, "secs": round(time.time() - t, 1)})
    print(res[-1], flush=True)
json.dump(res, open(r"D:\autoTesting\.worktrees\bench-inputs-ui\qa\evidence\bench-inputs-ui-B\mutants-cycle1.json", "w"), indent=1)
