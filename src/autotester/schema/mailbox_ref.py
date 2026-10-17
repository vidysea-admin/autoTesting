"""Where a role account's mailbox is, as KEYS only (MP2) -- plus the one secret-key rule.

One job: `MailboxRef` names the repo-root `.env` keys for an IMAP host, user and password (never a
value) and the folder to read. `SECRET_KEY_PATTERN` and `SecretKey` are the single home of the
"looks like an env key, not a value" rule; `SecretRef.key` (project.py) and `RoleAccount` import
them, so the rule is never copied. They live in this leaf module because project.py imports
role_account.py, which imports this file: a definition in project.py would be circular.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

SECRET_KEY_PATTERN = r"^[A-Z][A-Z0-9_]*$"
SecretKey = Annotated[str, Field(pattern=SECRET_KEY_PATTERN, max_length=64)]
"""An env-key name. A password, an address or any lower-case text fails the pattern (MP2)."""


class MailboxRef(BaseModel):
    """A read-only mailbox, named by keys. The values stay in the repo-root `.env`."""

    model_config = ConfigDict(extra="forbid")

    host_key: SecretKey
    user_key: SecretKey
    password_key: SecretKey
    folder: str = Field(default="INBOX", min_length=1, max_length=128, pattern=r"^[^\x00-\x1f]+$")
