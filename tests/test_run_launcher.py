"""TF1 (team-foundation.md): one run launcher; the route is a thin caller of it.

Structural proof over `src/`: exactly one non-test call site builds a `Run` or executes the
cases, the launcher imports no web framework, and `trigger_run` holds no run logic. The UI
behaviour itself (RU1-RU4, AT-044) is held by the existing `tests/test_ui_runs*.py`.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
EXECUTORS = {"_execute_with_trace", "execute_with_trace", "run_cases_traced"}


def _aliases(tree: ast.AST) -> dict[str, str]:
    """Local name -> the name it stands for: `import X as Y`, `from m import X as Y` and
    `Y = X` / `Y = mod.X` (followed to a fixed point, so `Z = Y` resolves too)."""
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom | ast.Import):
            names.update({a.asname: a.name.split(".")[-1] for a in node.names if a.asname})
    assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and isinstance(n.value, ast.Name | ast.Attribute)
               and all(isinstance(t, ast.Name) for t in n.targets)]
    for _ in range(4):                      # a chain of aliases is short; this always ends
        for node in assigns:
            real = _name(node.value, names)
            names.update({t.id: real for t in node.targets if t.id != real})
    return names


def _name(node: ast.AST, aliases: dict[str, str]) -> str:
    """The real name an expression refers to (`go` -> `run_cases_traced`, `mod.X` -> `X`)."""
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    return aliases.get(node.attr, node.attr) if isinstance(node, ast.Attribute) else ""


def _is_partial(node: ast.Call, aliases: dict[str, str]) -> bool:
    return _name(node.func, aliases) == "partial"


def _escapes(node: ast.Call, aliases: dict[str, str], wanted: set[str]) -> bool:
    """True when `node` hands a wanted name to something else to call later: a `partial`
    wrapper, or any call taking it as an argument."""
    args = [*node.args, *(k.value for k in node.keywords)]
    return any(_name(a, aliases) in wanted for a in args)


def _calls(name_in: set[str], *, escaping: bool = False) -> list[str]:
    """Every site in `src/` that calls one of `name_in`, under any alias; with `escaping`
    also every site that passes one on as an argument or assigns it onward (`functools.partial`,
    a wrapper, `go = run_cases_traced`). The sole allowed escape is the test shim
    `_execute_with_trace` in `ui/routes_runs.py` (open ruling 2)."""
    hits = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        aliases = _aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            used = _name(node.func, aliases) in name_in or (
                (escaping or _is_partial(node, aliases)) and _escapes(node, aliases, name_in))
            if used and (rel, _shim_target(tree, node)) not in ALLOWED_ESCAPES:
                hits.append(f"{rel}:{node.lineno}")
    return hits


ALLOWED_ESCAPES = {("ui/routes_runs.py", "_execute_with_trace")}


def _shim_target(tree: ast.AST, call: ast.Call) -> str:
    """The module-level name `call` is assigned to (`X = f(...)`), else an empty string."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and node.value is call and isinstance(
                node.targets[0], ast.Name):
            return node.targets[0].id
    return ""


def test_exactly_one_non_test_call_site_builds_a_run() -> None:
    sites = _calls({"Run"})
    assert [s.split(":")[0] for s in sites] == ["stages/run_launcher.py"], sites


def test_exactly_one_non_test_call_site_executes_the_cases() -> None:
    sites = _calls(EXECUTORS, escaping=True)
    assert [s.split(":")[0] for s in sites] == ["stages/run_launcher.py"], sites


def test_the_scan_sees_aliases_partials_and_wrappers(tmp_path: Path, monkeypatch) -> None:
    """The scan itself is proven on hostile spellings, in a scratch tree used as `SRC`."""
    (tmp_path / "stages").mkdir()
    source = chr(10).join([
        "import functools",
        "from autotester.schema.run import Run as R",
        "from autotester.stages.run_launcher import run_cases_traced as go",
        "again = go",
        "def f():",
        "    R(id='x')",
        "    again()",
        "p = functools.partial(go, 1)",
        "q = wrap(run_cases_traced)",
        "r = functools.partial(R, 1)",
    ])
    (tmp_path / "stages" / "x.py").write_text(source, encoding="utf-8")
    monkeypatch.setitem(globals(), "SRC", tmp_path)
    assert len(_calls({"Run"})) == 2              # R(...) and the partial of R
    assert len(_calls(EXECUTORS)) == 2            # again() and the partial
    assert len(_calls(EXECUTORS, escaping=True)) == 3   # ... and wrap(run_cases_traced)


def test_the_launcher_imports_nothing_from_fastapi() -> None:
    tree = ast.parse((SRC / "stages" / "run_launcher.py").read_text(encoding="utf-8"))
    modules = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    modules |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not [m for m in modules if m.split(".")[0] in {"fastapi", "starlette"}]


def test_trigger_run_is_a_thin_caller() -> None:
    tree = ast.parse((SRC / "ui" / "routes_runs.py").read_text(encoding="utf-8"))
    trigger = next(n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "trigger_run")
    assert trigger.end_lineno - trigger.lineno <= 20
    called = {n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
              for n in ast.walk(trigger) if isinstance(n, ast.Call)}
    assert "prepare_run" in called and not called & (EXECUTORS | {"Run", "save_run"})
