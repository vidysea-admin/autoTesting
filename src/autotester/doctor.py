"""Design enforcement. Runs the rules that keep this repo readable.

These limits are not style preferences. They exist because the previous project
(d:/erp) lost human control when files, duplicated concepts, and root-level
scratch grew unchecked. `autotester doctor` fails the build before that starts.
"""

from __future__ import annotations

import ast
import os
import sys
import tomllib
from dataclasses import dataclass
from importlib.metadata import packages_distributions
from pathlib import Path

from autotester.core.paths import RepoDocs, repo_root

MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 50
BANNED_NAME_HINTS = ("_v2", "_new", "_old", "_copy", "_final", "_temp")
ALLOWED_ROOT_ENTRIES = {
    ".claude", ".dockerignore", ".git", ".gitignore", ".goal", ".python-version", ".venv",
    ".work", "AGENTS.md", "CLAUDE.md", "README.md", "docker", "docker-compose.yml", "Dockerfile",
    "docs", "goal.md", "plan.md", "profiles", "projects", "pyproject.toml", "qa", "scripts",
    "src", "target.md", "tests",
    "uv.lock",
}
"""AGENTS.md sits beside CLAUDE.md (AT-283): a second AI tool's project-instruction file at the
same root, not scratch or evidence — the thing check_root_clean actually exists to catch.
target.md is the human roadmap (shipped-vs-target milestone checklist, routed in CLAUDE.md),
a sibling of goal.md/plan.md — a real project-doc surface, not scratch."""


@dataclass(frozen=True)
class Violation:
    rule: str
    location: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.location} — {self.detail}"


def _python_files(root: Path) -> list[Path]:
    return [
        p
        for p in (root / "src").rglob("*.py")
        if ".venv" not in p.parts and "__pycache__" not in p.parts
    ]


def _capped_files(root: Path) -> list[Path]:
    """C2 caps EVERY file in src/ and tests/, not only Python (AT-419): a 316-line
    visual_order.js once passed as "doctor: clean". Binary files have no lines.
    The walk never enters a directory that resolves elsewhere (a junction or symlink:
    a loop crashed doctor, a foreign folder got capped) nor a tool cache (AT-461)."""
    out: list[Path] = []
    for base in (root / "src", root / "tests"):
        for dirpath, dirnames, filenames in os.walk(base):
            here = os.path.realpath(dirpath)
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d != "__pycache__"
                and os.path.normcase(os.path.realpath(os.path.join(dirpath, d)))
                == os.path.normcase(os.path.join(here, d))
            ]
            out += [Path(dirpath, f) for f in filenames]
    return out


def check_file_sizes(root: Path) -> list[Violation]:
    out = []
    for path in _capped_files(root):
        try:
            lines = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue
        if lines > MAX_FILE_LINES:
            out.append(Violation("file-too-long", str(path.relative_to(root)),
                                 f"{lines} lines > {MAX_FILE_LINES}; split by responsibility"))
    return out


def check_function_sizes(root: Path) -> list[Violation]:
    out = []
    for path in _python_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno:
                length = node.end_lineno - node.lineno
                if length > MAX_FUNCTION_LINES:
                    out.append(Violation("function-too-long",
                                         f"{path.relative_to(root)}:{node.lineno}",
                                         f"{node.name} is {length} lines > {MAX_FUNCTION_LINES}"))
    return out


def check_file_names(root: Path) -> list[Violation]:
    out = []
    for path in _python_files(root):
        if any(hint in path.stem for hint in BANNED_NAME_HINTS):
            out.append(Violation("drift-filename", str(path.relative_to(root)),
                                 "edit the original in place instead of versioning the filename"))
    return out


def check_root_clean(root: Path) -> list[Violation]:
    out = []
    for entry in root.iterdir():
        if entry.name not in ALLOWED_ROOT_ENTRIES and not entry.name.startswith("."):
            out.append(Violation("root-clutter", entry.name,
                                 "scratch and evidence belong in .work/, not the repo root"))
    return out


def check_duplicate_definitions(root: Path) -> list[Violation]:
    """Same class or top-level function name defined in two modules = drift."""
    seen: dict[str, str] = {}
    out = []
    for path in _python_files(root):
        rel = str(path.relative_to(root))
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and not node.name.startswith("_"):
                if node.name in seen and seen[node.name] != rel:
                    out.append(Violation("duplicate-concept", f"{rel}:{node.lineno}",
                                         f"'{node.name}' also defined in {seen[node.name]}"))
                seen.setdefault(node.name, rel)
    return out


def _dep_name(requirement: str) -> str:
    """PEP 508 requirement string -> bare, normalized distribution name."""
    name = requirement
    for cut in "[<>=!~; ":
        name = name.split(cut, 1)[0]
    return name.strip().lower().replace("_", "-")


