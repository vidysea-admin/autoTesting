"""Doctor's advisory on `${` inside repo-root `.env` values (AT-1389).

One job: turn `core.env.dollar_value_keys` into a non-blocking doctor warning that carries the
count and the KEY NAMES only. A value is never read into the message."""

from __future__ import annotations

from pathlib import Path

from autotester.core.env import dollar_value_keys, dollar_warning
from autotester.doctor import Violation

RULE = "env-dollar-literal"


def check_env_dollar(root: Path) -> list[Violation]:
    """Zero keys -> no row; otherwise ONE row naming the count and the keys."""
    keys = dollar_value_keys(root)
    return [Violation(RULE, ".env", dollar_warning(keys))] if keys else []
