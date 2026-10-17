"""One product surface inside a multi-platform project (MP1).

One job: `Platform` -- a host set a browser may be driven on, with its own login case. A project
with several linked products (a parent app, a school portal) declares several; an old project with
one `base_url` is a single implicit platform (`Project.effective_platforms`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

IMPLICIT_PLATFORM_ID = "primary"
"""The id of the one platform an old project (no `platforms`) is read as."""

PLATFORM_ID_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"


class Platform(BaseModel):
    """A platform's boundary. Secrets for it are scoped within `allowed_domains` (MPI5)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PLATFORM_ID_PATTERN)
    name: str
    base_url: str
    allowed_domains: list[str] = Field(default_factory=list)
    include_subdomains: bool = Field(
        default=True, strict=True,
        description="False pins a role account on this platform to the exact hosts, so a sibling "
                    "platform on the same parent domain is not admitted by the suffix match",
    )
    login_case_id: str | None = Field(default=None, description="the case that signs in here")

    @field_validator("allowed_domains")
    @classmethod
    def _clean_domains(cls, domains: list[str]) -> list[str]:
        """A blank domain would match an empty host and open the gate (AT-001)."""
        cleaned = [d.strip().lower().lstrip(".") for d in domains]
        if any(not d for d in cleaned):
            raise ValueError("platform domains must be non-empty hostnames")
        return cleaned
