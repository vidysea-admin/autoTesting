"""T-213 (multi-role-platform.md A5, MP20): the gate in front of the authz probes.

The planned probe count must be covered by a signed `RunApproval` (`core/consent.py::
require_project_approval`), a code-side ceiling refuses an oversized plan, and a refusal sends
nothing and appends one non-secret line to `refusals.jsonl`. Exercised through the tenant oracle;
the gate is shared (`stages/authz_probe.py`) and the privilege oracle is covered in its own file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from authz_fakes import NOW, NoReadPort, ReadOnlyApp, Scaffold, rows
from cross_role_fakes import FakeClock

from autotester.core.consent import ApprovalRequired
from autotester.schema.ai_probe import ProbeRefusal
from autotester.schema.authz_probe import AuthzPlan, TenantProbe
from autotester.schema.enums import WritePolicy
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.oracle_context import OracleState
from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.stages import oracle_tenant
from autotester.stages.adversarial import AdversarialBlocked, ProbeCeilingExceeded
from autotester.stages.authz_probe import (
    PROBE_CEILING,
    AuthzPlanMissing,
    NoProbeTransport,
    plan_size,
)
from autotester.stages.oracle_registry import run_oracles

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
LIST = "/api/students?page=1"


def _probe(**kw: object) -> TenantProbe:
    fields: dict[str, object] = {"id": "students", "viewer_role_id": "tenant-a",
                                 "owner_role_id": "tenant-b", "list_url": LIST}
    return TenantProbe(**{**fields, **kw})  # type: ignore[arg-type]


def _plan(*probes: TenantProbe, **kw: object) -> AuthzPlan:
    return AuthzPlan(platform_id="primary", tenant_probes=list(probes) or [_probe()],
                     request_interval_s=0, **kw)  # type: ignore[arg-type]


def _leaky(sc: Scaffold) -> None:
    sc.app.serve("tenant-a", LIST, data=rows("a", 2) + rows("b", 3))
    sc.app.serve("tenant-b", LIST, data=rows("b", 3))


def _run(sc: Scaffold, port: object | None = None):
    fc = FakeClock()
    return oracle_tenant.run_tenant_pass(sc.context(port), clock=fc.now, sleep=fc.sleep, now=NOW)


def _refusals(sc: Scaffold) -> list[ProbeRefusal]:
    path = sc.root / "projects" / "demo" / "authz" / "refusals.jsonl"
    if not path.exists():
        return []
    return [ProbeRefusal.model_validate_json(x) for x in path.read_text("utf-8").splitlines()]


@pytest.fixture
def sc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Scaffold:
    return Scaffold(tmp_path, monkeypatch)


# --- A5: the planned count is covered by a signed approval; the ceiling; the refusal -----------

def test_a5_an_approval_for_two_probes_against_a_plan_of_three_is_refused_with_nothing_sent(
        sc: Scaffold) -> None:
    _leaky(sc)
    plan = _plan(*(_probe(id=name, owner_role_id=None, declared_own_count=1)
                   for name in ("one", "two", "three")))
    assert plan_size(plan) == 3
    sc.plan(plan)
    sc.grant(2)
    with pytest.raises(ApprovalRequired):
        _run(sc)
    assert sc.app.calls == 0
    lines = _refusals(sc)
    assert len(lines) == 1 and lines[0].requested_probes == 3
    assert "probes 3 > approved 2" in lines[0].reason
    assert not (SRC / "schema" / "probe_budget.py").exists()
    assert "ZZNAME" not in sc.tree_text()


def test_a5_no_approval_at_all_is_refused_and_logged(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan())
    with pytest.raises(ApprovalRequired):
        _run(sc)
    assert sc.app.calls == 0 and len(_refusals(sc)) == 1


def test_a5_the_code_ceiling_refuses_an_oversized_plan_whatever_the_approval(sc: Scaffold) -> None:
    plan = _plan(*(_probe(id=f"v{n}", list_url=f"/api/v{n}?page=1") for n in range(31)))
    assert plan_size(plan) == 62 > PROBE_CEILING
    sc.plan(plan)
    sc.grant(10_000)
    with pytest.raises(ProbeCeilingExceeded):
        _run(sc)
    assert sc.app.calls == 0 and len(_refusals(sc)) == 1


def test_a5_a_planned_url_outside_the_allowed_domains_is_refused(sc: Scaffold) -> None:
    sc.plan(_plan(_probe(list_url="https://elsewhere.example/api/students?page=1")))
    sc.grant(5)
    with pytest.raises(AdversarialBlocked):
        _run(sc)
    assert sc.app.calls == 0 and len(_refusals(sc)) == 1


def test_a5_an_approval_for_one_platform_cannot_be_spent_on_a_sibling_platforms_host(
        sc: Scaffold) -> None:
    """Cycle 1 (coordinator A): scope is the PROBED platform's own hosts, not the whole project."""
    sc.store.save_project(Project(
        slug="demo", name="Demo", base_url="https://app.test/",
        allowed_domains=["app.test", "other.test"], write_policy=WritePolicy.ALLOW_WRITES,
        platforms=[Platform(id="primary", name="Primary", base_url="https://app.test/",
                            allowed_domains=["app.test"]),
                   Platform(id="other", name="Other", base_url="https://other.test/",
                            allowed_domains=["other.test"])]))
    sc.app.serve("tenant-a", "/admin/users", data=rows("a", 2) + rows("x", 3))
    sc.plan(_plan(_probe(list_url="https://other.test/admin/users", owner_role_id=None,
                         declared_own_count=2)))
    sc.grant(5)  # signed for https://app.test/ only
    with pytest.raises(AdversarialBlocked, match="primary"):
        _run(sc)
    assert sc.app.calls == 0 and sc.app.reads == []
    assert len(_refusals(sc)) == 1


