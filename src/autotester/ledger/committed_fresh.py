"""L1 committed leg: each generated doc's committed blob must equal a fresh regeneration (AT-697).

`doctor.check_generated_fresh` compares the file on DISK with a fresh render, so a regeneration that
was never committed passes clean while every clone receives the stale blob. This module reads the
blob out of HEAD and compares it, LF-normalised on both sides (git stores LF while a checkout on a
`core.autocrlf=true` machine holds CRLF; without normalising every file would always look stale).
Where no committed object can exist (not its own git repo, or no commit yet) the leg is reported as
`committed-leg-skipped` and named, never as passed.

It also hosts `check_state_bypass` (mongo-store M16), here only because the ledger check modules
are at the 300-line cap and a new module needs a D-122 entry; move it out when one exists.
"""

from __future__ import annotations

import ast
import os
import subprocess
import tomllib
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from autotester.core.paths import RepoDocs
from autotester.doctor import Violation

SKIPPED = "committed-leg-skipped"
STALE = "stale-committed"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None


def _skip_reason(root: Path) -> str | None:
    """Why no committed object can be read for `root`, or None when HEAD is readable."""
    top = _git(root, "rev-parse", "--show-toplevel")
    if top is None or top.returncode != 0:
        return "not a git repository (or git unavailable)"
    if not os.path.samefile(top.stdout.decode("utf-8", "replace").strip(), root):
        return "root is not its own git repository"
    head = _git(root, "rev-parse", "--verify", "-q", "HEAD")
    if head is None or head.returncode != 0:
        return "no commit yet"
    return None


def _fresh(docs: RepoDocs, rel: str) -> str | None:
    """The regeneration for `rel`, or None when this artifact does not apply or cannot render."""
    from autotester.ledger.render import apply_map, render_snapshot
    try:
        if rel == "docs/MAP.md":
            return apply_map(docs) if docs.map.exists() else None
        if docs.snapshot.exists() or docs.features.exists():
            return render_snapshot(docs)
    except Exception:  # the disk leg and check_ledger report an unrenderable artifact
        return ""
    return None


def check_committed_generated_fresh(root: Path) -> list[Violation]:
    """Committed MAP.md / SNAPSHOT.md blobs must equal a fresh regeneration (LF-normalised)."""
    docs = RepoDocs(root)
    out: list[Violation] = []
    reason = None
    for rel in ("docs/MAP.md", "docs/SNAPSHOT.md"):
        fresh = _fresh(docs, rel)
        if fresh is None:
            continue
        reason = reason or _skip_reason(root)
        if reason:
            out.append(Violation(SKIPPED, rel, f"committed leg not checked: {reason}"))
        elif not fresh:
            out.append(Violation(SKIPPED, rel, "committed leg not checked: cannot regenerate"))
        else:
            out.extend(_compare(root, rel, fresh))
    return out


def _compare(root: Path, rel: str, fresh: str) -> list[Violation]:
    shown = _git(root, "show", f"HEAD:./{rel}")
    if shown is None or shown.returncode != 0:
        return [Violation(STALE, rel, "committed blob missing: the file is not in HEAD; "
                                      "commit the regenerated file")]
    if shown.stdout.decode("utf-8").replace("\r\n", "\n") != fresh.replace("\r\n", "\n"):
        return [Violation(STALE, rel, "committed blob (HEAD) differs from a fresh regeneration; "
                                      "commit the regenerated file")]
    return []


STATE_BYPASS = "state-bypass"
STATE_BYPASS_STALE = "state-bypass-stale"
_EXEMPT_DIRS = frozenset({"store", "browser"})
_STATE_MODULES = frozenset({  # modules that persist state under a path the CALLER passes in
    "core/trace.py", "stages/orchestrate_checkpoint.py", "auth/audit.py",
    "delivery/inbox.py", "stages/schedule_store.py", "core/env.py"})
_STATE_NAMES = frozenset({"ProjectPaths", "team_path", "paths", "work_dir"})
_STATE_PARTS = frozenset({".work", "projects", ".env"})
_ROOT_NAMES = frozenset({"repo_root", "root", "base"})
_METHODS = frozenset({"write_text", "write_bytes", "unlink", "glob", "rglob", "iterdir", "exists",
                      "stat", "mkdir", "touch", "rename", "rmdir", "symlink_to", "hardlink_to",
                      "open", "replace", "is_file", "is_dir", "read_text", "read_bytes"})
