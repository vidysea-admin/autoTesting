"""AT-516 (D-048, gate answer c): does a unit's evidence spec (`mutations.json`)
stay runnable, or is it stale -- and if stale, was that decided or did it just
happen?

A later unit sometimes splits or renames the test file a mutation spec's
`kills` node-ids name (AT-506 moved `test_doctor.py`'s record-rule tests into
`test_ledger_checks.py`; AT-513 later moved a block of THOSE into
`test_marker_blocks.py`). The moved-out spec still parses and its bytes never
change -- but `mutation_check.py` refuses to run it (a `kills` node-id pytest
no longer collects fails closed, `mutation_check.py:319-323`), so the evidence
can never be re-derived.

Umesh answered gate `at516-evidence-spec-splitting-policy` with (c) (D-048,
2026-09-26): the spec stays byte-intact -- this module never writes to
`mutations.json` -- and gets a machine-readable tag naming where the test
actually lives now, in a SIDECAR file (`mutations.stale.json`), so a check can
tell "stale on purpose" from "stale because a test quietly vanished". A
tombstone entry counts only if its `moved_to` node-id ACTUALLY resolves in the
current tree; an absent or a lying tombstone is reported exactly like no
tombstone at all -- trusting a tag's presence instead of resolving it is the
vacuous-guard class (AT-218) this project keeps re-discovering.

AT-711 adds the same idea for a manifest's capability rows: a row names the
tree it ran on (`tree: head=<sha> porcelain=<clean|digest>`, from `record_tree`)
and `check_capability_row_tree` COMPARES that head with the submitted commit.
A recorded head nothing compares is a field, not a check; a dirty digest is
disclosure (`tree_disclosures`), never disqualification.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from autotester.doctor import Violation
from autotester.schema.evidence_tombstone import EvidenceTombstone


def _bare(name: str) -> str:
    """Drop a parametrize suffix (`[...]`); the bare function name underneath."""
    return name.split("[", 1)[0]


def _scope_files(root: Path, tests_field: object) -> list[Path]:
    """`mutation_check.py`'s `collected_tests()` collects only inside the spec's
    OWN `"tests"` field (a path or a list of paths) -- a bare `kills` name is
    resolved against that scope, never the whole repo (`scripts/mutation_check.py`
    `collected_tests`). A directory entry expands to every `.py` file under it."""
    entries = [tests_field] if isinstance(tests_field, str) else (
        tests_field if isinstance(tests_field, list) else [])
    out: list[Path] = []
    for entry in entries:
        if not isinstance(entry, str):
            continue
        path = root / entry
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            out.extend(sorted(path.rglob("*.py")))
    return out


def _defines(path: Path, name: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return f"def {name}(" in text


def _resolves(root: Path, nodeid: str, scope: list[Path]) -> bool:
    """Does this `kills` node-id still collect, the same way
    `mutation_check.py` itself would attribute it?

    A literal `def <name>(` search, not a live pytest collection -- `doctor`
    runs every check on every invocation, and a subprocess per node-id is the
    wrong cost for a design-rule check. It cannot tell a real function from one
    merely mentioned in a comment or a string; that is a narrower, already
    accepted blind spot, since `mutation_check.py` still fails closed at run
    time on any node-id that turns out not to actually collect.

    A **path-qualified** id (`file::name[params]`) is checked at that exact
    file. A **bare** id (`name[params]`, no `::`) is a valid `mutation_check.py`
    shorthand and is checked across the spec's own declared `tests` scope,
    never the whole repo -- treating every bare name as unresolvable is exactly
    the false-positive AT-311's mutation and AT-520/AT-523's own specs hit
    during this unit's own build.
    """
    if "::" in nodeid:
        path_part, name = nodeid.rsplit("::", 1)
        path = root / path_part
        return path.is_file() and _defines(path, _bare(name))
    name = _bare(nodeid)
    return any(_defines(f, name) for f in scope)


def _tombstone_key(nodeid: str) -> str:
    """A tombstone names the FUNCTION a `kills` entry belongs to (its bare name,
    with the file prefix if the entry carried one), not one exact parametrized
    id -- every parameter of a moved parametrized test shares one entry."""
    if "::" in nodeid:
        path_part, name = nodeid.rsplit("::", 1)
        return f"{path_part}::{_bare(name)}"
    return _bare(nodeid)


def _load_spec(spec_path: Path) -> tuple[object, set[str]]:
    """`(tests field, kills node-ids)`, or `(None, set())` for a file that is not
    shaped like a maker mutation spec (a checker's own sabotage log under a
    `browser-*` evidence directory is a list of rows, a different artifact)."""
    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, set()
    if not isinstance(data, dict):
        return None, set()
    kills: set[str] = set()
    for mutation in data.get("mutations", []):
        if isinstance(mutation, dict):
            kills.update(k for k in mutation.get("kills", []) if isinstance(k, str))
    return data.get("tests"), kills


def _load_tombstone(spec_dir: Path) -> EvidenceTombstone:
    path = spec_dir / "mutations.stale.json"
    if not path.exists():
        return EvidenceTombstone()
    return EvidenceTombstone.model_validate_json(path.read_text(encoding="utf-8"))


def check_stale_evidence_specs(root: Path) -> list[Violation]:
    """Every `qa/evidence/<unit>/mutations.json` either still resolves, or is
    tagged stale-on-purpose by a sidecar `mutations.stale.json` whose
    `moved_to` actually resolves. Anything else is stale by neglect."""
    evidence_dir = root / "qa" / "evidence"
    if not evidence_dir.exists():
        return []
    out: list[Violation] = []
    for spec_dir in sorted(p for p in evidence_dir.iterdir()
                            if p.is_dir() and not p.name.startswith("browser-")):
        spec_path = spec_dir / "mutations.json"
        if not spec_path.exists():
            continue
        tests_field, kills = _load_spec(spec_path)
        if not kills:
            continue
        scope = _scope_files(root, tests_field)
        tagged = {e.old_nodeid: e for e in _load_tombstone(spec_dir).entries}
        rel = spec_path.relative_to(root).as_posix()
        for nodeid in sorted(kills):
            if _resolves(root, nodeid, scope):
                continue
            entry = tagged.get(_tombstone_key(nodeid))
            if entry is not None and _resolves(root, entry.moved_to, scope=[]):
                continue  # stale on purpose, and the tag is honest
            detail = (
                f"tagged moved to {entry.moved_to!r} but that does not resolve either"
                if entry is not None
                else "no mutations.stale.json entry tags this as deliberate"
            )
            out.append(Violation("evidence-spec-stale-unexplained", f"{rel}::{nodeid}", detail))
    return out


_TREE_RE = re.compile(
    r"tree:\s*head=([0-9a-f]{7,40})\s+porcelain=(clean|[0-9a-f]{8,64})", re.IGNORECASE)
_MANIFEST_DIR = "qa/manifests/"


def _git(root: Path, *args: str) -> str:
    """Read-only git over an argv list (no shell). Raises on a git failure."""
    out = subprocess.run(["git", "-C", str(root), *args],
                         capture_output=True, text=True, check=True)
    return out.stdout


def record_tree(root: Path) -> str:
    """The marker a maker pastes into a capability row: HEAD plus a digest of
    `git status --porcelain` taken NOW, or `porcelain=clean` for an empty one."""
    head = _git(root, "rev-parse", "HEAD").strip()
    porcelain = _git(root, "status", "--porcelain")
    digest = hashlib.sha256(porcelain.encode("utf-8")).hexdigest()[:16] if porcelain else "clean"
    return f"tree: head={head} porcelain={digest}"


def _capability_rows(text: str) -> list[str]:
    """Data rows of the `## Capability coverage` table (header and separator dropped)."""
    rows: list[str] = []
    in_section, previous = False, ""
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.lower().startswith("## capability coverage")
            previous = ""
            continue
        if not (in_section and line.lstrip().startswith("|")):
            continue
        if re.fullmatch(r"\s*\|[\s:|-]+\|\s*", line):
            if rows and rows[-1] == previous:
                rows.pop()  # the row before the separator was the header
            continue
        rows.append(line)
        previous = line
    return rows


def _head_covers(root: Path, recorded: str, submitted: str) -> bool:
    """Equal heads, or the only paths between them are manifests (the maker
    commits the manifest AFTER the code commit it names, so it cannot name its own)."""
    if submitted.startswith(recorded) or recorded.startswith(submitted):
        return True
    try:
        changed = _git(root, "diff", "--name-only", recorded, submitted).split()
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(changed) and all(c.startswith(_MANIFEST_DIR) for c in changed)


def check_capability_row_tree(manifest: Path, submitted: str, root: Path) -> list[Violation]:
    """Refuse a capability row whose recorded HEAD is not the submitted commit,
    and a row that records none. A non-empty porcelain digest is not checked here."""
    rel = manifest.name
    out: list[Violation] = []
    for number, row in enumerate(_capability_rows(manifest.read_text(encoding="utf-8")), 1):
        found = _TREE_RE.search(row)
        if found is None:
            out.append(Violation("capability-row-tree-unrecorded", f"{rel}::row{number}",
                                 "row names no `tree: head=<sha> porcelain=<...>` marker"))
        elif not _head_covers(root, found.group(1).lower(), submitted.lower()):
            out.append(Violation(
                "capability-row-tree-mismatch", f"{rel}::row{number}",
                f"row ran at {found.group(1)[:12]}, submitted commit is {submitted[:12]}"))
    return out


def tree_disclosures(manifest: Path) -> list[str]:
    """Rows that ran on a dirty tree (digest is not `clean`): disclosure, not failure."""
    rows = _capability_rows(manifest.read_text(encoding="utf-8"))
    found = (_TREE_RE.search(r) for r in rows)
    return [f"row{n}: head={m.group(1)[:12]} porcelain={m.group(2)}"
            for n, m in enumerate(found, 1) if m and m.group(2).lower() != "clean"]