def test_a5_a_platform_pinned_to_exact_hosts_refuses_its_own_subdomain(sc: Scaffold) -> None:
    sc.store.save_project(Project(
        slug="demo", name="Demo", base_url="https://app.test/", allowed_domains=["app.test"],
        write_policy=WritePolicy.ALLOW_WRITES,
        platforms=[Platform(id="primary", name="Primary", base_url="https://app.test/",
                            allowed_domains=["app.test"], include_subdomains=False)]))
    sc.plan(_plan(_probe(list_url="https://api.app.test/students", owner_role_id=None,
                         declared_own_count=1)))
    sc.grant(5)
    with pytest.raises(AdversarialBlocked):
        _run(sc)
    assert sc.app.calls == 0


def test_a5_a_production_project_accepts_only_a_human_production_approval(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prod = Scaffold(tmp_path, monkeypatch, production=True)
    _leaky(prod)
    prod.plan(_plan())
    prod.grant(5, production=False)
    with pytest.raises(ApprovalRequired, match="production"):
        _run(prod)
    assert prod.app.calls == 0
    prod.grant(5, production=True)
    assert len(_run(prod)) == 1


def test_a5_a_covered_plan_runs(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan())
    sc.grant(2)
    assert len(_run(sc)) == 1 and _refusals(sc) == []


# --- the registry entry point ----------------------------------------------------------------

def test_registry_runs_the_real_module_and_reports_an_unconfigured_one_as_errored(
        sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan())
    sc.grant(5)
    summary, found = run_oracles(sc.context(), [OracleName.TENANT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.TENANT)
    assert status.state is OracleState.RAN and status.finding_count == 1 and len(found) == 1


def test_a_missing_plan_or_a_port_that_cannot_read_is_an_error_not_a_silent_pass(
        sc: Scaffold) -> None:
    with pytest.raises(AuthzPlanMissing):
        oracle_tenant.run(sc.context())
    sc.plan(_plan())
    with pytest.raises(NoProbeTransport):
        oracle_tenant.run(sc.context(port=NoReadPort()))
    summary, _ = run_oracles(sc.context(), [OracleName.TENANT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.TENANT)
    assert status.state is OracleState.ERRORED


def test_a_port_that_only_reads_is_enough_for_the_tenant_oracle(sc: Scaffold) -> None:
    _leaky(sc)
    sc.plan(_plan())
    sc.grant(5)
    assert len(_run(sc, port=ReadOnlyApp(sc.app))) == 1
