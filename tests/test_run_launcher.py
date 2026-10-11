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


def _calls(name_in: set[str]) -> list[str]:
    hits = []
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else "")
            if called in name_in:
                hits.append(f"{path.relative_to(SRC).as_posix()}:{node.lineno}")
    return hits


def test_exactly_one_non_test_call_site_builds_a_run() -> None:
    sites = _calls({"Run"})
    assert [s.split(":")[0] for s in sites] == ["stages/run_launcher.py"], sites


def test_exactly_one_non_test_call_site_executes_the_cases() -> None:
    sites = _calls(EXECUTORS)
    assert [s.split(":")[0] for s in sites] == ["stages/run_launcher.py"], sites


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
