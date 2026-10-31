"""One auth-store contract suite, two backends (mongo-store U6b, M29/M30): every test runs on
SQLite and on Mongo (the `fake_mongo` double) through the unchanged business modules, so parity
is proven by running the same assertions: users, groups, sessions, grants, first-admin and claim
races, the last-admin guard, rollback of a refused change, and hash / token containment."""

from __future__ import annotations

import hashlib
import re
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD
from auth_store_backends import BACKENDS, AuthEnv, auth_env

from autotester.auth import access, accounts, groups, sessions
from autotester.auth.db import LastAdmin, NotAllowed
from autotester.auth.store import auth_store
from autotester.auth.store_mongo import reset_auth_store
from autotester.schema.auth import ProjectRelation

OTHER = "dev@team.test"

@pytest.fixture(params=BACKENDS)
def env(request: pytest.FixtureRequest, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> Iterator[AuthEnv]:
    yield from auth_env(request.param, tmp_path, monkeypatch)

def seed_id(seed: str) -> int:
    return next(g.id for g in groups.list_groups() if g.seed == seed)

def race(jobs: list) -> list:
    barrier = threading.Barrier(len(jobs))
    out: list = [None] * len(jobs)

    def go(i: int, job) -> None:
        barrier.wait()
        try:
            out[i] = ("ok", job())
        except Exception as exc:
            out[i] = ("err", exc)

    threads = [threading.Thread(target=go, args=(i, j)) for i, j in enumerate(jobs)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return out

def test_reading_a_missing_store_creates_nothing(env: AuthEnv) -> None:
    assert sessions.resolve_session("a" * 40) is None
    sessions.end_session("a" * 40)
    assert not auth_store().exists() and env.nothing_written()

def test_round_trip_users_groups_sessions(env: AuthEnv) -> None:
    admin = accounts.signup(ADMIN, PASSWORD)
    other = accounts.signup(OTHER, PASSWORD)
    assert admin.groups == ["Admin/CEO"] and other.groups == []
    accounts.set_user_groups(other.id, [seed_id("developer")])
    token = sessions.create_session(other.id)
    assert env.digests() == [hashlib.sha256(token.encode()).hexdigest()]
    assert token not in env.dump()
    principal = sessions.resolve_session(token)
    assert principal is not None and principal.email == OTHER
    assert "project.create" in principal.permissions
    accounts.set_disabled(other.id, True)
    assert sessions.resolve_session(token) is None
    assert accounts.authenticate(OTHER, PASSWORD) is None
    assert accounts.authenticate(ADMIN, PASSWORD).id == admin.id
    sessions.end_session(token)

def test_signup_waiting_approve_decline(env: AuthEnv) -> None:
    admin = accounts.signup("  Admin@Team.TEST ", PASSWORD)
    assert admin.email == ADMIN and admin.groups == ["Admin/CEO"]
    with pytest.raises(accounts.AccountError, match="already exists"):
        accounts.signup(ADMIN, PASSWORD)
    one = accounts.signup("one@team.test", PASSWORD)
    two = accounts.signup("two@team.test", PASSWORD)
    assert [u.email for u in accounts.list_waiting()] == ["one@team.test", "two@team.test"]
    accounts.approve_waiting(one.id, seed_id("tester"))
    assert accounts.get_user(one.id).groups == ["Tester"]
    with pytest.raises(accounts.AccountError, match="not waiting"):
        accounts.approve_waiting(one.id, seed_id("developer"))
    accounts.decline_waiting(two.id)
    assert accounts.get_user(two.id).disabled and accounts.list_waiting() == []
    assert [u.email for u in accounts.list_users()] == [ADMIN, "one@team.test", "two@team.test"]
    assert accounts.find_user(" ONE@team.test ").id == one.id

def test_password_paths_and_account_edits(env: AuthEnv) -> None:
    admin = accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup(OTHER, PASSWORD)
    assert accounts.authenticate(OTHER, "wrong-password-xyz") is None
    assert accounts.authenticate("nobody@team.test", PASSWORD) is None
    token = sessions.create_session(user.id)
    accounts.reset_password(user.id, "a-brand-new-password")
    assert sessions.resolve_session(token) is None  # every session of the account is revoked
    assert accounts.authenticate(OTHER, PASSWORD) is None
    assert accounts.authenticate(OTHER, "a-brand-new-password").id == user.id
    accounts.set_display_name(user.id, "  Dev   Person ")
    assert accounts.get_user(user.id).display_name == "Dev Person"
    with pytest.raises(accounts.AccountError, match="no such account"):
        accounts.set_display_name(9999, "x")
    assert accounts.get_user(admin.id).display_name == ""

def test_generation_is_stable_and_ids_are_integers(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup(OTHER, PASSWORD)
    before = accounts.get_user(user.id)
    assert isinstance(before.id, int) and re.fullmatch(r"[0-9a-f]{32}", before.generation)
    accounts.reset_password(user.id, "another-password-1")
    accounts.set_disabled(user.id, True)
    accounts.set_user_groups(user.id, [seed_id("tester")])
    assert accounts.get_user(user.id).generation == before.generation

def test_delete_user_takes_sessions_and_grants_with_it(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup(OTHER, PASSWORD)
    token = sessions.create_session(user.id)
    access.set_owner("proj-a", user.id)
    access.set_relation("proj-b", user.id, ProjectRelation.SHARED, True)
    accounts.delete_user(user.id)
    assert accounts.get_user(user.id) is None and sessions.resolve_session(token) is None
    assert access.resource_for("proj-a").owner_email is None
    assert access.resource_for("proj-b").shared_with == frozenset()
    assert env.digests() == [] and "proj-" not in env.dump()  # no orphan grant stays behind
    with pytest.raises(accounts.AccountError, match="no such account"):
        accounts.delete_user(user.id)

def test_groups_create_update_delete(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    member = accounts.signup(OTHER, PASSWORD)
    made = groups.create_group("  QA   Leads ", ["report.view@all", "project.create"])
    assert made.name == "QA Leads" and made.seed is None
    assert made.permissions == ["project.create", "report.view@all"] and made.member_ids == []
    with pytest.raises(groups.GroupError, match="already exists"):
        groups.create_group("QA Leads", [])
    with pytest.raises(groups.GroupError, match="unknown permission"):
        groups.create_group("Bad", ["not.a.key"])
    renamed = groups.update_group(made.id, "QA", ["live.view"], member_ids=[member.id])
    assert (renamed.name, renamed.permissions, renamed.member_ids) == ("QA", ["live.view"],
                                                                       [member.id])
    assert accounts.get_user(member.id).groups == ["QA"]
    with pytest.raises(groups.GroupError, match="unknown member"):
        groups.update_group(made.id, "QA", [], member_ids=[member.id, 9999])
    assert groups.get_group(made.id).member_ids == [member.id]  # the refused edit changed nothing
    with pytest.raises(groups.GroupError, match="already exists"):
        groups.update_group(made.id, "Tester", [])
    assert groups.delete_group(made.id) == 1
    assert accounts.get_user(member.id).groups == [] and groups.get_group(made.id) is None
    with pytest.raises(groups.GroupError, match="no such group"):
        groups.delete_group(made.id)
    assert [g.seed for g in groups.list_groups()] == ["admin", "sub-admin", "developer", "tester"]

def test_project_grants_owner_assigned_shared(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    a, b = accounts.signup("a@team.test", PASSWORD), accounts.signup("b@team.test", PASSWORD)
    assert access.resource_for("p1").owner_email is None
    access.set_owner("p1", a.id)
    access.set_owner("p1", b.id)  # one owner only: the creator replaced
    access.set_relation("p1", a.id, ProjectRelation.ASSIGNED, True)
    access.set_relation("p1", a.id, ProjectRelation.ASSIGNED, True)  # idempotent
    access.set_relation("p1", b.id, ProjectRelation.SHARED, True)
    res = access.resource_for("p1")
    assert (res.owner_email, res.assignees, res.shared_with) == (
        "b@team.test", frozenset({"a@team.test"}), frozenset({"b@team.test"}))
    access.set_relation("p1", a.id, ProjectRelation.ASSIGNED, False)
    assert access.resource_for("p1").assignees == frozenset()
    assert access.resource_for("other").owner_email is None
    with pytest.raises(ValueError, match="set_owner"):
        access.set_relation("p1", a.id, ProjectRelation.OWNER, True)

def test_user_managers_need_both_keys_in_some_group(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    only_manage = accounts.signup("m@team.test", PASSWORD)
    only_approve = accounts.signup("a@team.test", PASSWORD)
    both = accounts.signup("b@team.test", PASSWORD)
    disabled = accounts.signup("d@team.test", PASSWORD)
    g_manage = groups.create_group("M", ["users.manage"]).id
    g_approve = groups.create_group("A", ["access.approve@own"]).id
    accounts.set_user_groups(only_manage.id, [g_manage])
    accounts.set_user_groups(only_approve.id, [g_approve])
    accounts.set_user_groups(both.id, [g_manage, g_approve])
    accounts.set_user_groups(disabled.id, [g_manage, g_approve])
    accounts.set_disabled(disabled.id, True)
    assert accounts.user_managers() == [ADMIN, "b@team.test"]

def test_a_refused_change_is_rolled_back_whole(env: AuthEnv) -> None:
    only, _ = accounts.bootstrap_admin(ADMIN, PASSWORD)
    token = sessions.create_session(only.id)
    with pytest.raises(LastAdmin):
        accounts.set_disabled(only.id, True)  # the guard fires after the disable and the revoke
    assert not accounts.get_user(only.id).disabled
    assert sessions.resolve_session(token) is not None
    with pytest.raises(LastAdmin):
        accounts.set_user_groups(only.id, [])
    assert accounts.get_user(only.id).groups == ["Admin/CEO"]
    admin_group = seed_id("admin")
    with pytest.raises(LastAdmin):
        groups.update_group(admin_group, "Admin/CEO", ["live.view"])  # drops users.manage
    assert "users.manage" in groups.get_group(admin_group).permissions
    with pytest.raises(LastAdmin):
        groups.delete_group(admin_group)
    assert groups.get_group(admin_group).member_ids == [only.id]

def test_non_admin_actor_limits_hold(env: AuthEnv) -> None:
    admin = accounts.signup(ADMIN, PASSWORD)
    dev = accounts.signup(OTHER, PASSWORD)
    accounts.set_user_groups(dev.id, [seed_id("developer")])
    actor = sessions.resolve_session(sessions.create_session(dev.id))
    with pytest.raises(NotAllowed):
        accounts.set_disabled(admin.id, True, actor=actor)
    with pytest.raises(NotAllowed):
        accounts.set_user_groups(dev.id, [seed_id("admin")], actor=actor)
    assert accounts.get_user(dev.id).groups == ["Developer"]

def test_bootstrap_admin_creates_then_resets(env: AuthEnv) -> None:
    user, created = accounts.bootstrap_admin(ADMIN, PASSWORD)
    assert created and user.groups == ["Admin/CEO"]
    token = sessions.create_session(user.id)
    again, created = accounts.bootstrap_admin(ADMIN, "second-password-123")
    assert not created and again.id == user.id and again.groups == ["Admin/CEO"]
    assert sessions.resolve_session(token) is None
    assert accounts.authenticate(ADMIN, "second-password-123") is not None

def test_concurrent_first_signups_yield_exactly_one_admin(env: AuthEnv) -> None:
    for _ in range(5):
        env.fresh(slow=True)
        made = race([lambda i=i: accounts.signup(f"u{i}@team.test", PASSWORD) for i in range(6)])
        assert all(kind == "ok" for kind, _ in made), made
        assert len([u for _, u in made if "Admin/CEO" in u.groups]) == 1
        assert len({u.id for _, u in made}) == 6

def test_concurrent_claims_yield_exactly_one_admin(env: AuthEnv) -> None:
    for _ in range(5):
        env.fresh(slow=True)
        users = [accounts.signup(f"c{i}@team.test", PASSWORD, secure_cookie=True)
                 for i in range(4)]
        assert all(not u.groups for u in users)
        outcome = race([lambda u=u: accounts.claim_admin(u.id) for u in users])
        assert sum(kind == "ok" for kind, _ in outcome) == 1, outcome
        assert all(isinstance(v, accounts.AccountError) for kind, v in outcome if kind == "err")
        assert len(groups.get_group(seed_id("admin")).member_ids) == 1

def test_disabling_the_last_two_admins_leaves_one_enabled(env: AuthEnv) -> None:
    for _ in range(15):
        env.fresh(slow=True)
        a, _ = accounts.bootstrap_admin("a@team.test", PASSWORD)
        b, _ = accounts.bootstrap_admin("b@team.test", PASSWORD)
        outcome = race([lambda uid=a.id: accounts.set_disabled(uid, True),
                        lambda uid=b.id: accounts.set_disabled(uid, True)])
        assert len([u for u in accounts.list_users() if not u.disabled]) >= 1, outcome
        assert any(isinstance(v, LastAdmin) for kind, v in outcome if kind == "err")

def test_last_admin_guard_survives_delete_and_regroup(env: AuthEnv) -> None:
    only, _ = accounts.bootstrap_admin(ADMIN, PASSWORD)
    with pytest.raises(LastAdmin):
        accounts.delete_user(only.id)
    with pytest.raises(LastAdmin):
        accounts.set_user_groups(only.id, [])
    with pytest.raises(LastAdmin):
        groups.delete_group(seed_id("admin"))
    assert accounts.get_user(only.id) is not None

def test_a_disabled_account_or_expired_session_never_resolves(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup(OTHER, PASSWORD)
    live, stale = sessions.create_session(user.id), sessions.create_session(user.id)
    assert sessions.resolve_session(live) is not None
    env.expire(stale)
    assert sessions.resolve_session(stale) is None
    assert env.digests() == [hashlib.sha256(live.encode()).hexdigest()]  # the stale id was dropped
    assert sessions.resolve_session("x" * 200) is None  # over-long ids are refused unread
    sessions.end_session(live)
    assert sessions.resolve_session(live) is None and env.digests() == []
    env.expire(sessions.create_session(user.id))  # an expired session is purged on the next login
    fresh = sessions.create_session(user.id)
    assert env.digests() == [hashlib.sha256(fresh.encode()).hexdigest()]

def test_password_hash_never_leaves_the_store(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    user = accounts.signup(OTHER, PASSWORD)
    assert env.dump().count("$argon2") == 2  # one per account, in the account record only
    surfaces = [repr(accounts.list_users()), repr(accounts.get_user(user.id)),
                repr(accounts.find_user(OTHER)), repr(groups.list_groups()),
                repr(sessions.resolve_session(sessions.create_session(user.id))),
                repr(accounts.user_managers()), repr(accounts.list_waiting())]
    with pytest.raises(accounts.AccountError) as dup:
        accounts.signup(OTHER, PASSWORD)
    with pytest.raises(LastAdmin) as last:
        accounts.set_disabled(accounts.find_user(ADMIN).id, True)
    for text in [*surfaces, str(dup.value), str(last.value)]:
        assert "argon2" not in text and "password_hash" not in text

def test_the_group_seed_runs_once(env: AuthEnv) -> None:
    accounts.signup(ADMIN, PASSWORD)
    groups.delete_group(seed_id("tester"))
    if env.name == "mongo":
        reset_auth_store()  # a restart: a new process-level handle on the same database
    assert [g.seed for g in groups.list_groups()] == ["admin", "sub-admin", "developer"]
