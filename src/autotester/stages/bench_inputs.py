"""The private CEO-benchmark answer list: validate, store under `.work/`, pin its sha256 (T-218).

One job: take the uploaded atomic list bytes, refuse anything that is not an `AtomicList`
(ids, priorities, techniques only -- no finding text, MPI6), keep the bytes at
`.work/ceo-bench/<slug>/atomic-list.json` and write `atomic-list.pin.json` beside it. T-218's run
reads the list through `load_pinned_list`, which re-hashes the file against the pin, so the run
scores exactly the bytes that were pinned. The list is git-ignored and no route serves it back;
only the hash, counts and time travel (`AtomicListPin`).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from pydantic import ValidationError

from autotester.core.paths import work_dir
from autotester.core.safe_names import safe_name
from autotester.schema.base import utc_now
from autotester.schema.ceo_inputs import AtomicList, AtomicListPin
from autotester.store.filestore import read_json, write_json

LIST_NAME = "atomic-list.json"
PIN_NAME = "atomic-list.pin.json"
MAX_BYTES = 256 * 1024


class ListRefused(ValueError):
    """The list cannot be stored or read; the message never carries a value from the file."""


def input_dir(slug: str, root: Path | None = None) -> Path:
    return work_dir(root) / "ceo-bench" / safe_name(slug)


def _reason(exc: ValidationError) -> str:
    """Where and what was wrong, from pydantic's locations and messages only (never `input`)."""
    found = [f"{'.'.join(str(p) for p in e['loc']) or 'file'}: {e['msg']}"
             for e in exc.errors(include_input=False, include_url=False)[:5]]
    return "not a valid atomic list (" + "; ".join(found) + ")"


def load_pin(slug: str, root: Path | None = None) -> AtomicListPin | None:
    return read_json(input_dir(slug, root) / PIN_NAME, AtomicListPin)


def save_atomic_list(slug: str, raw: bytes, who: str, root: Path | None = None) -> AtomicListPin:
    """Validate `raw` and pin it; raises `ListRefused` with nothing written."""
    if not raw:
        raise ListRefused("the file is empty")
    if len(raw) > MAX_BYTES:
        raise ListRefused(f"the file is larger than {MAX_BYTES // 1024} KiB")
    try:
        atomic = AtomicList.model_validate_json(raw)
    except ValidationError as exc:
        raise ListRefused(_reason(exc)) from None
    digest = hashlib.sha256(raw).hexdigest()
    folder = input_dir(slug, root)
    folder.mkdir(parents=True, exist_ok=True)
    before = load_pin(slug, root)
    replaced = [*before.replaced_sha256, before.sha256] if before and before.sha256 != digest \
        else (before.replaced_sha256 if before else [])
    staged = folder / (LIST_NAME + ".tmp")
    staged.write_bytes(raw)
    os.replace(staged, folder / LIST_NAME)
    pin = AtomicListPin(sha256=digest, items=len(atomic.items), bytes=len(raw),
                        pinned_at=utc_now(), pinned_by=who, replaced_sha256=replaced)
    write_json(folder / PIN_NAME, pin)
    return pin


def load_pinned_list(slug: str, root: Path | None = None) -> tuple[AtomicList, str]:
    """The list and its sha256, for `CeoRunInput`; refuses when nothing is pinned or the file
    no longer matches its pin."""
    pin = load_pin(slug, root)
    path = input_dir(slug, root) / LIST_NAME
    if pin is None or not path.exists():
        raise ListRefused("no atomic list is pinned for this project")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin.sha256:
        raise ListRefused("the stored list no longer matches its pinned sha256")
    return AtomicList.model_validate_json(raw), pin.sha256
