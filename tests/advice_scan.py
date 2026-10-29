"""Find every command this codebase tells a human to run — a helper, not a test.

Three generations of the same defect live in this file's history, and each fix
was beaten by the same weakness: the collector could not say WHERE it found
what it found.

1. **AT-176** — the first version scanned string *literals*, so it missed the
   one site the class exists for. `stages/media_prep.py` builds its advice as

       f"... run `{PREP_COMMAND} " f"{slug} {source_id}` on the HOST first"

   Backtick in one f-string part, command name in a module constant: two AST
   nodes, no single literal containing both.
2. **AT-178** — it required a backtick, so the un-backticked advice in
   `core/consent.py` was invisible.
3. **AT-206** — the renderer built to close (1) could be **deleted whole** and
   the guard still passed, because `PREP_COMMAND`'s own definition is a plain
   `ast.Constant` that yields `ingest prep` by itself, and results were deduped
   to `(file, command)`. The guard could not tell the composed message apart
   from the constant it is composed from.

So every result now carries its **line**. A rendered site and the constant it
interpolates are different lines, which is what lets a test pin the site the
class exists for instead of its ingredients.

Still static — no import, no execution. What it cannot resolve it reports:
`unresolved_in_source` lists every SCREAMING_CASE interpolation it could not
put a value to, because a hole that reports nothing looks exactly like a clean
scan — which is how all three of the above survived a guard written to catch
them.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

UNRESOLVED = "\x00"
"""Stands in for an interpolation this cannot resolve. Chosen so it can never
appear in a real command name, and so a partially-rendered string is visibly
partial rather than quietly wrong."""

COMMAND = re.compile(r"autotester ((?:[a-z][a-z-]*)(?: [a-z][a-z-]*)*)")
"""`autotester` followed by lowercase words. Not anchored on backticks: the
un-backticked advice at `core/consent.py` was invisible to the version that
required them (AT-178), and a message is no less wrong for lacking quotes."""


class Advice(NamedTuple):
    """One command named in one string, at the line that string starts on."""

    where: Path
    line: int
    command: str


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level `NAME = "literal"` bindings, which is how this codebase
    holds command names (`PREP_COMMAND`) so they live in one place."""
    out: dict[str, str] = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            out[node.targets[0].id] = node.value.value
    return out


def _imported_constants(tree: ast.Module, module: str,
                        known: dict[str, dict[str, str]]) -> dict[str, str]:
    """Constants this file imported by name from elsewhere in the tree.

    AT-192: resolution used to stop at the file boundary, so AT-176's exact
    shape written one `import` away rendered `UNRESOLVED` and the collector
    returned **nothing at all** for it."""
    out: dict[str, str] = {}
    package = module.rsplit(".", 1)[0] if "." in module else ""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        target = node.module or ""
        if node.level:                       # `from .x import Y` / `from . import Y`
            base = package
            for _ in range(node.level - 1):
                base = base.rsplit(".", 1)[0] if "." in base else ""
            target = f"{base}.{target}" if target else base
        for alias in node.names:
            value = known.get(target, {}).get(alias.name)
            if value is not None:
                out[alias.asname or alias.name] = value
    return out


