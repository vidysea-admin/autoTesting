"""The authorisation-probe plan, its two transport seams and the run's own log (MP18-MP20).

One job: say WHAT `stages/oracle_tenant.py` and `stages/oracle_privilege.py` may probe and what
they leave behind. `AuthzPlan` is written by the scenario author and holds ids of roles and URL
templates only -- no foreign id, no row, no credential. `ProbeReply` is one transport answer; its
rows stay in memory (excluded from every dump), because a leaked row is third-party data (MPI1).
`ReadTransport` and `EscalationTransport` are the seams T-210's multi-role session plugs into
later; tests drive the oracles through fakes. `ProbeLog` and `RevertRecord` are the only things
written to disk: counts, what was left unprobed, and the revert of an escalation that worked.
The budgets themselves (3 swaps, 1 list page, the request cap, the ceiling) live in code in
`stages/authz_probe.py`; there is deliberately no separate budget schema.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.platform import PLATFORM_ID_PATTERN
from autotester.schema.role_account import ROLE_ACCOUNT_ID_PATTERN

ID_PATTERN = r"^[a-z][a-z0-9_-]{0,63}$"
FIELD_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]{0,63}$"
MAX_URL = 190
ID_PLACEHOLDER = "{id}"


def _plain_url(url: str) -> str:
    """A path or http(s) URL with no userinfo, fragment, whitespace, secret placeholder or PII."""
    if not url or len(url) > MAX_URL or "#" in url or "@" in url or "{{" in url:
        raise ValueError("a probe URL must be a plain path or http(s) URL")
    if any(c.isspace() for c in url) or ".." in url.split("?")[0].split("/"):
        raise ValueError("a probe URL must not hold whitespace or '..' segments")
    if not (url.startswith("/") or url.startswith(("http://", "https://"))):
        raise ValueError("a probe URL starts with '/', 'http://' or 'https://'")
    if contains_personal_shape(url):
        raise ValueError("a probe URL looks like personal data")
    return url


class TenantProbe(BaseModel):
    """One list view read as tenant A (the viewer); rows that are not A's are foreign (MP18).

    Two ways to know what is A's: another tenant `owner_role_id` whose own list names the rows
    that must never reach A (the owner reads the SAME `list_url`, one page), or
    `declared_own_count`, the number of rows A owns (the surplus is foreign).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    viewer_role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    list_url: str
    owner_role_id: str | None = Field(default=None, pattern=ROLE_ACCOUNT_ID_PATTERN)
    declared_own_count: int | None = Field(default=None, ge=0, strict=True)
    id_field: str = Field(default="id", pattern=FIELD_PATTERN)
    detail_url: str | None = Field(
        default=None, description="contains `{id}`; read as the viewer with the owner's ids")

    @field_validator("list_url", "detail_url")
    @classmethod
    def _urls_are_plain(cls, url: str | None) -> str | None:
        return None if url is None else _plain_url(url)

    @model_validator(mode="after")
    def _one_way_to_know_what_is_owned(self) -> TenantProbe:
        if (self.owner_role_id is None) == (self.declared_own_count is None):
            raise ValueError("name exactly one of owner_role_id or declared_own_count")
        if self.owner_role_id == self.viewer_role_id:
            raise ValueError("the owner tenant must differ from the viewer")
        if self.detail_url is not None:
            if ID_PLACEHOLDER not in self.detail_url:
                raise ValueError("detail_url must contain {id}")
            if self.owner_role_id is None:
                raise ValueError("id swaps need an owner tenant to take the ids from")
        return self


class RoleAssignControl(BaseModel):
    """A control that assigns a role (a button, a form); at most one attempt is made (MP19)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    url: str = Field(description="where the control lives, as a template")

    @field_validator("url")
    @classmethod
    def _url_is_plain(cls, url: str) -> str:
        return _plain_url(url)


class PrivilegeProbe(BaseModel):
    """Reads captured in a higher role's session, replayed as a lower role, plus role-assigns."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    higher_role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    lower_role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    read_urls: list[str] = Field(default_factory=list, max_length=20)
    controls: list[RoleAssignControl] = Field(default_factory=list, max_length=10)

    @field_validator("read_urls")
    @classmethod
    def _reads_are_plain(cls, urls: list[str]) -> list[str]:
        return [_plain_url(u) for u in urls]

    @model_validator(mode="after")
    def _roles_differ_and_something_to_do(self) -> PrivilegeProbe:
        if self.higher_role_id == self.lower_role_id:
            raise ValueError("the higher and the lower role must differ")
        if not (self.read_urls or self.controls):
            raise ValueError("a privilege probe needs a read or a control")
        return self


