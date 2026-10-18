"""T-213 (multi-role-platform.md MP18, MP20, A5): the cross-tenant oracle.

A counting fake app leaks 3 foreign rows to tenant A; the oracle must report them as one P0 data
leak whose evidence holds counts, headers and hashes only (MPI1), stay inside its bounds (3 swaps,
1 list page, the request cap, the wall clock) and name what a bound left unprobed. Fixtures are
synthetic and generic (MPI2); nothing here opens a socket or calls a model.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from authz_fakes import NOW, PII_MARKERS, Scaffold, rows
from cross_role_fakes import FakeClock

from autotester.schema.ai_probe import ProbeRefusal
from autotester.schema.authz_probe import AuthzPlan, ProbeLog, StopReason, TenantProbe
from autotester.schema.multi_role_enums import FindingClass, OracleName, Priority
from autotester.stages import oracle_tenant
from autotester.stages.finding_priority import priority_for

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
LIST = "/api/students?page=1"


def _probe(**kw: object) -> TenantProbe:
    fields: dict[str, object] = {"id": "students", "viewer_role_id": "tenant-a",
                                 "owner_role_id": "tenant-b", "list_url": LIST}
    return TenantProbe(**{**fields, **kw})  # type: ignore[arg-type]


def _plan(*probes: TenantProbe, **kw: object) -> AuthzPlan:
    return AuthzPlan(platform_id="primary", tenant_probes=list(probes) or [_probe()],
                     request_interval_s=0, **kw)  # type: ignore[arg-type]


def _leaky(sc: Scaffold, foreign: int = 3, own: int = 2) -> None:
    """Tenant A's list holds its own rows plus `foreign` of tenant B's (the planted leak)."""
    sc.app.serve("tenant-a", LIST, data=rows("a", own) + rows("b", foreign))
    sc.app.serve("tenant-b", LIST, data=rows("b", max(foreign, 3)))


def _run(sc: Scaffold, clock: FakeClock | None = None, port: object | None = None):
    fc = clock or FakeClock()
    return oracle_tenant.run_tenant_pass(sc.context(port), clock=fc.now, sleep=fc.sleep, now=NOW)


def _log(sc: Scaffold) -> ProbeLog:
    path = sc.run_dir / "authz" / "tenant_log.json"
    return ProbeLog.model_validate_json(path.read_text("utf-8"))


def _refusals(sc: Scaffold) -> list[ProbeRefusal]:
    path = sc.root / "projects" / "demo" / "authz" / "refusals.jsonl"
    return [ProbeRefusal.model_validate_json(x) for x in path.read_text("utf-8").splitlines()] \
        if path.exists() else []


@pytest.fixture
def sc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Scaffold:
    return Scaffold(tmp_path, monkeypatch)


# --- MP18: rows visible to A that are not A's are counted, P0, with LeakEvidence ---------------

def test_mp18_fixture_leaking_three_foreign_rows_is_one_p0_data_leak(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan())
    sc.grant(5)
    findings = _run(sc)
    assert len(findings) == 1
    f = findings[0]
    assert f.finding_class is FindingClass.DATA_LEAK
    assert priority_for(f.finding_class) is Priority.P0
    assert f.count == 3 and f.leak_evidence is not None
    assert f.leak_evidence.foreign_row_count == 3
    assert f.leak_evidence.field_names == ["id", "Name", "Email"]
    assert len(f.leak_evidence.hashed_ids) == 3
    assert f.role == "tenant-a" and f.oracle is OracleName.TENANT
    assert f.url_template == "/api/students?page={value}"


def test_mp18_a_clean_app_reports_nothing(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 2))
    sc.app.serve("tenant-b", LIST, data=rows("b", 3))
    sc.plan(_plan())
    sc.grant(5)
    assert _run(sc) == []
    assert _log(sc).findings == 0


def test_mp18_no_foreign_value_reaches_disk_a_log_or_the_finding(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan(_probe(detail_url="/api/students/{id}")))
    sc.app.serve("tenant-a", "/api/students/sid-b-1", data=rows("b", 1))
    sc.grant(5)
    findings = _run(sc)
    text = sc.tree_text() + json.dumps([f.model_dump(mode="json") for f in findings])
    assert findings and sc.files("*.json")
    for marker in (*PII_MARKERS, "school.invalid", "sid-b-1", "sid-b-2", "sid-b-3"):
        assert marker not in text
    stored = sc.files("authz-tenant-students.json")
    assert len(stored) == 1


def test_mp18_declared_own_count_mode_counts_the_surplus_and_keeps_no_id(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 5))
    sc.plan(_plan(_probe(owner_role_id=None, declared_own_count=2)))
    sc.grant(5)
    f = _run(sc)[0]
    assert f.count == 3 and f.leak_evidence is not None
    assert f.leak_evidence.hashed_ids == [] and f.leak_evidence.ids_withheld_reason is None
    assert len(sc.app.reads) == 1


def test_mp18_a_list_within_the_declared_count_is_clean(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 2))
    sc.plan(_plan(_probe(owner_role_id=None, declared_own_count=2)))
    sc.grant(5)
    assert _run(sc) == []


def test_mp18_id_swap_reads_that_leak_count_once_with_the_list_rows(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 2) + rows("b", 1))
    sc.app.serve("tenant-b", LIST, data=rows("b", 3))
    for n in (1, 2, 3):
        sc.app.serve("tenant-a", f"/api/students/sid-b-{n}", data=rows("b", 1, start=n))
    sc.plan(_plan(_probe(detail_url="/api/students/{id}")))
    sc.grant(5)
    f = _run(sc)[0]
    assert f.count == 3  # b1 seen twice (list + swap) counts once; b2, b3 only by swap
    assert [p for _, p in sc.app.reads].count("/api/students/sid-b-1") == 1


def test_mp18_a_correctly_refused_swap_is_not_a_leak(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 2))
    sc.app.serve("tenant-b", LIST, data=rows("b", 3))
    sc.plan(_plan(_probe(detail_url="/api/students/{id}")))
    sc.grant(5)
    assert _run(sc) == []
    assert sum(1 for _, p in sc.app.reads if p.startswith("/api/students/")) == 3


def test_mp18_ids_are_hashed_at_most_five_and_withheld_without_the_key(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    keyed = Scaffold(tmp_path / "k", monkeypatch)
    _leaky(keyed, foreign=7)
    keyed.plan(_plan())
    keyed.grant(5)
    ev = _run(keyed)[0].leak_evidence
    assert ev is not None and ev.foreign_row_count == 7 and len(ev.hashed_ids) == 5
    bare = Scaffold(tmp_path / "n", monkeypatch, key=False)
    _leaky(bare, foreign=7)
    bare.plan(_plan())
    bare.grant(5)
    f = _run(bare)[0]
    assert f.count == 7 and f.leak_evidence is not None
    assert f.leak_evidence.hashed_ids == [] and f.leak_evidence.ids_withheld_reason == "key_missing"


# --- cycle 1: a non-2xx list read is "not probed", never "clean" -------------------------------

def test_mp18_an_owner_list_that_returns_401_names_the_view_unprobed_never_clean(
        sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 2) + rows("b", 3))
    sc.app.serve("tenant-b", LIST, status=401)
    sc.plan(_plan())
    sc.grant(10)
    assert _run(sc) == []
    unprobed = _log(sc).unprobed
    assert unprobed, "a 401 on the owner list must not read as a clean view"
    assert {u.reason for u in unprobed} == {StopReason.LIST_STATUS}
    assert any(u.item.endswith("owner_list") for u in unprobed)


def test_mp18_a_viewer_list_that_returns_403_names_the_view_unprobed(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, status=403)
    sc.app.serve("tenant-b", LIST, data=rows("b", 3))
    sc.plan(_plan())
    sc.grant(10)
    assert _run(sc) == []
    unprobed = _log(sc).unprobed
    assert unprobed and unprobed[0].reason is StopReason.LIST_STATUS


# --- MP20: bounded and deterministic ---------------------------------------------------------

def test_mp20_at_most_three_swaps_and_the_rest_is_named_unprobed(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 1))
    sc.app.serve("tenant-b", LIST, data=rows("b", 5))
    sc.plan(_plan(_probe(detail_url="/api/students/{id}")))
    sc.grant(5)
    _run(sc)
    swaps = [p for _, p in sc.app.reads if p.startswith("/api/students/")]
    assert len(swaps) == 3 and sum(1 for _, p in sc.app.reads if p == LIST) == 2
    unprobed = _log(sc).unprobed
    assert [(u.item, u.reason) for u in unprobed] == [
        ("tenant:students:swap_beyond_3", StopReason.SWAP_LIMIT)]


def test_mp20_one_list_page_per_view(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan())
    sc.grant(5)
    _run(sc)
    assert [p for r, p in sc.app.reads if r == "tenant-a"] == [LIST]


def test_mp20_the_request_cap_stops_the_pass_and_names_what_was_left(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan(_probe(detail_url="/api/students/{id}"), request_cap=3))
    sc.grant(5)
    _run(sc)
    assert len(sc.app.reads) == 3
    log = _log(sc)
    assert log.sent == 3 and log.planned == 5
    assert [u.item for u in log.unprobed] == ["tenant:students:swap_2", "tenant:students:swap_3"]
    assert {u.reason for u in log.unprobed} == {StopReason.REQUEST_CAP}


def test_mp20_a_second_view_after_the_cap_is_wholly_unprobed(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan(_probe(), _probe(id="staff", list_url="/api/staff?page=1"), request_cap=2))
    sc.grant(5)
    _run(sc)
    assert len(sc.app.reads) == 2
    assert {u.item for u in _log(sc).unprobed} == {
        "tenant:staff:list", "tenant:staff:owner_list"}


def test_mp20_the_wall_clock_stops_the_pass_and_the_pacing_is_applied(sc: Scaffold) -> None:
    _leaky(sc)
    probe = _probe(detail_url="/api/students/{id}")
    sc.plan(AuthzPlan(platform_id="primary", tenant_probes=[probe],
                      request_interval_s=1.0, wall_clock_s=2.5))
    sc.grant(5)
    clock = FakeClock()
    _run(sc, clock)
    assert clock.sleeps == [1.0, 1.0, 1.0]  # paced between requests, never before the first
    assert len(sc.app.reads) == 4
    assert [(u.item, u.reason) for u in _log(sc).unprobed] == [
        ("tenant:students:swap_3", StopReason.WALL_CLOCK)]


def test_mp20_no_provider_is_called_or_even_importable_from_the_authz_modules(
        sc: Scaffold, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.providers.base import Provider

    calls: list[str] = []
    for name in ("see_video", "act", "judge"):
        monkeypatch.setattr(Provider, name, lambda *a, _n=name, **k: calls.append(_n))
    _leaky(sc)
    sc.plan(_plan())
    sc.grant(5)
    _run(sc)
    assert calls == []
    for module in ("oracle_tenant", "oracle_privilege", "authz_probe"):
        tree = ast.parse((SRC / "stages" / f"{module}.py").read_text(encoding="utf-8"))
        imported = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not any("providers" in m or "ai_judge" in m for m in imported), module


def test_mp20_a_transport_failure_is_unprobed_and_its_message_is_never_kept(sc: Scaffold) -> None:
    sc.app.read_raises = True
    sc.plan(_plan())
    sc.grant(5)
    assert _run(sc) == []
    log = _log(sc)
    assert {u.reason for u in log.unprobed} == {StopReason.TRANSPORT_ERROR}
    assert "ZZNAME" not in sc.tree_text()
