"""Shared helpers for the crawl-guidance tests (qa/contracts/crawl-guidance.md G1-G12).

Not a test module. Holds the volatile-field normaliser behind the G5 byte-identical baseline and
the fake providers every guidance test uses (no real model, no network, no credential).
"""

from __future__ import annotations

import re
from pathlib import Path

BASELINE_DIR = Path(__file__).parent / "fixtures" / "crawl_guidance"
ARTIFACTS = ("crawl.json", "nodes.jsonl", "edges.jsonl")
_VOLATILE = [
    (re.compile(r'"(created_at|started_at|finished_at|heartbeat_at)":\s*"[^"]*"'), r'"\1":"T"'),
    (re.compile(r"crawl_[0-9A-Z]{26}"), "crawl_ID"),
    (re.compile(r"appr_[0-9A-Za-z]+"), "appr_ID"),
    (re.compile(r"edge_[0-9a-f]{12}"), "edge_ID"),
]


def normalise(text: str) -> str:
    """The artifact text with every per-run value (clock, ulid, hash of a ulid) fixed."""
    for pattern, replacement in _VOLATILE:
        text = pattern.sub(replacement, text)
    return text


def crawl_artifacts(tmp_path: Path, slug: str = "demo") -> dict[str, str]:
    """name -> normalised text of the one crawl under `tmp_path`'s project."""
    crawl_dir = next((tmp_path / "projects" / slug / "crawl").iterdir())
    return {name: normalise((crawl_dir / name).read_text(encoding="utf-8")) for name in ARTIFACTS}


def baseline(name: str) -> str:
    text = (BASELINE_DIR / f"baseline_{name}").read_text(encoding="utf-8")
    return text.replace(chr(13) + chr(10), chr(10))


def regenerate_baseline(tmp_path: Path) -> None:  # pragma: no cover - run on the pre-change tree
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in crawl_artifacts(tmp_path).items():
        (BASELINE_DIR / f"baseline_{name}").write_text(text, encoding="utf-8", newline="\n")

