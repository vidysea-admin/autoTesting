"""Checker throwaway: one falsification per row, each in its OWN copy of 868e3682 (outside the bound tree).
green-before in the copy, apply ONE hunk, red-after. Usage: python fals.py"""
import os, shutil, subprocess, sys, re
S = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
W = "D:/autoTesting/.worktrees/check-t202-mr-b"
ROWS = [
 ("F1b-LL11-cli-nonlitellm", "src/autotester/cli_orchestrate.py",
  '    if why := providers.why_unavailable(model):\n        typer.secho(f"{why} — `autotester providers` lists the ones that have credentials",\n                    fg=typer.colors.RED)\n        raise typer.Exit(1)\n    return model',
  '    return model',
  "tests/test_expand_cli.py::test_expand_refuses_when_the_named_provider_has_no_credentials"),
]
def run(copy, node):
    env = dict(os.environ); env["PYTHONPATH"] = copy + "/src"; env.pop("HTTP_PROXY", None); env.pop("HTTPS_PROXY", None)
    p = subprocess.run(["uv", "--directory", W, "run", "pytest", "-p", "no:xdist", "-p", "no:cacheprovider", "-o", "addopts=",
                        "--rootdir", copy, "-q", copy + "/" + node], capture_output=True, text=True, env=env)
    out = p.stdout + p.stderr
    tail = [l for l in out.splitlines() if re.search(r"passed|failed|error", l) and "VIRTUAL_ENV" not in l][-3:]
    asserts = [l.strip() for l in out.splitlines() if l.startswith("E ")][:3]
    return p.returncode, tail, asserts
res = []
for name, rel, old, new, node in ROWS:
    copy = f"{S}/fals-{name}"
    if os.path.exists(copy): shutil.rmtree(copy)
    shutil.copytree(f"{S}/copy-base", copy, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    g = run(copy, node)
    path = f"{copy}/{rel}"
    src = open(path, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in src else "\n"
    o = old.replace("\n", nl); n = new.replace("\n", nl)
    assert src.count(o) == 1, f"{name}: hunk not found exactly once"
    open(path, "w", encoding="utf-8", newline="").write(src.replace(o, n))
    r = run(copy, node)
    line = f"{name}: GREEN-before rc={g[0]} {g[1]} | RED-after rc={r[0]} {r[1]} {r[2]}"
    print(line, flush=True); res.append(line)
    shutil.rmtree(copy)
print("copies deleted")
