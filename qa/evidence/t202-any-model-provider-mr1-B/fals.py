"""Checker throwaway: one falsification per row, each in its OWN copy of 868e3682 (outside the bound tree).
green-before in the copy, apply ONE hunk, red-after. Usage: python fals.py"""
import os, shutil, subprocess, sys, re
S = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
W = "D:/autoTesting/.worktrees/check-t202-mr-b"
ROWS = [
 ("F1-LL11-cli", "src/autotester/cli_orchestrate.py",
  '    if why := providers.why_unavailable(model):\n        typer.secho(f"{why} — `autotester providers` lists the ones that have credentials",\n                    fg=typer.colors.RED)\n        raise typer.Exit(1)\n    return model',
  '    return model',
  "tests/test_provider_factory.py::test_ll11_the_cli_exits_non_zero_with_the_same_one_line_reason"),
 ("F2-LL11-learn", "src/autotester/ui/routes_learn.py",
  "    if why:\n        return _refusal(slug, \"No model provider configured\",",
  "    if False:\n        return _refusal(slug, \"No model provider configured\",",
  "tests/test_provider_factory.py::test_generate_cases_asks_the_factory_for_the_agent_of_this_project"),
 ("F3-LL8-AT790-moved", "src/autotester/providers/litellm_provider.py",
  "        if echoed or any(v in text for v in hidden) or len(text) > 300:",
  "        if False:",
  "tests/test_ui_learn_vendor_echo.py::test_generate_failure_page_does_not_carry_a_vendor_echoed_key"),
 ("F4-LL2-run-seam", "src/autotester/ui/routes_runs.py",
  "    if why := why_unavailable(judge):\n        raise HTTPException(400,",
  "    if False:\n        raise HTTPException(400,",
  "tests/test_provider_factory.py::test_trigger_run_asks_the_factory_for_the_judge_of_this_project"),
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
