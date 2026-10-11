"""The one place any artifact is read from or written to disk. Contract: core-invariants.md C6.

Every stage's typed convenience wrapper (`ProjectStore`, the feature ledger)
is built on these primitives, so "how does file X get persisted" always
has exactly one answer. Writes are atomic (temp file + `os.replace`) so a
crash mid-write never leaves a half-written artifact for a human — or the
next run — to trip over.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def write_text(path: Path, text: str) -> None:
    """Whole-file, atomic text. For stores that hold something other than one model."""
    _atomic_write(path, text)


def write_json(path: Path, model: BaseModel) -> None:
    """Whole-file, atomic. For the single-object artifacts (project, flowspec)."""
    _atomic_write(path, model.model_dump_json(indent=2, exclude_none=True) + "\n")


def read_json(path: Path, model_cls: type[ModelT]) -> ModelT | None:
    """`None` when the file is absent — a project with no flowspec yet is not an error.

    A file that exists but fails to validate raises, naming the path.
    """
    if not path.exists():
        return None
    try:
        return model_cls.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from None


def read_jsonl(path: Path, model_cls: type[ModelT]) -> list[ModelT]:
    """Every row, in file order. A malformed row raises with its line number."""
    if not path.exists():
        return []
    items: list[ModelT] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(model_cls.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from None
    return items


def append_jsonl(path: Path, model: BaseModel) -> None:
    """One more line. Never rewrites what is already there — cheap and crash-safe
    (a torn write can only ever damage the last line, never an earlier one)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(model.model_dump_json(exclude_none=True) + "\n")


def delete_jsonl_row(
    path: Path, model_cls: type[ModelT], row_id: str, *, key: str = "id"
) -> bool:
    """Drop the row whose `key` equals `row_id`; True when one was removed.

    Same whole-file atomic rewrite as `upsert_jsonl`, and the same caveat: for
    a small collection a human curates, never for append-only history.
    """
    items = read_jsonl(path, model_cls)
    kept = [item for item in items if getattr(item, key) != row_id]
    if len(kept) == len(items):
        return False
    _atomic_write(path, "".join(item.model_dump_json(exclude_none=True) + "\n" for item in kept))
    return True


def upsert_jsonl(path: Path, model: ModelT, model_cls: type[ModelT], *, key: str = "id") -> None:
    """Replace the row whose `key` matches this model's, else append.

    Rewrites the whole file atomically — use for status transitions on a
    small collection (e.g. a case moving proposed -> approved); prefer
    `append_jsonl` for pure history where nothing is ever replaced.
    """
    items = read_jsonl(path, model_cls)
    target = getattr(model, key)
    lines: list[str] = []
    replaced = False
    for item in items:
        if getattr(item, key) == target:
            lines.append(model.model_dump_json(exclude_none=True))
            replaced = True
        else:
            lines.append(item.model_dump_json(exclude_none=True))
    if not replaced:
        lines.append(model.model_dump_json(exclude_none=True))
    _atomic_write(path, "".join(f"{line}\n" for line in lines))