_OS_CALLS = frozenset({"replace", "rename", "link", "open", "remove", "unlink", "makedirs",
                       "mkdir", "rmdir", "removedirs", "listdir", "scandir", "walk", "stat",
                       "symlink", "truncate", "utime", "chmod"})
_OS_PATH = frozenset({"exists", "isfile", "isdir", "lexists", "getsize", "getmtime"})
_FS_MODULES = frozenset({"os", "shutil"})
_FuncDef = (ast.FunctionDef, ast.AsyncFunctionDef)


def _names(expr: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(expr) if isinstance(n, ast.Attribute)}


class _Taint:
    """Names bound to a state path, to the data root, and functions returning a state path."""

    def __init__(self, tree: ast.AST) -> None:
        self.tainted: set[str] = set()
        self.roots: set[str] = set()
        self.funcs: set[str] = set()
        pairs = _pairs(tree)
        for _ in range(4):  # a short fixpoint: `a = paths.x` then `b = a / "y"`
            for names, value in pairs:
                if _names(value) & _ROOT_NAMES:
                    self.roots.update(names)
                if self.is_state(value):
                    self.tainted.update(names)
            for fn in ast.walk(tree):
                if isinstance(fn, _FuncDef) and any(
                        r.value is not None and self.is_state(r.value)
                        for r in ast.walk(fn) if isinstance(r, ast.Return)):
                    self.funcs.add(fn.name)

    def is_state(self, expr: ast.AST) -> bool:
        names = _names(expr)
        if names & (_STATE_NAMES | self.tainted) or any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in self.funcs
                for n in ast.walk(expr)):
            return True
        parts = {n.value for n in ast.walk(expr) if isinstance(n, ast.Constant)}
        return bool(parts & _STATE_PARTS) and bool(names & (self.roots | _ROOT_NAMES))


def _bound(target: ast.AST, value: ast.AST) -> list[tuple[list[str], ast.AST]]:
    """`(names, value)` pairs for one binding; `a, b = x, y` pairs element by element."""
    if (isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List))
            and len(target.elts) == len(value.elts)):
        return [p for t, v in zip(target.elts, value.elts, strict=True) for p in _bound(t, v)]
    return [([n.id for n in ast.walk(target) if isinstance(n, ast.Name)], value)]


def _pairs(tree: ast.AST) -> list[tuple[list[str], ast.AST]]:
    """Every binding in the module: assignment, loop and comprehension target, `with ... as`."""
    out: list[tuple[list[str], ast.AST]] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            bindings = [(t, n.value) for t in n.targets]
        elif isinstance(n, ast.AnnAssign) and n.value is not None:
            bindings = [(n.target, n.value)]
        elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)):
            bindings = [(n.target, n.iter)]
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            bindings = [(n.optional_vars, n.context_expr)]
        else:
            continue
        out += [p for t, v in bindings for p in _bound(t, v)]
    return out


def _imports(tree: ast.AST) -> dict[str, str]:
    """Local name -> dotted origin for `os` / `shutil` imports, so an alias cannot hide a call."""
    out: dict[str, str] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                top = a.name.split(".")[0]
                if top in _FS_MODULES:
                    out[a.asname or top] = a.name if a.asname else top
        elif isinstance(n, ast.ImportFrom) and n.module in {*_FS_MODULES, "os.path"}:
            out.update({a.asname or a.name: f"{n.module}.{a.name}" for a in n.names})
    return out


def _dotted(fn: ast.AST, imports: dict[str, str]) -> str | None:
    """`os.path.exists` for a call target spelled through any alias, else None."""
    attrs: list[str] = []
    while isinstance(fn, ast.Attribute):
        attrs.append(fn.attr)
        fn = fn.value
    if not isinstance(fn, ast.Name) or fn.id not in imports:
        return None
    return ".".join([imports[fn.id], *reversed(attrs)])


def _fs_call(canon: str | None) -> bool:
    if canon is None:
        return False
    if canon.startswith("os.path."):
        return canon[len("os.path."):] in _OS_PATH
    head, _, tail = canon.partition(".")
    return bool(tail) and (head == "shutil" or (head == "os" and tail in _OS_CALLS))


def _writes(call: ast.Call, builtin: bool) -> bool:
    """`open()` that writes; a non-literal mode counts as a write, no mode is a read."""
    index = 1 if builtin else 0
    mode = call.args[index] if len(call.args) > index else next(
        (k.value for k in call.keywords if k.arg == "mode"), None)
    if mode is None:
        return False
    if isinstance(mode, ast.Constant):
        return isinstance(mode.value, str) and bool(set(mode.value) & set("wax+"))
    return True


