"""L1 committed leg: each generated doc's committed blob must equal a fresh regeneration (AT-697).

`doctor.check_generated_fresh` compares the file on DISK with a fresh render, so a regeneration that
was never committed passes clean while every clone receives the stale blob. This module reads the
blob out of HEAD and compares it, LF-normalised on both sides (git stores LF while a checkout on a
`core.autocrlf=true` machine holds CRLF; without normalising every file would always look stale).
Where no committed object can exist (not its own git repo, or no commit yet) the leg is reported as
`committed-leg-skipped` and named, never as passed.

It also hosts `check_state_bypass` (mongo-store M16), a second doctor rule: no raw filesystem call
on a state path outside `store/` and `browser/`. It lives here only because `doctor.py` and the
other ledger check modules are at the 300-line cap and a new module needs a D-122 entry; move it
to its own module when one is approved.
"""

from __future__ import annotations

import ast
import os
import subprocess
import tomllib
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


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n")


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
    if _lf(shown.stdout.decode("utf-8")) != _lf(fresh):
        return [Violation(STALE, rel, "committed blob (HEAD) differs from a fresh regeneration; "
                                      "commit the regenerated file")]
    return []


STATE_BYPASS = "state-bypass"
STATE_BYPASS_STALE = "state-bypass-stale"
_EXEMPT_DIRS = frozenset({"store", "browser"})
_STATE_MODULES = frozenset({  # modules that persist state under a path the CALLER passes in
    "core/trace.py", "stages/orchestrate_checkpoint.py", "auth/audit.py",
    "delivery/inbox.py", "stages/schedule_store.py", "core/env.py"})
_STATE_NAMES = frozenset({"ProjectPaths", "team_path", "paths"})
_STATE_PARTS = frozenset({".work", "projects", ".env"})
_ROOT_NAMES = frozenset({"repo_root", "root", "base"})
_METHODS = frozenset({"write_text", "write_bytes", "unlink", "glob", "rglob", "iterdir",
                      "exists", "stat"})
_OS_CALLS = frozenset({"replace", "rename", "link", "open", "remove", "unlink"})


def _names(expr: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(expr) if isinstance(n, ast.Attribute)}


def _is_state(expr: ast.AST, tainted: set[str], roots: set[str]) -> bool:
    names = _names(expr)
    if names & (_STATE_NAMES | tainted):
        return True
    parts = {n.value for n in ast.walk(expr) if isinstance(n, ast.Constant)}
    return bool(parts & _STATE_PARTS) and bool(names & (roots | _ROOT_NAMES))


def _bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    """`(tainted, roots)`: names bound (module-wide) to a state path, and to the data root."""
    tainted: set[str] = set()
    roots: set[str] = set()
    pairs = [(t, n.value) for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.AnnAssign))
             and n.value is not None
             for t in (n.targets if isinstance(n, ast.Assign) else [n.target])]
    for _ in range(4):  # a short fixpoint: `a = paths.x` then `b = a / "y"`
        for target, value in pairs:
            if not isinstance(target, ast.Name):
                continue
            if _names(value) & _ROOT_NAMES:
                roots.add(target.id)
            if _is_state(value, tainted, roots):
                tainted.add(target.id)
    return tainted, roots


def _writes(call: ast.Call) -> bool:
    """`open(...)` / `Path.open(...)` with a literal mode that writes, appends or creates."""
    literals = [*call.args, *(k.value for k in call.keywords if k.arg == "mode")]
    texts = [a.value for a in literals if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    return any(set(t) & set("wax+") for t in texts if len(t) <= 4)


def _kind(call: ast.Call, hit) -> str | None:  # type: ignore[no-untyped-def]
    """The raw-filesystem kind of `call` when it acts on a state path, else None."""
    fn = call.func
    if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id in {
            "os", "shutil"}:
        wanted = fn.value.id == "shutil" or fn.attr in _OS_CALLS
        return f"{fn.value.id}.{fn.attr}" if wanted and any(hit(a) for a in call.args) else None
    if isinstance(fn, ast.Attribute) and fn.attr in _METHODS and hit(fn.value):
        return fn.attr
    if isinstance(fn, ast.Attribute) and fn.attr == "open" and hit(fn.value) and _writes(call):
        return "open"
    if isinstance(fn, ast.Name) and fn.id == "open" and call.args and hit(call.args[0]):
        return "open" if _writes(call) else None
    return None


def _sites(path: Path, rel: str) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tainted, roots = _bindings(tree)
    everywhere = rel in _STATE_MODULES
    hit = (lambda e: True) if everywhere else (lambda e: _is_state(e, tainted, roots))
    found = [(c.lineno, k) for c in ast.walk(tree) if isinstance(c, ast.Call)
             and (k := _kind(c, hit)) is not None]
    return sorted(found)


def _allowed(root: Path, key: str) -> set[str]:
    """`path:line:kind` entries of `[tool.autotester.doctor.state-bypass].<key>`; the text after
    ` | ` is the owning unit (baseline) or the reason (permanent)."""
    table = root / "pyproject.toml"
    data = tomllib.loads(table.read_text(encoding="utf-8")) if table.exists() else {}
    rows = data.get("tool", {}).get("autotester", {}).get("doctor", {}).get("state-bypass", {})
    return {row.split(" | ", 1)[0] for row in rows.get(key, [])}


def check_state_bypass(root: Path) -> list[Violation]:
    """M16: no raw filesystem call on a state path outside `store/` and `browser/`.

    A call is flagged when its path derives from `ProjectPaths`, `team_path` or `repo_root()` with
    `.work`/`projects`, or when it sits in a module that persists state under a caller's path. The
    `baseline` rows are the known remaining sites (each tagged with the unit that removes it); a
    baseline row that no longer matches a call is itself reported, so the list can only shrink."""
    baseline, permanent = _allowed(root, "baseline"), _allowed(root, "permanent")
    seen: set[str] = set()
    out: list[Violation] = []
    base = root / "src" / "autotester"
    for path in sorted(base.rglob("*.py")):
        rel = path.relative_to(base).as_posix()
        if "__pycache__" in path.parts or rel.split("/")[0] in _EXEMPT_DIRS:
            continue
        for line, kind in _sites(path, rel):
            entry = f"{rel}:{line}:{kind}"
            seen.add(entry)
            if entry not in baseline | permanent:
                out.append(Violation(STATE_BYPASS, f"{rel}:{line}", f"`{kind}` on a state path: "
                                     "go through store.filestore (mongo-store M16)"))
    out += [Violation(STATE_BYPASS_STALE, e, "baseline/permanent row matches no call; delete it")
            for e in sorted((baseline | permanent) - seen)]
    return out
