import os, sys, shutil, subprocess, re, time
from pathlib import Path
W = Path(r"D:/autoTesting/.worktrees/t197-video-pointers")
S = Path(sys.argv[1]); only = sys.argv[2:] 
ROWS = {
 "F1-scratch-finally": ("src/autotester/media/redacted.py",
   "    finally:\n        shutil.rmtree(work_dir, ignore_errors=True)\n\n\nclass RedactedFrames",
   "    finally:\n        pass\n\n\nclass RedactedFrames",
   ["tests/test_video_review_cleanup.py","-k","ctrl_c or provider_error or spend_cap or successful_redacted"]),
 "F1-gitignore": (".gitignore", "projects/*/reviews/\n", "", ["tests/test_video_review_cleanup.py","-k","gitignored"]),
 "P2-cli-cap": ("src/autotester/cli_video_review.py",
   "if not math.isfinite(max_cost) or max_cost < 0:", "if max_cost < 0:",
   ["tests/test_cli_video_review_exits.py","-k","non_finite_or_negative"]),
 "P2-stage-cap": ("src/autotester/stages/video_review.py",
   "    if not math.isfinite(max_cost_usd):\n        raise ReviewRefused", "    if False:\n        raise ReviewRefused",
   ["tests/test_video_review_gates.py","-k","non_finite_spend_cap_is_refused"]),
 "P2-loop-cmp": ("src/autotester/stages/video_review.py",
   "if not cost_of(provider) < max_cost_usd:", "if cost_of(provider) >= max_cost_usd:",
   ["tests/test_video_review_gates.py","-k","batch_loop_itself"]),
 "J1-fail-doc": ("src/autotester/cli_video_review.py",
   "    _say(exc.reason, colour=typer.colors.RED)\n    if as_json:", "    _say(exc.reason, colour=typer.colors.RED)\n    if False:",
   ["tests/test_cli_video_review_exits.py","-k","every_exit_path"]),
 "P5-lines": ("src/autotester/stages/video_pointers.py",
   "if out.non_blank_lines > MAX_POINTER_LINES:", "if False:",
   ["tests/test_cli_video_review_exits.py","tests/test_video_pointers.py","-k","too_many_pointer_lines or size_limits"]),
 "P5-note": ("src/autotester/stages/video_pointers.py",
   "if line is not None and line.text and len(line.text) > MAX_POINTER_NOTE_CHARS:", "if False:",
   ["tests/test_cli_video_review_exits.py","tests/test_video_pointers.py","-k","too_long_a_note or size_limits"]),
 "P5-file": ("src/autotester/stages/video_pointers.py",
   "    if size > MAX_POINTER_FILE_BYTES:\n        return oversize_parse(size)", "    if False:\n        return oversize_parse(size)",
   ["tests/test_video_pointers.py","-k","size_limits"]),
 "TV7-origin": ("src/autotester/media/redacted.py",
   "                verify_blackout(self.origin, windows, work_dir)\n", "                verify_blackout(self.origin, windows, work_dir)\n                self.origin = video\n",
   ["tests/test_video_review_cleanup.py","-k","provider_receives_black"]),
 "TV7-noverify": ("src/autotester/media/redacted.py",
   "                verify_blackout(self.origin, windows, work_dir)\n", "                pass\n",
   ["tests/test_video_review_cleanup.py","tests/test_video_review_redaction.py","tests/test_video_review_gates.py","-k","blackout or constructor or noop or no_op or redact"]),
}
def run(copy, args):
    env = dict(os.environ, PYTHONPATH=str(copy/"src")+os.pathsep+str(copy/"tests"))
    r = subprocess.run(["uv","run","--project",str(W),"pytest","-p","no:xdist","-o","addopts=","--rootdir",str(copy),"-q","-p","no:cacheprovider",*args],
        cwd=str(copy), env=env, capture_output=True, text=True)
    tail = [l for l in (r.stdout+r.stderr).splitlines() if re.search(r"\d+ (passed|failed)|error", l, re.I)]
    return r.returncode, (tail[-1] if tail else "?")
for name,(f,a,b,args) in ROWS.items():
    if only and name not in only: continue
    copy = S/name; shutil.rmtree(copy, ignore_errors=True); copy.mkdir(parents=True)
    for d in ("src","tests","scripts"): shutil.copytree(W/d, copy/d, ignore=shutil.ignore_patterns("__pycache__",".pytest_cache","*.pyc"))
    for fn in ("pyproject.toml",".gitignore","uv.lock"): 
        if (W/fn).exists(): shutil.copy(W/fn, copy/fn)
    subprocess.run(["git","init","-q"],cwd=str(copy))
    chk = subprocess.run(["uv","run","--project",str(W),"python","-c","import autotester;print(autotester.__file__)"],cwd=str(copy),env=dict(os.environ,PYTHONPATH=str(copy/"src")),capture_output=True,text=True).stdout.strip()
    assert str(copy).lower().replace("/","\\") in chk.lower(), chk
    t=time.time(); g = run(copy,args)
    p = copy/f; s = p.read_text(encoding="utf-8"); assert s.count(a)==1, (name, s.count(a)); p.write_text(s.replace(a,b),encoding="utf-8")
    r = run(copy,args)
    print(f"{name:22} green-before: rc={g[0]} {g[1]} | after: rc={r[0]} {r[1]}  ({time.time()-t:.0f}s)", flush=True)
    shutil.rmtree(copy, ignore_errors=True)
