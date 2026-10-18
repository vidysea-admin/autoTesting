"""How one platform's sign-in page is driven, so a live role port can sign its accounts in (MP11).

One job: `RoleSignIn` -- the sign-in URL, the three controls to use and the element that proves the
account is signed in. It holds locators and a URL only; the account's username and password stay
`{{SECRET:KEY}}` placeholders resolved at fill time by `RoleAccount.username_key/password_key`
(MPI5). `signed_in_target` is what separates "the form was submitted" from "the role is in": a
role whose target never appears has not signed in, and its oracles must report `errored`.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotester.schema.platform import PLATFORM_ID_PATTERN


class RoleSignIn(BaseModel):
    """The sign-in recipe of one platform; every account on the platform uses it."""

    model_config = ConfigDict(extra="forbid")

    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    login_url: str = Field(min_length=1, max_length=500)
    user_locator: str = Field(min_length=1, max_length=200)
    password_locator: str = Field(min_length=1, max_length=200)
    submit_locator: str = Field(min_length=1, max_length=200)
    signed_in_target: str = Field(
        min_length=1, max_length=200,
        description="a locator visible only after a successful sign-in")

    @field_validator("login_url")
    @classmethod
    def _plain_http_url(cls, url: str) -> str:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or "@" in parts.netloc:
            raise ValueError("login_url must be an http(s) URL without userinfo")
        return url
