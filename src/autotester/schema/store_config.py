"""The ONE source of the store database name (D-121, D-122; contract mongo-store M1, M4).

`[tool.autotester.store].database` in the committed `pyproject.toml` is the only place the name
lives. It is not read from the environment, `.env`, the connection string's path, a CLI flag or any
argument. `StoreConfig` refuses the shapes that are unsafe by construction (the Mongo system
databases, anything that is not a plain identifier); the checks that need the connection string or
the server (URI-path clash, the identity marker) live in `store/mongo_guard.py`.
"""

from __future__ import annotations

import functools
import re
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from autotester.core.paths import code_root

DATABASE_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,37}")
FORBIDDEN_DATABASES = frozenset({"admin", "local", "config"})


class StoreConfigError(ValueError):
    """The store configuration, the connection string or the target database is unsafe."""


class StoreConfig(BaseModel):
    """`[tool.autotester.store]`: exactly one key, required, with no default (M1, M4)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    database: str

    @field_validator("database")
    @classmethod
    def _plain_and_not_a_system_database(cls, value: str) -> str:
        if DATABASE_PATTERN.fullmatch(value) is None:
            raise ValueError("database must match ^[A-Za-z][A-Za-z0-9_-]{0,37}$")
        if value.casefold() in FORBIDDEN_DATABASES:
            raise ValueError("database must not be a MongoDB system database")
        return value


def default_config_path() -> Path:
    """The CODE tree's `pyproject.toml`, never the data root (`core.paths.code_root`)."""
    return code_root() / "pyproject.toml"


@functools.cache
def _load(path: str) -> StoreConfig:
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise StoreConfigError(f"store config unreadable: {type(exc).__name__}") from None
    table = data.get("tool", {}).get("autotester", {}).get("store")
    if not isinstance(table, dict):
        raise StoreConfigError("[tool.autotester.store] is missing from the store config file")
    try:
        return StoreConfig.model_validate(table)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"]) or "store"
        raise StoreConfigError(f"[tool.autotester.store] {where}: {first['msg']}") from None


def load_store_config(path: Path | None = None) -> StoreConfig:
    """Read the config ONCE per (process, file); `None` is the committed file in the code tree."""
    return _load(str((path or default_config_path()).resolve()))


def clear_store_config_cache() -> None:
    """Test seam only: the process reads each config file once."""
    _load.cache_clear()