class AuthzPlan(BaseModel):
    """Everything planned against ONE platform. The planned count is derived, never typed."""

    model_config = ConfigDict(extra="forbid")

    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    tenant_probes: list[TenantProbe] = Field(default_factory=list, max_length=50)
    privilege_probes: list[PrivilegeProbe] = Field(default_factory=list, max_length=50)
    request_cap: int = Field(default=30, ge=1, le=500, strict=True,
                             description="requests this platform may receive in the run")
    wall_clock_s: float = Field(default=120.0, gt=0, le=3600)
    request_interval_s: float = Field(default=0.25, ge=0, le=10)

    @model_validator(mode="after")
    def _ids_unique_and_nonempty(self) -> AuthzPlan:
        for what, probes in (("tenant", self.tenant_probes), ("privilege", self.privilege_probes)):
            ids = [p.id for p in probes]
            if len(set(ids)) != len(ids):
                raise ValueError(f"duplicate {what} probe id")
        if not (self.tenant_probes or self.privilege_probes):
            raise ValueError("an authz plan needs at least one probe")
        return self


class ProbeReply(BaseModel):
    """One answer. `status` is the final one after redirects; a login redirect reports 401/403.

    `rows` are the records the response held. They exist in memory for the oracle to count and
    are excluded from every dump: a reply cannot be written to disk by accident (MPI1).
    """

    model_config = ConfigDict(extra="forbid")

    status: int = Field(ge=100, le=599)
    rows: list[dict[str, object]] = Field(default_factory=list, exclude=True, repr=False)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


@runtime_checkable
class ReadTransport(Protocol):
    """GET `url` as the named role account. The oracles call nothing else to read."""

    def read(self, role_id: str, url: str) -> ProbeReply: ...


@runtime_checkable
class EscalationTransport(Protocol):
    """The writes of MP19, only ever called when the project's write policy allows them."""

    def can_reach(self, role_id: str, control: RoleAssignControl) -> bool: ...

    def assign(self, role_id: str, control: RoleAssignControl) -> bool:
        """Attempt the role-assign once; True when the app accepted it."""
        ...

    def revert(self, role_id: str, control: RoleAssignControl) -> bool:
        """Undo an accepted assign; True when the app confirms the old role is back."""
        ...


class StopReason(StrEnum):
    """Why something planned was not probed."""

    REQUEST_CAP = "request_cap"
    WALL_CLOCK = "wall_clock"
    SWAP_LIMIT = "swap_limit"
    WRITE_POLICY = "write_policy"
    NO_ESCALATION_TRANSPORT = "no_escalation_transport"
    TRANSPORT_ERROR = "transport_error"
    LIST_STATUS = "list_status"


class UnprobedItem(BaseModel):
    """One planned probe that was not made, named by probe id and kind, never by a value."""

    model_config = ConfigDict(extra="forbid")

    item: str = Field(pattern=r"^[a-z0-9_:-]{1,160}$")
    reason: StopReason


class ProbeLog(BaseModel):
    """What one oracle did on one platform: counts and what it left unprobed (MP20)."""

    model_config = ConfigDict(extra="forbid")

    oracle: OracleName
    platform_id: str = Field(pattern=PLATFORM_ID_PATTERN)
    planned: int = Field(ge=0)
    sent: int = Field(ge=0)
    elapsed_s: float = Field(ge=0)
    findings: int = Field(ge=0)
    unprobed: list[UnprobedItem] = Field(default_factory=list)


class RevertRecord(BaseModel):
    """An escalation that succeeded and what happened to it. `reverted: false` is a P0 follow-up."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    control_id: str = Field(pattern=ID_PATTERN)
    role_id: str = Field(pattern=ROLE_ACCOUNT_ID_PATTERN)
    reverted: bool
    timestamp: str
