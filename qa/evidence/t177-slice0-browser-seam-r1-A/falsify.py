"""Checker falsification runner: each mutant in its own copy of the archive, green before, red after."""
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys
import time

BASE = r"C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\236a59b4-e0ec-4b2d-b22e-73d3059dd7f6\scratchpad"
SRC = os.path.join(BASE, "at887r1a-copy")
PY = os.path.join(SRC, ".venv", "Scripts", "python.exe")
OUT = r"D:\autoTesting\qa\evidence\at887-crawl-to-flows-r1-A"

MUTANTS = {
    "fz1-X13c-drop-alias-rewrite": (
        "src/autotester/stages/explore_merge.py",
        "proposed = [rewrite_screen_refs(f, alias) for f in flows_from_crawl(",
        "proposed = [f for f in flows_from_crawl(",
        ["tests/test_explore_flows_doors.py", "tests/test_explore_flows.py"]),
    "fz2-X6-narrow-except": (
        "src/autotester/ui/routes_learn.py",
        "except (ProviderError, ValueError) as exc:",
        "except ProviderError as exc:",
        ["tests/test_ui_learn_guard.py"]),
    "fz3-PII2-mask-joined": (
        "src/autotester/stages/expand.py",
        None, None, ["tests/test_expand_redaction.py"]),
    "m4-double-bump": (
        "src/autotester/stages/explore_merge.py",
        '"version": merged.version if bumped else merged.version + 1,',
        '"version": merged.version + 1,',
        ["tests/test_explore_flows.py", "tests/test_explore_flows_doors.py"]),
    "m5-rediscovery-name-cond": (
        "src/autotester/stages/explore_merge.py",
        "if incoming.id not in known and clash is not None and _is_rediscovery(clash, incoming):",
        "if incoming.id not in known and clash is not None and not _is_rediscovery(clash, incoming):",
        ["tests/test_explore_flows_doors.py", "tests/test_explore_flows.py"]),
}


def run(name):
    rel, old, new, tests = MUTANTS[name]
    dst = os.path.join(BASE, "fz", name)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", "tests/test_probe_r1a.py"))
    env = dict(os.environ, PYTHONPATH=os.path.join(dst, "src"), VIRTUAL_ENV="")
    cmd = [PY, "-I", "-m", "pytest", "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=", *tests]
    # -I ignores PYTHONPATH; use -s-less mode: run via runpy path instead
    cmd = [PY, "-m", "pytest", "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=", *tests]
    chk = subprocess.run([PY, "-c", "import autotester;print(autotester.__file__)"], env=env,
                         cwd=dst, capture_output=True, text=True).stdout.strip()
    t0 = time.time()
    green = subprocess.run(cmd, env=env, cwd=dst, capture_output=True, text=True)
    tg = time.time() - t0
    path = os.path.join(dst, rel)
    text = open(path, encoding="utf-8", newline="").read()
    if name == "fz3-PII2-mask-joined":
        a = '''    steps_text = "\\n".join(
        mask_pii(f"{s.order}. {s.action.value} {s.target}" + (f" = {s.value}" if s.value else ""))
        for s in sorted(flow.steps, key=lambda s: s.order)
    )'''
        b = '''    steps_text = mask_pii("\\n".join(
        f"{s.order}. {s.action.value} {s.target}" + (f" = {s.value}" if s.value else "")
        for s in sorted(flow.steps, key=lambda s: s.order)
    ))'''
        text = text.replace("\r\n", "\n")
        assert a in text, "pii anchor missing"
        text = text.replace(a, b)
    else:
        text = text.replace("\r\n", "\n")
        assert old in text, "anchor missing " + name
        assert text.count(old) == 1
        text = text.replace(old, new)
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    t1 = time.time()
    red = subprocess.run(cmd, env=env, cwd=dst, capture_output=True, text=True)
    tr = time.time() - t1
    failed = [ln for ln in red.stdout.splitlines() if ln.startswith("FAILED")]
    res = {
        "name": name, "import_path": chk,
        "green_rc": green.returncode, "green_tail": green.stdout.strip().splitlines()[-1], "green_s": round(tg),
        "red_rc": red.returncode, "red_tail": red.stdout.strip().splitlines()[-1], "red_s": round(tr),
        "failed": [f[:230] for f in failed],
    }
    with open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8") as fh:
        for k, v in res.items():
            fh.write(f"{k}: {v}\n")
    return res


if __name__ == "__main__":
    names = sys.argv[1:] or list(MUTANTS)
    with cf.ThreadPoolExecutor(max_workers=len(names)) as ex:
        for r in ex.map(run, names):
            print(r["name"], "| import:", r["import_path"][-60:], "| GREEN", r["green_rc"], r["green_tail"], f'({r["green_s"]}s)',
                  "| RED", r["red_rc"], r["red_tail"], f'({r["red_s"]}s)')
            for f in r["failed"]:
                print("    ", f)