def _render(node: ast.expr, constants: dict[str, str]) -> str:
    """The text this expression will produce, as far as it can be known."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else UNRESOLVED
    if isinstance(node, ast.JoinedStr):
        return "".join(_render(part, constants) for part in node.values)
    if isinstance(node, ast.FormattedValue):
        inner = node.value
        if isinstance(inner, ast.Name) and inner.id in constants:
            return constants[inner.id]
        return UNRESOLVED
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _render(node.left, constants) + _render(node.right, constants)
    return UNRESOLVED


def _is_documentation(tree: ast.Module) -> set[int]:
    """Ids of strings that are an ENTIRE statement.

    Evaluating one does nothing, so the program can never hand it to anyone.
    That covers real docstrings and this codebase's variable-docstring
    convention — including `PREP_COMMAND`'s own, which exists to explain that
    `autotester media prep` is dead and must not be read as advising it.

    AT-193: this matched `ast.Expr(Constant)` only, while the renderer had
    already been taught to read `JoinedStr` and `BinOp` — so a bare f-string or
    joined documentation statement was scanned as live advice.

    Every DESCENDANT is excluded too, not just the statement itself. A
    `JoinedStr` holds its text in child `Constant` nodes, and the walk visits
    those independently — so excluding only the parent left the documentation
    fully visible through its own children, which is the same
    seen-it-somewhere-else miss the line numbers exist to prevent."""
    excluded: set[int] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant | ast.JoinedStr | ast.BinOp)):
            excluded |= {id(child) for child in ast.walk(node.value)}
    return excluded


def _strings(tree: ast.Module, constants: dict[str, str]) -> list[tuple[int, str]]:
    """Every string this module could actually print, with its line."""
    documentation = _is_documentation(tree)
    return [(node.lineno, _render(node, constants))
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant | ast.JoinedStr | ast.BinOp)
            and id(node) not in documentation]


def advice_in(source: str, constants: dict[str, str] | None = None) -> list[tuple[int, str]]:
    """Every `(line, command)` named in a string this module could print."""
    tree = ast.parse(source)
    resolved = {**_module_constants(tree), **(constants or {})}
    found: list[tuple[int, str]] = []
    for line, text in _strings(tree, resolved):
        for match in COMMAND.finditer(text):
            command = match.group(1).strip()
            if command and UNRESOLVED not in command:
                found.append((line, command))
    return found


def unresolved_in(source: str, constants: dict[str, str] | None = None,
                  bound_elsewhere: set[str] | None = None) -> list[int]:
    """Lines interpolating a SCREAMING_CASE name this could not put a value to.

    That casing is how this codebase holds a command name, so an unresolved one
    is exactly the AT-192 hole: `f"run `{PREP_COMMAND} {slug}`"` with the
    constant imported renders no `autotester` at all, so it yields an empty
    list — identical, to any caller, to a file that simply gives no advice.

    Two kinds of name are deliberately NOT reported, because a detector that
    cries at every interpolation gets ignored within a week: `{slug}`-style
    runtime values (not SCREAMING_CASE), and a constant this module binds to
    something that is not a string (`MAX_FILE_LINES` and friends — a number can
    never be a command name). `bound_elsewhere` extends that to an imported
    name the tree binds to a non-string — known, and known not to be advice."""
    tree = ast.parse(source)
    resolved = {**_module_constants(tree), **(constants or {})}
    local = _module_level_names(tree) | (bound_elsewhere or set())
    documentation = _is_documentation(tree)
    holes: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr) or id(node) in documentation:
            continue
        for part in node.values:
            if (isinstance(part, ast.FormattedValue)
                    and isinstance(part.value, ast.Name)
                    and part.value.id.isupper()
                    and part.value.id not in resolved
                    and part.value.id not in local):
                holes.add(node.lineno)
    return sorted(holes)


NEVER_A_COMMAND = (ast.Tuple, ast.List, ast.Dict, ast.Set)
"""Literal containers. A name bound to one cannot BE a command string, so it is
safe to exempt from the hole report without knowing its value."""


KNOWN_NUMERIC_IMPORTS = frozenset({"MAX_GRANT_PROBES"})
"""Imported names bound to an ARITHMETIC expression of ints (`schema.approval`:
`MAX_GRANT_ACTIONS * PROBES_PER_ACTION`), which `_module_level_names` cannot prove numeric (a
BinOp may be `"ab" * 2`). Named one by one, never by shape, so the hole report keeps its teeth."""


def _module_level_names(tree: ast.Module) -> set[str]:
    """Names this module binds to something that CANNOT be a command string.

    AT-212: this used to exempt a name for being bound at all, while
    `_module_constants` resolves literals only — so

        PREP_COMMAND = os.environ.get("CMD", "autotester ingest prep")

    was exempt from the hole report AND invisible to the collector, in one
    move. A call can return anything, so being bound to a call is not an
    exemption; only a non-string literal or a literal container is."""
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        value = node.value
        if value is None:
            continue
        safe = ((isinstance(value, ast.Constant) and not isinstance(value.value, str))
                or isinstance(value, NEVER_A_COMMAND))
        if not safe:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names |= {t.id for t in targets if isinstance(t, ast.Name)}
    return names


def _module_name(path: Path, src_dir: Path) -> str:
    parts = path.relative_to(src_dir.parent).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _constant_index(src_dir: Path) -> dict[str, dict[str, str]]:
    return {_module_name(path, src_dir):
            _module_constants(ast.parse(path.read_text(encoding="utf-8")))
            for path in sorted(src_dir.rglob("*.py"))}


def _name_index(src_dir: Path) -> dict[str, set[str]]:
    """Every module-level name each module binds, whatever its type — so an
    imported constant can be told from an import this cannot see at all."""
    return {_module_name(path, src_dir):
            _module_level_names(ast.parse(path.read_text(encoding="utf-8")))
            for path in sorted(src_dir.rglob("*.py"))}


def _imported_names(tree: ast.Module, module: str, names: dict[str, set[str]]) -> set[str]:
    """Local aliases for names some module in the tree does bind."""
    known = {m: dict.fromkeys(bound, "") for m, bound in names.items()}
    return set(_imported_constants(tree, module, known))


def advice_in_source(src_dir: Path) -> list[Advice]:
    """Every command named anywhere under `src_dir`, one row per site.

    Deduped on `(file, line, command)` rather than `(file, command)`: the old
    key merged a composed message with the constant it interpolates, so a test
    asserting the command was present could not tell which of the two it had
    found — AT-206, and the reason the AT-176 fix could be removed entirely
    without a single failure."""
    index = _constant_index(src_dir)
    seen: set[tuple[str, int, str]] = set()
    out: list[Advice] = []
    for path in sorted(src_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        constants = _imported_constants(ast.parse(source), _module_name(path, src_dir), index)
        where = path.relative_to(src_dir)
        for line, command in advice_in(source, constants):
            if (str(where), line, command) in seen:
                continue
            seen.add((str(where), line, command))
            out.append(Advice(where, line, command))
    return out


def unresolved_in_source(src_dir: Path) -> list[tuple[Path, int]]:
    """Every site under `src_dir` naming `autotester` that could not be
    rendered — the collector's own blind spots, made countable."""
    index, names = _constant_index(src_dir), _name_index(src_dir)
    out: list[tuple[Path, int]] = []
    for path in sorted(src_dir.rglob("*.py")):
        source, module = path.read_text(encoding="utf-8"), _module_name(path, src_dir)
        tree = ast.parse(source)
        constants = _imported_constants(tree, module, index)
        bound = _imported_names(tree, module, names) | KNOWN_NUMERIC_IMPORTS
        out += [(path.relative_to(src_dir), line)
                for line in unresolved_in(source, constants, bound)]
    return out
