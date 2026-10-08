"""Fail-closed owner/policy assembly and the ordered router registration seam (TF3/TF4)."""

import pytest
from fastapi import APIRouter, FastAPI

from autotester.auth import policy
from autotester.schema.auth import CATALOGUE, PermissionKey, RouteRule
from autotester.ui import routers
from autotester.ui.app import app


def test_policy_merge_is_deterministic_and_refuses_duplicate_owners() -> None:
    a = {("GET", "/a"): RouteRule(kind="key", key=PermissionKey.SETTINGS_MANAGE)}
    b = {("POST", "/b"): RouteRule(kind="project", key=PermissionKey.PROJECT_RUN)}
    assert list(policy.merge_policies([("a", a), ("b", b)])) == [
        ("GET", "/a"), ("POST", "/b")]
    with pytest.raises(ValueError, match=r"duplicate.*a.*b"):
        policy.merge_policies([("a", a), ("b", a)])


@pytest.mark.parametrize("rule,reason", [
    (RouteRule.model_construct(kind="key", key="unknown.permission"), "unknown permission"),
    (RouteRule(kind="public"), "outside AU16"),
    (RouteRule(kind="project"), "missing permission"),
])
def test_policy_merge_rejects_unknown_or_unsafe_declaration(rule, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        policy.merge_policies([("offending-unit", {("GET", "/unsafe"): rule})])


def test_policy_assembly_rejects_nonexistent_route_before_serving() -> None:
    rule = RouteRule(kind="key", key=PermissionKey.SETTINGS_MANAGE)
    with pytest.raises(ValueError, match=r"nonexistent.*missing-route"):
        policy.assemble(app, [("missing-owner", {("GET", "/missing-route"): rule})])


def test_group10_stubs_are_empty_and_router_hook_needs_no_app_edit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert len(routers.POLICY_MODULES) == 8
    assert all(not module.router.routes and not module.ROUTE_POLICY
               for module in routers.POLICY_MODULES)
    extra = APIRouter()

    @extra.get("/fixture-hook")
    def hook() -> dict:
        return {"ok": True}

    monkeypatch.setattr(routers, "ROUTERS", (*routers.ROUTERS, extra))
    probe = FastAPI()
    routers.include_all(probe)
    assert any(getattr(route, "original_router", None) is extra for route in probe.routes)
    assert set(CATALOGUE) == set(PermissionKey)


def test_legacy_router_order_remains_exact() -> None:
    expected = ("routes_cases", "routes_project_edit", "routes_runs", "routes_report",
                "routes_video", "routes_flow_diagram", "routes_crawls", "routes_crawl_login",
                "routes_credentials", "routes_crawl_approval", "routes_settings", "routes_learn",
                "routes_sources", "routes_product_map", "routes_issues", "routes_live",
                "routes_catalog")
    legacy = routers.ROUTERS[2:19]
    assert tuple(router.routes[0].endpoint.__module__.rsplit(".", 1)[-1]
                 for router in legacy) == expected
