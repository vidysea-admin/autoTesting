"""One signed-in identity on one platform, held as KEYS only (MP2, MPI5).

One job: `RoleAccount` -- the id, free-text role, platform, `.env` keys for username and password,
tenant label, optional mailbox and advisory persona. No value is ever a field here; a value-shaped
string in a key field is rejected by `SecretKey`. The role text is whatever the onboarder types:
no role name is known to the code. That the platform exists is checked by `Project`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.schema.mailbox_ref import MailboxRef, SecretKey
from autotester.schema.multi_role_enums import AccountOrigin
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.user_persona import PERSONA_ID_PATTERN

ROLE_ACCOUNT_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"


class RoleAccount(BaseModel):
    """A test account for one role. Its scope is the account's own permissions (D-018)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    role: str = Field(min_length=1, max_length=64, description="free text the onboarder typed")
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    username_key: SecretKey
    password_key: SecretKey
    tenant_label: str | None = Field(default=None, max_length=64)
    mailbox_ref: MailboxRef | None = None
    user_persona_ref: str | None = Field(default=None, pattern=PERSONA_ID_PATTERN)
    provided_by: AccountOrigin = AccountOrigin.ONBOARDER