def _method(fn: ast.AST, hit, alias: dict[str, str]) -> str | None:  # type: ignore[no-untyped-def]
    """The `_METHODS` verb a target names on a state path: `p.m`, `getattr(p, "m")`, or an alias."""
    if isinstance(fn, ast.Name):
        return alias.get(fn.id)
    if (isinstance(fn, ast.Call) and isinstance(fn.func, ast.Name) and fn.func.id == "getattr"
            and len(fn.args) > 1 and isinstance(fn.args[1], ast.Constant)):
        obj, attr = fn.args[0], fn.args[1].value
    elif isinstance(fn, ast.Attribute):
        obj, attr = fn.value, fn.attr
    else:
        return None
    return attr if attr in _METHODS and hit(obj) else None


def _kind(call: ast.Call, hit, imports: dict[str, str],  # type: ignore[no-untyped-def]
          alias: dict[str, str]) -> str | None:
    """The raw-filesystem kind of `call` when it acts on a state path, else None."""
    fn = call.func
    canon = _dotted(fn, imports)
    if _fs_call(canon):
        return canon if any(hit(a) for a in call.args) else None
    builtin = isinstance(fn, ast.Name) and fn.id == "open" and bool(call.args) and hit(call.args[0])
    method = "open" if builtin else _method(fn, hit, alias)
    if method == "open":
        return "open" if _writes(call, builtin) else None
    if method == "replace" and (len(call.args) != 1 or call.keywords):
        return None  # `str.replace(old, new)`; `Path.replace(target)` takes one argument
    return method


def _scoped_calls(node: ast.AST, scope: tuple[str, ...] = ()) -> Iterator[tuple[ast.Call, str]]:
    """Every call with the dotted name of the function or class that encloses it."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.Call):
            yield child, ".".join(scope) or "<module>"
        if isinstance(child, (*_FuncDef, ast.ClassDef)):
            yield from _scoped_calls(child, (*scope, child.name))
        else:
            yield from _scoped_calls(child, scope)


def _sites(path: Path, rel: str) -> list[tuple[int, str, str]]:
    """`(line, function, kind)` for each raw call on a state path in the module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    taint, imports = _Taint(tree), _imports(tree)
    hit = (lambda e: True) if rel in _STATE_MODULES else taint.is_state
    alias = {n: m for ns, v in _pairs(tree) if (m := _method(v, hit, {})) for n in ns}
    return sorted((c.lineno, scope, k) for c, scope in _scoped_calls(tree)
                  if (k := _kind(c, hit, imports, alias)) is not None)


def _allowed(root: Path, key: str) -> list[str]:
    """`path:function:kind` of each pyproject `state-bypass.<key>` row; ` | owner` is dropped."""
    table = root / "pyproject.toml"
    data = tomllib.loads(table.read_text(encoding="utf-8")) if table.exists() else {}
    rows = data.get("tool", {}).get("autotester", {}).get("doctor", {}).get("state-bypass", {})
    return [row.split(" | ", 1)[0] for row in rows.get(key, [])]


def check_state_bypass(root: Path) -> list[Violation]:
    """M16: no raw filesystem call on a state path outside `store/` and `browser/`: a path from
    `ProjectPaths`, `team_path`, `work_dir()` or `repo_root()` with `.work`/`projects`, or any path
    in a module that persists state under a caller's path. `baseline` rows are the known remaining
    sites (tagged with the unit that removes them); a row matching no call is reported too."""
    allowed = Counter(_allowed(root, "baseline") + _allowed(root, "permanent"))
    seen: dict[str, list[int]] = {}
    base = root / "src" / "autotester"
    for path in sorted(base.rglob("*.py")):
        rel = path.relative_to(base).as_posix()
        if "__pycache__" in path.parts or rel.split("/")[0] in _EXEMPT_DIRS:
            continue
        for line, scope, kind in _sites(path, rel):
            seen.setdefault(f"{rel}:{scope}:{kind}", []).append(line)
    out = [Violation(STATE_BYPASS, f"{key.partition(':')[0]}:{line}",
                     f"`{key.rpartition(':')[2]}` on a state path: go through "
                     f"store.filestore (mongo-store M16); baseline row `{key}`")
           for key, lines in seen.items() for line in lines[allowed[key]:]]  # beyond the baseline
    out += [Violation(STATE_BYPASS_STALE, key, "baseline/permanent row matches no call; delete it")
            for key, n in sorted(allowed.items()) for _ in range(n - len(seen.get(key, [])))]
    return out
