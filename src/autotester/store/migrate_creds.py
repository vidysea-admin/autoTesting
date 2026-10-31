"""Copy declared project credentials from the repo-root `.env` into the credential store (U8, M46).

One job: for each project, find the credential keys it DECLARES (`project.json` `secrets[*].key`),
take only those from `.env`, and hand them to the credential door
(`ui/env_editor.py::put_credentials`), never to a collection directly. The filter runs BEFORE the
door, so an undeclared `.env` line is never carried forward. Deployment secrets (the Mongo URI,
`AUTOTESTER_*`, provider keys) are counted and never named (M36). `.env` is opened for reading
only, no value is returned in a report or raised in an error, and the approval key is not read.
"""

from __future__ import annotations

import contextlib
import os
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from autotester.core.env import MONGO_URI_ENV, is_server_key, read_dotenv
from autotester.store.filestore import FileBackend

AREAS_ENV = "AUTOTESTER_STORE_AREAS"
Pair = tuple[str, str, str]  # (project slug, key, value): the value is never printed


@contextlib.contextmanager
def credentials_on() -> Iterator[None]:
    """The credential door opens only with the credentials area on mongo; migrating before the G1
    area flip turns it on for this process alone."""
    old = os.environ.get(AREAS_ENV)
    os.environ[AREAS_ENV] = f"{old},credentials=mongo" if old else "credentials=mongo"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(AREAS_ENV, None)
        else:
            os.environ[AREAS_ENV] = old


def _declared(src: FileBackend, slug: str) -> list[str]:
    from autotester.schema.project import SecretDeclarations

    try:
        text = src.get(f"projects/{slug}/project.json")
        rows = SecretDeclarations.model_validate_json(text).secrets if text else []
    except (OSError, ValueError):
        return []
    return [str(r["key"]) for r in rows if isinstance(r, dict) and "key" in r]


def credential_pairs(root: Path, project: str | None) -> tuple[list[Pair], int]:
    """The `(slug, key, value)` of each key a project declares that `.env` sets, and how many
    were left out as deployment secrets (a count, never a name)."""
    path = root / ".env"
    env = {k: v for k, v in read_dotenv(path).items() if v} if path.is_file() else {}
    src, pairs, dropped = FileBackend(root), [], 0
    for slug in [project] if project else src.children("projects"):
        for key in (k for k in _declared(src, slug) if k in env):
            if key.upper() == MONGO_URI_ENV or is_server_key(key):
                dropped += 1
            else:
                pairs.append((slug, key, env[key]))
    return pairs, dropped


def import_credentials(pairs: list[Pair], remote: bool, apply: bool) -> Counter[str]:
    """Through the door; a stored key is never replaced. Counts only: `to_insert`, `unchanged`,
    `conflicting-id`, `written`, `refused`. `remote=False` opens nothing."""
    out: Counter[str] = Counter()
    if not remote:
        out["to_insert"] = len(pairs)
        return out
    from autotester.core.env import credential_collection
    from autotester.ui.env_editor import InvalidEnvValue, put_credentials

    with credentials_on():
        coll = credential_collection()
        for slug, key, value in pairs:
            held = coll.find_one({"_id": key})
            if held is not None:
                out["unchanged" if (held.get("p"), held.get("value")) == (slug, value)
                    else "conflicting-id"] += 1
            elif not apply:
                out["to_insert"] += 1
            else:
                try:
                    put_credentials(slug, {key: value})
                    out["written"] += 1
                except InvalidEnvValue:  # includes CredentialRefused; its text names a key only
                    out["refused"] += 1
    return out