def check_dependencies_declared(root: Path) -> list[Violation]:
    """AT-130: an import that resolves only because some OTHER declared package
    happens to depend on it is a hazard -- the day that other package drops or
    renames the dependency, the import breaks with no pyproject change and no
    failing test (that is exactly how GeminiProvider's `google-genai` import
    survived undeclared, riding on `langchain-google-genai`'s pin). Every
    third-party top-level import under src/ must be declared directly, or be
    stdlib. Imports of modules the current environment cannot resolve at all
    are left to `import` itself to fail -- this check only catches the
    "works by transitive accident" class. AT-590: a declared-optional soft import
    (TYPE_CHECKING-only or try/except ImportError/ModuleNotFoundError) is skipped
    here instead, per `ledger.render.soft_import_ids` (moved there -- this file is
    at C2's 300-line cap)."""
    from autotester.ledger.render import soft_import_ids

    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return []
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    declared = {_dep_name(d) for d in data.get("project", {}).get("dependencies", [])}
    dist_map = packages_distributions()
    stdlib = set(sys.stdlib_module_names)

    out = []
    for path in _python_files(root):
        rel = path.relative_to(root)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        soft = soft_import_ids(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [(alias.name, node.lineno) for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [(node.module, node.lineno)]
            else:
                continue
            if id(node) in soft:
                continue
            for module, lineno in modules:
                top = module.split(".")[0]
                if top == "autotester" or top in stdlib:
                    continue
                candidates = dist_map.get(top)
                if not candidates:  # not resolvable in this env -- not this check's job
                    continue
                normalized = {c.lower().replace("_", "-") for c in candidates}
                if not normalized & declared:
                    out.append(Violation(
                        "undeclared-dependency", f"{rel}:{lineno}",
                        f"`{module}` resolves via {sorted(candidates)}, none of which are "
                        "declared in [project].dependencies -- add the direct package"))
    return out


def check_generated_fresh(root: Path) -> list[Violation]:
    """L1: ARCHITECTURE generated sections and SNAPSHOT must equal a fresh regeneration."""
    from autotester.ledger.render import apply_map, render_snapshot

    docs = RepoDocs(root)
    out = []
    if docs.map.exists():
        try:
            if apply_map(docs) != docs.map.read_text(encoding="utf-8"):
                out.append(Violation("stale-generated", "docs/MAP.md",
                                     "generated sections differ; run `autotester map`"))
        except ValueError as exc:
            out.append(Violation("stale-generated", "docs/MAP.md", str(exc)))
    if docs.snapshot.exists() or docs.features.exists():
        current = docs.snapshot.read_text(encoding="utf-8") if docs.snapshot.exists() else ""
        try:
            fresh = render_snapshot(docs)
        except Exception as exc:  # a broken ledger is reported by check_ledger, not raised here
            out.append(Violation("stale-generated", "docs/SNAPSHOT.md",
                                 f"cannot regenerate: {type(exc).__name__}"))
            return out
        if fresh != current:
            out.append(Violation("stale-generated", "docs/SNAPSHOT.md",
                                 "differs from regeneration; run `autotester snapshot`"))
    return out


def check_architecture_budget(root: Path) -> list[Violation]:
    """C2: ARCHITECTURE.md stays within its line budget (AT-019)."""
    from autotester.ledger.render import ARCHITECTURE_MAX_LINES

    path = RepoDocs(root).architecture
    if not path.exists():
        return []
    lines = len(path.read_text(encoding="utf-8").splitlines())
    if lines > ARCHITECTURE_MAX_LINES:
        return [Violation("architecture-too-long", "docs/ARCHITECTURE.md",
                          f"{lines} lines > {ARCHITECTURE_MAX_LINES}; move detail to a routed doc")]
    return []


def check_docs_routed(root: Path) -> list[Violation]:
    """L6: every docs/*.md self-describes and is listed in the CLAUDE.md router, and vice versa."""
    from autotester.ledger.render import doc_header_missing, router_paths

    docs = RepoDocs(root)
    if not docs.docs_dir.exists():
        return []
    out = []
    routed = router_paths(docs.router)
    on_disk = {p.relative_to(root).as_posix() for p in docs.docs_dir.rglob("*.md")}
    for path in sorted(on_disk):
        if doc_header_missing(root / path):
            out.append(Violation("doc-header-missing", path,
                                 "needs **Purpose:** and **Open me when:**"))
        if path not in routed:
            out.append(Violation("doc-unrouted", path,
                                 "add a row to the router table in CLAUDE.md"))
    for path in sorted(routed - on_disk):
        if path.endswith(".md"):
            out.append(Violation("router-dangling", path, "router names a doc that does not exist"))
    return out


def run(root: Path | None = None) -> list[Violation]:
    """All checks, in reporting order."""
    from autotester.ledger.checks import (
        check_adapter_pytest_q,
        check_goal_pytest_q,
        check_ledger,
        check_qa_issue_rows,
    )

    base = root or repo_root()
    violations: list[Violation] = []
    for check in (check_file_sizes, check_function_sizes, check_file_names,
                  check_root_clean, check_duplicate_definitions,
                  check_dependencies_declared,
                  check_ledger, check_qa_issue_rows, check_adapter_pytest_q,
                  check_goal_pytest_q, check_generated_fresh,
                  check_architecture_budget, check_docs_routed):
        violations.extend(check(base))
    return violations
