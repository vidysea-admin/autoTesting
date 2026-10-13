"""TF3 (team-foundation.md): routers register from one ordered list; the stubs expose nothing.

The golden is the route table (methods, path, endpoint) as it stood before the router list
existed. Later units add routes, so the check is "the golden is an ordered subsequence of the
live table", never full equality.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from autotester.ui import routers
from autotester.ui.app import app

GOLDEN = Path(__file__).parent / "golden" / "ui_routes.json"
APP_PY = Path(__file__).resolve().parents[1] / "src" / "autotester" / "ui" / "app.py"


def route_table(target: FastAPI) -> list[list[str]]:
    """(methods, path, endpoint) of every app route, in registration order."""
    def flat(routes):
        for route in routes:
            inner = getattr(route, "original_router", None)
            yield from flat(inner.routes) if inner is not None else [route]
    rows = []
    for route in flat(target.routes):
        endpoint = getattr(route, "endpoint", None)
        name = f"{endpoint.__module__}.{endpoint.__qualname__}" if endpoint else ""
        if name.startswith("autotester."):
            rows.append([",".join(sorted(getattr(route, "methods", None) or [])),
                         getattr(route, "path", ""), name])
    return rows


def is_ordered_subsequence(wanted: list[list[str]], actual: list[list[str]]) -> bool:
    remaining = iter(actual)
    return all(any(row == candidate for candidate in remaining) for row in wanted)


def test_existing_routes_keep_their_order() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert golden and is_ordered_subsequence(golden, route_table(app))


def test_stubs_are_registered_and_add_zero_routes() -> None:
    assert set(routers.STUBS) == {
        "team_run", "inbox", "profile", "video_review", "video_portal",
        "access_requests"}
    for name, stub in routers.STUBS.items():
        assert stub in routers.ROUTERS, name
        assert stub.routes == [], name
    stubs_only = FastAPI()
    for stub in routers.STUBS.values():
        stubs_only.include_router(stub)
    assert route_table(stubs_only) == []


def test_a_router_appended_to_the_list_is_reachable_without_editing_app_py(monkeypatch) -> None:
    throwaway = APIRouter()

    @throwaway.get("/throwaway-t205-probe")
    def probe() -> dict[str, bool]:
        return {"ok": True}

    monkeypatch.setattr(routers, "ROUTERS", (*routers.ROUTERS, throwaway))
    fresh = FastAPI()
    routers.include_all(fresh)
    assert TestClient(fresh).get("/throwaway-t205-probe").json() == {"ok": True}


def test_app_py_registers_no_router_itself_and_stays_under_the_cap() -> None:
    text = APP_PY.read_text(encoding="utf-8")
    assert "include_router" not in text
    assert len(text.splitlines()) <= 300
