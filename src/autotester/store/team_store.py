"""The sibling store for team data: markers, records, preferences, outboxes (T-205/TF7, R65).

One job: read and write team state under the data root (`core.paths.team_path`, i.e.
`<AUTOTESTER_ROOT>/.work/team/`) so every Group 10 unit does it the same safe way. Every path
part is validated by `core.safe_names` before any directory is made; whole-file writes go through
`store.filestore` (a temp file in the same directory, then `os.replace`, so a reader sees the old
file or the new one, never half); a marker is created with `O_CREAT | O_EXCL`, so exactly one
caller wins. No `fcntl`, `pwd`, `grp`, `resource` or `os.fork`: the same code runs on Windows
and Ubuntu.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

from autotester.core.paths import team_path
from autotester.store.filestore import ModelT, read_json, write_json

__all__ = ["create_marker", "read_model", "write_model"]


def write_model(root: Path | None, model: BaseModel, *parts: str) -> Path:
    """Atomically write `model` as JSON at `<team root>/<parts...>`; returns the path."""
    path = team_path(*parts, root=root)
    write_json(path, model)
    return path


def read_model(root: Path | None, model_cls: type[ModelT], *parts: str) -> ModelT | None:
    """The model stored at `<team root>/<parts...>`, or `None` when it does not exist."""
    return read_json(team_path(*parts, root=root), model_cls)


def create_marker(root: Path | None, *parts: str, body: str = "") -> bool:
    """Create the marker file once. True for the one caller that created it, else False."""
    return _create_exclusive(team_path(*parts, root=root), body)


def _create_exclusive(path: Path, body: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(body)
    return True
