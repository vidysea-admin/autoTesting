"""Merge each unit's own `ROUTE_POLICY` into the one central route-policy table (TF4, AU12/AU14).

One job: let every unit declare the routes it adds in a module-level dict of its own, and fold
them into the single table the default-deny gate and the AU14 enumeration test walk, failing
loudly (never silently) when the declarations disagree. No unit edits a shared table, so units
cannot collide, and none can invent a permission key (R63): a key must be in the closed
catalogue (`qa/contracts/auth.md`), passed in by whoever owns that catalogue.

A unit dict maps `"<METHOD> <path template>"` to the string `public` (only for a route in
AU16's closed public set) or to `(permission key, resource resolver name)`. The merge fails
with a `PolicyError` naming the offender on: a route claimed by two units; a permission key not
in the catalogue; `public` outside the public set; a route that does not exist. The Group 10
stubs contribute empty dicts. Pure functions: no import-time side effect of their own.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping

PUBLIC = "public"
RoutePolicy = Mapping[str, "str | tuple[str, str]"]


class PolicyError(ValueError):
    """The unit policies cannot be merged; the message names the unit and the route."""


def _check_entry(unit: str, route: str, grant: str | tuple[str, str], *,
                 catalogue: Collection[str], public_routes: Collection[str],
                 routes: Collection[str] | None) -> None:
    if routes is not None and route not in routes:
        raise PolicyError(f"{unit}: policy names a route that does not exist: {route!r}")
    if grant == PUBLIC:
        if route not in public_routes:
            raise PolicyError(f"{unit}: {route!r} is marked public but is not in the closed "
                              "public set (auth.md AU16)")
        return
    if not isinstance(grant, tuple) or len(grant) != 2:
        raise PolicyError(f"{unit}: {route!r} must be 'public' or (permission key, resolver)")
    if grant[0] not in catalogue:
        raise PolicyError(f"{unit}: {route!r} uses permission key {grant[0]!r}, which is not "
                          "in the closed catalogue (R63: a unit cannot invent a key)")


def merge_route_policies(
    units: Mapping[str, RoutePolicy], *, catalogue: Collection[str],
    public_routes: Collection[str], routes: Collection[str] | None = None,
) -> dict[str, str | tuple[str, str]]:
    """The central table: every unit's routes, deterministically (units in name order).

    `routes` is the set of `"<METHOD> <path>"` the app really serves; when given, a policy
    row for a route outside it is an error. Raises `PolicyError`; never last-wins."""
    table: dict[str, str | tuple[str, str]] = {}
    owner: dict[str, str] = {}
    for unit in sorted(units):
        for route, grant in units[unit].items():
            if route in table:
                raise PolicyError(f"duplicate route {route!r}: claimed by {owner[route]} "
                                  f"and {unit}")
            _check_entry(unit, route, grant, catalogue=catalogue, public_routes=public_routes,
                         routes=routes)
            table[route], owner[route] = grant, unit
    return table
