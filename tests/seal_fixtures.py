"""Fixtures for the L10 seal tests: tiny real git repos with a reviewed inbox block."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from autotester import doctor
from autotester.ledger import citations

MANIFEST = "# M\nStatus: checked-PASS (cycle 1)\nauthorized by D-001\n"
LOG = "## D-001 | 2026-09-01 | type: decision | status: ACTIVE\n**What:** x\n"


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                           *args], check=True, capture_output=True, text=True)
    return done.stdout.strip()


def sha(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(text.encode("utf-8"))


def row(root: Path, rel: str, **over) -> dict:
    row = dict(kind="sealed-record", path=rel, scope="file",
               sha256=sha((root / rel).read_text(encoding="utf-8")),
               baseline=git(root, "rev-parse", "HEAD"), reason="closed historical record",
               reviewer="/checker", review_ref="qa/review.md")
    row.update(over)
    return row


def block(root: Path, rows: list[dict]) -> None:
    body = "<!-- BEGIN T196 CURRENT CITATION REVIEWS -->\n"
    body += "".join(f"<!-- citation-review: {json.dumps(r)} -->\n" for r in rows)
    write(root, "qa/feedback-inbox.md", body + "<!-- END T196 CURRENT CITATION REVIEWS -->\n")


def tree(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
    git(tmp_path, "init", "-q")
    write(tmp_path, "docs/DECISIONS.md", "")
    write(tmp_path, "qa/review.md", "Attribution: /checker\nReviewer: Umesh\n")
    for rel, text in (files or {"qa/manifests/m.md": MANIFEST}).items():
        write(tmp_path, rel, text)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "baseline")
    return tmp_path


def rules(root: Path) -> list[str]:
    return [v.rule for v in citations.check_citation_subjects(root)]


def blocking(root: Path) -> list[doctor.Violation]:
    return doctor.blocking(citations.check_citation_subjects(root))
