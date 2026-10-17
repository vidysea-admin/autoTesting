"""L1 committed leg: each generated doc's committed blob must equal a fresh regeneration (AT-697).

`doctor.check_generated_fresh` compares the file on DISK with a fresh render, so a regeneration that
was never committed passes clean while every clone receives the stale blob. This module reads the
blob out of HEAD and compares it, LF-normalised on both sides (git stores LF while a checkout on a
`core.autocrlf=true` machine holds CRLF; without normalising every file would always look stale).
Where no committed object can exist (not its own git repo, or no commit yet) the leg is reported as
`committed-leg-skipped` and named, never as passed.
"""

from __future__ import annotations

import os
import subprocess
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
