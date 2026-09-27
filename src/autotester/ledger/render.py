"""Derive the living docs from code and the ledger. Nothing here is hand-typed.

`render_map` fills the generated sections of ARCHITECTURE.md (directory map from module docstrings,
schema summary from the models). `render_snapshot` writes the lean session-start digest. `doctor`
regenerates both and fails on any diff. Also holds `soft_import_ids`, the AST classifier doctor's
dependency check uses to tell a genuinely optional import from a required one dressed up as one
(AT-590/AT-619; see the "optional-import detection" section below for why it lives in this file).
"""

from __future__ import annotations

import ast
import re
from datetime import timedelta
from pathlib import Path

from autotester.core.paths import RepoDocs
from autotester.ledger.store import latest_by_feature, live, load_events, load_goal_tasks
from autotester.schema.enums import FeatureEventKind, UserValue

SNAPSHOT_MAX_LINES = 60
ARCHITECTURE_MAX_LINES = 150
HIGH_FEATURES_SHOWN = 8
RECENT_DAYS = 30
_HEADER_RE = re.compile(r"^## (D-\d+) \| (\d{4}-\d{2}-\d{2}) \| type: (\w+) \| status: (\w+)")
_SUPERSEDES_RE = re.compile(r"^\*\*Supersedes:\*\*\s*(.+?)\s--\s")
_ROUTER_PATH_RE = re.compile(r"`(docs/[\w./-]+)`")


# -- generated sections -----------------------------------------------------

def marker(name: str) -> tuple[str, str]:
    return f"<!-- generated:{name} -->", f"<!-- /generated:{name} -->"


def replace_generated(text: str, name: str, body: str) -> str:
    """Swap the body between `name`'s markers. Markers must already exist."""
    start, end = marker(name)
    if start not in text or end not in text:
        raise ValueError(f"markers for generated section '{name}' not found")
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{start}\n{body.rstrip()}\n{end}{tail}"


