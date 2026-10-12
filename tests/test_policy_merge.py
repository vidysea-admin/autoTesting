"""TF4 (team-foundation.md): units declare their own route policy; `auth/policy.py` merges them
and fails loudly on a duplicate route, an unknown permission key, a stray `public`, or a route
that does not exist. G1 adds the merge only: the catalogue and the public set come from the
caller (T-204 owns the catalogue), so no key is invented here."""

from __future__ import annotations

import pytest

from autotester.auth.policy import PUBLIC, PolicyError, merge_route_policies

CATALOGUE = {"project.view", "project.run", "schedule.manage"}
PUBLIC_SET = {"GET /auth/login"}
ROUTES = {"GET /projects/{slug}/schedule", "POST /projects/{slug}/run", "GET /auth/login"}
UNIT_A = {"POST /projects/{slug}/run": ("project.run", "project")}
UNIT_B = {"GET /projects/{slug}/schedule": ("schedule.manage", "project"),
          "GET /auth/login": PUBLIC}


def merge(units, **kw):
    return merge_route_policies(units, catalogue=CATALOGUE, public_routes=PUBLIC_SET,
                                routes=kw.pop("routes", ROUTES), **kw)


def test_two_unit_dicts_merge_into_one_table() -> None:
    assert merge({"a": UNIT_A, "b": UNIT_B}) == {**UNIT_A, **UNIT_B}


def test_the_merge_does_not_depend_on_the_order_units_are_given() -> None:
    first = merge({"a": UNIT_A, "b": UNIT_B})
    second = merge({"b": UNIT_B, "a": UNIT_A})
    assert list(first) == list(second)


def test_stubs_contribute_empty_dicts() -> None:
    assert merge({"schedule": {}, "inbox": {}, "a": UNIT_A}) == UNIT_A


def test_a_route_claimed_by_two_units_fails_naming_both() -> None:
    with pytest.raises(PolicyError, match=r"duplicate route 'POST /projects/\{slug\}/run'.*a.*c"):
        merge({"a": UNIT_A, "c": {"POST /projects/{slug}/run": ("project.view", "project")}})


def test_a_key_outside_the_catalogue_fails_naming_unit_and_key() -> None:
    with pytest.raises(PolicyError, match=r"b: .*'schedule.invent'.*closed catalogue"):
        merge({"b": {"GET /projects/{slug}/schedule": ("schedule.invent", "project")}})


def test_public_outside_the_closed_set_fails() -> None:
    with pytest.raises(PolicyError, match=r"b: .*marked public.*AU16"):
        merge({"b": {"POST /projects/{slug}/run": PUBLIC}})


def test_a_route_that_does_not_exist_fails() -> None:
    with pytest.raises(PolicyError, match=r"a: .*does not exist.*'GET /nowhere'"):
        merge({"a": {"GET /nowhere": ("project.view", "project")}})


def test_a_malformed_grant_fails() -> None:
    with pytest.raises(PolicyError, match="must be 'public' or"):
        merge({"a": {"POST /projects/{slug}/run": "project.run"}})  # type: ignore[dict-item]
