"""T-213: the authorisation-probe plan refuses the wrong shapes at load (MP18-MP20, MPI1, MPI4).

The plan holds role ids and URL templates only; a reply's rows never serialise; the transports
are the seams T-210 will plug into.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotester.schema.authz_probe import (
    AuthzPlan,
    EscalationTransport,
    PrivilegeProbe,
    ProbeReply,
    ReadTransport,
    RoleAssignControl,
    TenantProbe,
)

T: dict[str, object] = {"id": "students", "viewer_role_id": "tenant-a",
                        "owner_role_id": "tenant-b", "list_url": "/api/students?page=1"}


def _tenant(**kw: object) -> TenantProbe:
    return TenantProbe(**{**T, **kw})  # type: ignore[arg-type]


def test_a_tenant_probe_names_exactly_one_way_to_know_what_is_owned() -> None:
    assert _tenant().owner_role_id == "tenant-b"
    assert _tenant(owner_role_id=None, declared_own_count=2).declared_own_count == 2
    with pytest.raises(ValidationError):
        _tenant(owner_role_id=None)
    with pytest.raises(ValidationError):
        _tenant(declared_own_count=2)
    with pytest.raises(ValidationError):
        _tenant(owner_role_id="tenant-a")


def test_id_swaps_need_a_placeholder_and_an_owner_tenant() -> None:
    assert _tenant(detail_url="/api/students/{id}").detail_url
    with pytest.raises(ValidationError):
        _tenant(detail_url="/api/students/1")
    with pytest.raises(ValidationError):
        _tenant(owner_role_id=None, declared_own_count=1, detail_url="/api/students/{id}")


@pytest.mark.parametrize("url", [
    "api/students", "/a b", "/x#frag", "https://user@host.test/x", "/x/../y", "/x/{{SECRET:K}}",
    "/mail/someone@school.invalid", "ftp://host.test/x", "/" + "a" * 200, ""])
def test_a_probe_url_that_is_not_plain_is_refused(url: str) -> None:
    with pytest.raises(ValidationError):
        _tenant(list_url=url)
    with pytest.raises(ValidationError):
        RoleAssignControl(id="c", url=url)


def test_a_privilege_probe_needs_two_roles_and_something_to_do() -> None:
    PrivilegeProbe(id="p", higher_role_id="admin", lower_role_id="teacher", read_urls=["/a"])
    for kw in ({"lower_role_id": "admin"}, {"read_urls": []}):
        with pytest.raises(ValidationError):
            PrivilegeProbe(**{"id": "p", "higher_role_id": "admin", "lower_role_id": "teacher",
                              "read_urls": ["/a"], **kw})  # type: ignore[arg-type]


def test_a_plan_needs_a_probe_unique_ids_and_sane_bounds() -> None:
    with pytest.raises(ValidationError):
        AuthzPlan(platform_id="primary")
    with pytest.raises(ValidationError):
        AuthzPlan(platform_id="primary", tenant_probes=[_tenant(), _tenant()])
    for bad in ({"request_cap": 0}, {"request_cap": 501}, {"wall_clock_s": 0},
                {"request_interval_s": -1}, {"surprise": 1}):
        with pytest.raises(ValidationError):
            AuthzPlan(platform_id="primary", tenant_probes=[_tenant()], **bad)  # type: ignore[arg-type]


def test_reply_rows_are_kept_in_memory_and_never_dumped() -> None:
    reply = ProbeReply(status=200, rows=[{"Name": "ZZNAME"}])
    assert reply.ok and reply.rows
    assert "ZZNAME" not in reply.model_dump_json() and "rows" not in reply.model_dump()
    assert "ZZNAME" not in repr(reply)
    assert not ProbeReply(status=403).ok and not ProbeReply(status=302).ok


def test_the_transports_are_runtime_checkable_protocols() -> None:
    class Reader:
        def read(self, role_id: str, url: str) -> ProbeReply:
            return ProbeReply(status=200)

    assert isinstance(Reader(), ReadTransport) and not isinstance(Reader(), EscalationTransport)
    assert not isinstance(object(), ReadTransport)