def _first_docstring_line(path: Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    except SyntaxError:
        return "(unparseable)"
    return doc.strip().splitlines()[0] if doc.strip() else "(no docstring)"


def _class_summaries(path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            doc = (ast.get_docstring(node) or "").strip().splitlines()
            out.append((node.name, doc[0] if doc else ""))
    return out


def _script_one_liner(path: Path) -> str:
    """A script's one-job line: a `.py` docstring, or a `.ps1`'s first `# name -- doc`
    header comment (AT-520: `scripts/` had no equivalent of a module docstring row —
    a file's existence was undiscoverable through any routed doc)."""
    if path.suffix == ".py":
        return _first_docstring_line(path)
    for line in path.read_text(encoding="utf-8").splitlines()[:5]:
        stripped = line.strip()
        if stripped.startswith("#") and "--" in stripped:
            return stripped.lstrip("#").strip()
    return "(no description)"


def render_map(root: Path) -> dict[str, str]:
    """Bodies for the three generated sections: `map`, `schema`, `scripts`."""
    pkg = root / "src" / "autotester"
    rows = ["| Module | One job |", "|---|---|"]
    for path in sorted(pkg.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "__init__.py":
            continue
        rows.append(f"| `{path.relative_to(pkg).as_posix()}` | {_first_docstring_line(path)} |")
    schema_rows = ["| Model | Meaning |", "|---|---|"]
    for path in sorted((pkg / "schema").glob("*.py")):
        if path.name in ("__init__.py", "enums.py"):
            continue
        for name, doc in _class_summaries(path):
            schema_rows.append(f"| `{name}` (`schema/{path.name}`) | {doc} |")
    script_rows = ["| Script | One job |", "|---|---|"]
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        for path in sorted(scripts_dir.iterdir()):
            if path.suffix not in (".py", ".ps1") or "__pycache__" in path.parts:
                continue
            script_rows.append(f"| `scripts/{path.name}` | {_script_one_liner(path)} |")
    return {"map": "\n".join(rows), "schema": "\n".join(schema_rows),
            "scripts": "\n".join(script_rows)}


def apply_map(docs: RepoDocs) -> str:
    """docs/MAP.md with its generated sections refreshed (AT-019: not in ARCHITECTURE)."""
    text = docs.map.read_text(encoding="utf-8")
    for name, body in render_map(docs.root).items():
        text = replace_generated(text, name, body)
    return text


# -- optional-import detection ------------------------------------------------
# Lives here, not in doctor.py, purely for C2's 300-line cap (doctor.py was already
# at 269/300 -- AT-590's fix would not fit). Consumed by doctor's
# check_dependencies_declared, the same lazy-import pattern this module already
# serves for check_generated_fresh/check_architecture_budget/check_docs_routed.

_SOFT_EXCEPT_NAMES = {"ImportError", "ModuleNotFoundError"}
_EXIT_CALL_NAMES = {"exit", "quit"}


def _is_exit_call(call: ast.Call) -> bool:
    """`exit(...)`/`quit(...)`/`sys.exit(...)` -- AT-619's non-raise exit shape."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in _EXIT_CALL_NAMES
    return (isinstance(func, ast.Attribute) and func.attr == "exit"
            and isinstance(func.value, ast.Name) and func.value.id == "sys")


def _handler_exits(body: list[ast.stmt]) -> bool:
    """True if a raise or exit call is reachable on any path through `body`, without
    descending into a nested def/class (AT-619: a handler that re-raises or exits is
    a required-dependency guard, not a graceful degrade)."""
    for stmt in body:
        if isinstance(stmt, ast.Raise):
            return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) \
                and _is_exit_call(stmt.value):
            return True
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(stmt, ast.Try) and (
                any(_handler_exits(h.body) for h in stmt.handlers)
                or _handler_exits(stmt.finalbody)):
            return True
        for field in ("body", "orelse", "finalbody"):
            nested = getattr(stmt, field, None)
            if isinstance(nested, list) and _handler_exits(nested):
                return True
    return False


def soft_import_ids(tree: ast.AST) -> set[int]:
    """id() of every Import/ImportFrom nested inside `if TYPE_CHECKING:` /
    `if typing.TYPE_CHECKING:`, or inside a try whose handlers name ONLY
    ImportError/ModuleNotFoundError AND whose bodies degrade gracefully (AT-590 --
    `except Exception` or a bare `except:` stays hard, since neither proves the
    failure was a missing package; AT-619 -- a handler that re-raises or exits,
    e.g. `except ImportError: raise` or `sys.exit(...)`, stays hard too, since that
    is a required-dependency guard, not an optional one). Each guard's own body is
    walked in isolation, so an `if`'s `else` and any statement after the `try` stay
    hard; anything inside the guard is soft however deeply nested."""
    def is_type_checking(test: ast.expr) -> bool:
        return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")

    def except_names(expr: ast.expr) -> set[str | None]:
        if isinstance(expr, ast.Tuple):
            return {n for e in expr.elts for n in except_names(e)}
        return {expr.id if isinstance(expr, ast.Name) else getattr(expr, "attr", None)}

    def try_is_soft(node: ast.Try) -> bool:
        return bool(node.handlers) and all(
            h.type is not None and except_names(h.type) <= _SOFT_EXCEPT_NAMES
            and not _handler_exits(h.body)
            for h in node.handlers)

    def guarded_body(node: ast.AST) -> list[ast.stmt]:
        if isinstance(node, ast.If) and is_type_checking(node.test):
            return node.body
        if isinstance(node, ast.Try) and try_is_soft(node):
            return node.body
        return []

    soft: set[int] = set()
    for node in ast.walk(tree):
        for stmt in guarded_body(node):
            soft.update(id(sub) for sub in ast.walk(stmt)
                       if isinstance(sub, (ast.Import, ast.ImportFrom)))
    return soft


# -- decisions index --------------------------------------------------------

def decision_index(decisions_path: Path) -> list[tuple[str, str, str, str]]:
    """(id, date, type, computed status) for every entry, in file order."""
    if not decisions_path.exists():
        return []
    entries: list[list[str]] = []
    superseded: dict[str, str] = {}
    current: str | None = None
    for line in decisions_path.read_text(encoding="utf-8").splitlines():
        head = _HEADER_RE.match(line)
        if head:
            current = head.group(1)
            entries.append([current, head.group(2), head.group(3), head.group(4)])
            continue
        sup = _SUPERSEDES_RE.match(line)
        if sup and current:
            for target in re.findall(r"D-\d+", sup.group(1)):
                superseded[target] = current
    out = []
    for entry_id, day, kind, status in entries:
        if entry_id in superseded:
            status = f"SUPERSEDED (by {superseded[entry_id]})"
        out.append((entry_id, day, kind, status))
    return out


# -- snapshot ---------------------------------------------------------------

def _product_paragraph(architecture: Path) -> list[str]:
    text = architecture.read_text(encoding="utf-8") if architecture.exists() else ""
    section = text.split("## What it does", 1)[-1].split("\n## ", 1)[0]
    return [line for line in section.strip().splitlines() if line.strip()][:6]


def _feature_lines(docs: RepoDocs) -> list[str]:
    """AT-613: the shown high-value slice is newest-first by id, so a new live feature is kept."""
    events = load_events(docs.features)
    current = live(events)
    lines = ["## Live features"]
    high = [e for e in current if e.user_value is UserValue.HIGH]
    normal = [e for e in current if e.user_value is not UserValue.HIGH]
    shown = sorted(high, key=lambda x: x.id, reverse=True)
    for e in shown[:HIGH_FEATURES_SHOWN]:
        lines.append(f"- {e.id} **{e.title}** [high] — {e.description} · reason: {e.reason}")
    if len(shown) > HIGH_FEATURES_SHOWN:
        extra_high = len(shown) - HIGH_FEATURES_SHOWN
        lines.append(f"- +{extra_high} more high-value features → docs/FEATURES.jsonl")
    if normal:
        names = ", ".join(f"{e.id} {e.title}" for e in sorted(normal, key=lambda x: x.id)[:8])
        extra = f" (+{len(normal) - 8} more)" if len(normal) > 8 else ""
        lines.append(f"- normal: {names}{extra}")
    if not current:
        lines.append("- none live yet")
    lines.append(f"## Changed in the last {RECENT_DAYS} days")
    anchor = max((e.date for e in events), default=None)
    recent = [e for e in events if anchor and e.date >= anchor - timedelta(days=RECENT_DAYS)
              and e.event in (FeatureEventKind.UPDATED, FeatureEventKind.RETIRED)]
    for e in recent[-8:]:
        lines.append(f"- {e.date} {e.event.value} {e.id} {e.title} — {e.reason}")
    if not recent:
        lines.append("- nothing updated or retired")
    retired = [e for e in latest_by_feature(events).values() if e.event is FeatureEventKind.RETIRED]
    if retired:
        lines.append("## Retired (do not rebuild without the gate)")
        lines.extend(f"- {e.id} {e.title} — {e.reason}" for e in retired[:6])
    return lines


def render_snapshot(docs: RepoDocs) -> str:
    """The ≤60-line digest injected at session start. Deterministic for given inputs."""
    lines = [
        "# AutoTester — snapshot (generated by `autotester snapshot`; do not edit)",
        "",
        "**Purpose:** the whole project in one screen — what it is, what is live and why, "
        "what changed, what is next.",
        "**Open me when:** every session start (the hook injects me); before picking a unit. "
        "For detail go to the router in `CLAUDE.md`.",
        "",
        "## Product",
        *_product_paragraph(docs.architecture),
        *_feature_lines(docs),
        "## Next (open goal tasks)",
    ]
    pending = [t for t in load_goal_tasks(docs.goal) if t.get("status") == "pending"][:5]
    lines.extend(f"- {t['id']} [{t.get('user_value', 'normal')}] {t['title']}" for t in pending)
    if not pending:
        lines.append("- backlog empty")
    lines.append("## Last decisions (computed status)")
    for entry_id, day, kind, status in decision_index(docs.decisions)[-5:]:
        lines.append(f"- {entry_id} {day} {kind} {status}")
    text = "\n".join(lines).rstrip() + "\n"
    if text.count("\n") > SNAPSHOT_MAX_LINES:
        raise ValueError(f"snapshot exceeds {SNAPSHOT_MAX_LINES} lines; tighten the roll-ups")
    return text


# -- self-describing docs + router -----------------------------------------

def doc_header_missing(path: Path) -> bool:
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:8])
    return "**Purpose:**" not in head or "**Open me when:**" not in head


def router_paths(router: Path) -> set[str]:
    """Every `docs/...` path the router table names."""
    if not router.exists():
        return set()
    return set(_ROUTER_PATH_RE.findall(router.read_text(encoding="utf-8")))
