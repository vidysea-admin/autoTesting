"""The Mongo implementation of the auth store seam (`auth/store.py`; mongo-store U6b, M29/M30).

The `AuthTx` contract of `store_sqlite.py` over `store.mongo_guard.GuardedStore` only (no database
name here, M2/M5). Writers are serialised by the lease and a refused change is rolled back whole
by the undo log (`store_mongo_tx.py`); unique indexes are the second line. Readers take no lease,
so one may see a write just before its rollback; every rollback follows a refused change, which
only lowers privilege. A membership is an entry in the account's `group_ids`; a session is stored
by the sha256 of its token only.
"""

from __future__ import annotations

import functools
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from autotester.auth import db
from autotester.auth.defaults import ADMIN_SEED, DEFAULT_GROUPS
from autotester.auth.store_mongo_tx import META, AuthStoreBusy, Doc, MongoTxBase, coll_of, lease
from autotester.schema.auth import Group, PermissionKey, Principal, User
from autotester.store.mongo_backend import URI_ENV
from autotester.store.mongo_guard import GuardedStore, StoreDuplicateKey
from autotester.store.mongo_routes import StoreSelectionError

__all__ = ["AuthStoreBusy", "MongoAuthStore", "MongoAuthTx", "mongo_auth_store", "reset_auth_store"]

USERS, GROUPS, SESSIONS, GRANTS = "auth_users", "auth_groups", "auth_sessions", "auth_grants"
SEEDED_ID, NAMESPACE = "seeded", "auth"  # `p`: the guard's scoped delete_many
INDEXES: tuple[tuple[str, str, bool], ...] = (
    (USERS, "email", True), (USERS, "generation", True), (GROUPS, "name", True),
    (SESSIONS, "user_id", False), (GRANTS, "slug", False), (GRANTS, "user_id", False))


class MongoAuthTx(MongoTxBase):
    def _names(self) -> dict[int, str]: return {g["_id"]: g["name"] for g in self._docs(GROUPS)}

    def _perms(self, group_ids: list[int]) -> set[str]:
        return {p for g in self._docs(GROUPS) if g["_id"] in group_ids for p in g["permissions"]}

    def _user(self, doc: Doc | None, names: dict[int, str] | None = None) -> User | None:
        names = self._names() if names is None else names
        return None if doc is None else User(
            id=doc["_id"], email=doc["email"], display_name=doc["display_name"],
            disabled=bool(doc["disabled"]), generation=doc["generation"],
            created_at=datetime.fromisoformat(doc["created_at"]),
            groups=sorted(names[g] for g in doc["group_ids"] if g in names))

    def count_users(self) -> int: return coll_of(self._s, USERS).count_documents({})
    def get_user(self, user_id: int) -> User | None: return self._user(self._get(USERS, user_id))
    def find_user(self, email: str) -> User | None:
        return self._user(self._one(USERS, {"email": email}))

    def known_user_ids(self) -> set[int]: return {d["_id"] for d in self._docs(USERS)}

    def login_record(self, email: str) -> tuple[User, str] | None:
        doc = self._one(USERS, {"email": email})
        user = self._user(doc)
        return (user, doc["password_hash"]) if user and doc else None

    def list_users(self) -> list[User]:
        names = self._names()
        return [u for d in sorted(self._docs(USERS), key=lambda d: d["email"])
                if (u := self._user(d, names)) is not None]

    def user_manager_emails(self) -> list[str]:
        manage = PermissionKey.USERS_MANAGE.value
        return sorted(u["email"] for u in self._docs(USERS) if not u["disabled"]
                      and manage in (held := self._perms(u["group_ids"]))
                      and any(p.startswith("access.approve@") for p in held))

    def insert_user(self, email: str, password_hash: str) -> int:
        user_id = self._allocate(USERS)
        self._insert(USERS, {"_id": user_id, "email": email, "password_hash": password_hash,
                             "display_name": "", "disabled": False, "created_at": db.now_iso(),
                             "generation": db.new_account_generation(), "group_ids": []})
        return user_id

    def set_password_hash(self, user_id: int, password_hash: str) -> bool:
        return self._patch(USERS, user_id, password_hash=password_hash)

    def enable_with_password_hash(self, user_id: int, password_hash: str) -> None:
        self._patch(USERS, user_id, password_hash=password_hash, disabled=False)

    def set_disabled(self, user_id: int, disabled: bool) -> bool:
        return self._patch(USERS, user_id, disabled=disabled)

    def set_display_name(self, user_id: int, name: str) -> bool:
        return self._patch(USERS, user_id, display_name=name)

    def delete_user(self, user_id: int) -> bool:
        gone = self._drop(USERS, user_id)
        if gone:
            self.delete_user_sessions(user_id)
            self._drop_where(GRANTS, {"user_id": user_id})
        return gone

    def admin_group_id(self) -> int | None:
        doc = self._one(GROUPS, {"seed": ADMIN_SEED})
        return None if doc is None else int(doc["_id"])

    def admin_has_member(self) -> bool:
        admin = self.admin_group_id()
        return admin is not None and any(admin in u["group_ids"] for u in self._docs(USERS))

    def _group(self, doc: Doc | None) -> Group | None:
        return None if doc is None else Group(
            id=doc["_id"], name=doc["name"], seed=doc.get("seed"),
            permissions=sorted(doc["permissions"]),
            member_ids=sorted(self.group_member_ids(doc["_id"])))

    def list_groups(self) -> list[Group]:
        return [g for d in sorted(self._docs(GROUPS), key=lambda d: d["_id"])
                if (g := self._group(d)) is not None]

    def get_group(self, group_id: int) -> Group | None:
        return self._group(self._get(GROUPS, group_id))

    def known_group_ids(self) -> set[int]: return {d["_id"] for d in self._docs(GROUPS)}

    def group_name_taken(self, name: str, except_id: int | None = None) -> bool:
        return any(d["name"] == name and d["_id"] != except_id for d in self._docs(GROUPS))

    def insert_group(self, name: str) -> int:
        group_id = self._allocate(GROUPS)
        self._insert(GROUPS, {"_id": group_id, "name": name, "permissions": []})
        return group_id

    def rename_group(self, group_id: int, name: str) -> None:
        self._patch(GROUPS, group_id, name=name)

    def delete_group(self, group_id: int) -> bool:
        gone = self._drop(GROUPS, group_id)
        for user in self._docs(USERS) if gone else []:
            if group_id in user["group_ids"]:
                self._patch(USERS, user["_id"],
                            group_ids=[g for g in user["group_ids"] if g != group_id])
        return gone

    def group_permissions(self, group_id: int) -> set[str]:
        doc = self._get(GROUPS, group_id)
        return set(doc["permissions"]) if doc else set()

    def set_group_permissions(self, group_id: int, permissions: set[str]) -> None:
        self._patch(GROUPS, group_id, permissions=sorted(permissions))

    def group_member_ids(self, group_id: int) -> set[int]:
        return {u["_id"] for u in self._docs(USERS) if group_id in u["group_ids"]}

    def set_group_members(self, group_id: int, user_ids: set[int]) -> None:
        for user in self._docs(USERS):
            kept = {g for g in user["group_ids"] if g != group_id}
            wanted = sorted(kept | ({group_id} if user["_id"] in user_ids else set()))
            if wanted != sorted(user["group_ids"]):
                self._patch(USERS, user["_id"], group_ids=wanted)

    def user_group_ids(self, user_id: int) -> set[int]:
        doc = self._get(USERS, user_id)
        return set(doc["group_ids"]) if doc else set()

    def set_user_groups(self, user_id: int, group_ids: set[int]) -> None:
        self._patch(USERS, user_id, group_ids=sorted(group_ids))

    def add_membership(self, user_id: int, group_id: int, ignore_existing: bool = False) -> None:
        current = self.user_group_ids(user_id)
        if group_id in current and ignore_existing:
            return
        if group_id in current:
            raise StoreDuplicateKey("duplicate membership")
        if not self._patch(USERS, user_id, group_ids=sorted({*current, group_id})):
            raise ValueError("no such account")

    def ensure_an_admin_remains(self, after_delete: bool = False) -> None:
        users, admin = self._docs(USERS), self._one(GROUPS, {"seed": ADMIN_SEED})
        if not users and not after_delete:
            return
        if not (admin is not None and PermissionKey.USERS_MANAGE.value in admin["permissions"]
                and any(admin["_id"] in u["group_ids"] and not u["disabled"] for u in users)):
            raise db.LastAdmin("refused: this would leave no enabled Admin/CEO account "
                               "that can manage users")

    def insert_session(self, digest: str, user_id: int, created_at: str, expires_at: str) -> None:
        self._insert(SESSIONS, {"_id": digest, "p": NAMESPACE, "user_id": user_id,
                                "created_at": created_at, "expires_at": expires_at})

    def purge_sessions_before(self, now: str) -> None:
        self._writer(SESSIONS).delete_many({"p": NAMESPACE, "expires_at": {"$lt": now}})

    def delete_session(self, digest: str) -> None: self._drop(SESSIONS, digest)
    def has_session(self, digest: str) -> bool: return self._get(SESSIONS, digest) is not None
    def delete_user_sessions(self, user_id: int) -> None:
        self._drop_where(SESSIONS, {"user_id": user_id})

    def delete_session_if_expired(self, digest: str, now: str) -> None:
        doc = self._get(SESSIONS, digest)
        if doc is not None and doc["expires_at"] <= now:
            self._drop(SESSIONS, digest)

    def live_principal(self, digest: str, now: str) -> Principal | None:
        session = self._get(SESSIONS, digest)
        user = self._get(USERS, session["user_id"]) if session else None
        if session is None or not session["expires_at"] > now or user is None or user["disabled"]:
            return None
        return Principal(user_id=user["_id"], email=user["email"],
                         display_name=user["display_name"],
                         permissions=frozenset(self._perms(user["group_ids"])))

    def project_people(self, slug: str) -> dict[str, set[str]]:
        emails = {u["_id"]: u["email"] for u in self._docs(USERS)}
        people: dict[str, set[str]] = {}
        for grant in self._docs(GRANTS, {"slug": slug}):
            if grant["user_id"] in emails:
                people.setdefault(grant["relation"], set()).add(emails[grant["user_id"]])
        return people

    @staticmethod
    def _grant(slug: str, user_id: int, relation: str) -> Doc:
        return {"_id": f"{slug}|{user_id}|{relation}", "slug": slug, "user_id": user_id,
                "relation": relation}

    def replace_project_owner(self, slug: str, user_id: int) -> None:
        self._drop_where(GRANTS, {"slug": slug, "relation": "owner"})
        self._insert(GRANTS, self._grant(slug, user_id, "owner"))

    def add_project_relation(self, slug: str, user_id: int, relation: str) -> None:
        grant = self._grant(slug, user_id, relation)
        if self._get(GRANTS, grant["_id"]) is None:
            self._insert(GRANTS, grant)

    def remove_project_relation(self, slug: str, user_id: int, relation: str) -> None:
        self._drop(GRANTS, self._grant(slug, user_id, relation)["_id"])


class MongoAuthStore:
    def __init__(self, store: GuardedStore) -> None:
        self._s, self._prepared, self._once = store, False, threading.Lock()

    def exists(self) -> bool:
        """A read that finds no store must not create one (AU16): no write happens here."""
        return coll_of(self._s, META).find_one({"_id": SEEDED_ID}) is not None

    def _prepare(self) -> None:
        """Once per process: the indexes, and (AU11) the default groups once per store, under
        the lease; a crashed seed resumes group by group and never doubles one."""
        with self._once:
            if self._prepared:
                return
            for name, field, unique in INDEXES:
                coll_of(self._s, name).create_index([(field, 1)], unique=unique, name=field)
            meta = coll_of(self._s, META)
            with lease(self._s):
                if meta.find_one({"_id": SEEDED_ID}) is None:
                    tx = MongoAuthTx(self._s, True)
                    for seed, (name, permissions) in DEFAULT_GROUPS.items():
                        if tx._one(GROUPS, {"seed": seed}) is None:
                            tx._insert(GROUPS, {"_id": tx._allocate(GROUPS), "name": name,
                                                "seed": seed, "permissions": sorted(permissions)})
                    meta.insert_one({"_id": SEEDED_ID, "at": db.now_iso()})
            self._prepared = True

    @contextmanager
    def reading(self) -> Iterator[MongoAuthTx]:
        self._prepare()
        yield MongoAuthTx(self._s, False)

    @contextmanager
    def transaction(self) -> Iterator[MongoAuthTx]:
        self._prepare()
        with lease(self._s) as holds:
            tx = MongoAuthTx(self._s, True)
            try:
                yield tx
                if not holds():
                    raise AuthStoreBusy("the auth store lease expired mid-transaction")
            except BaseException:
                tx.rollback()
                raise


@functools.cache
def mongo_auth_store() -> MongoAuthStore:
    """The process's auth store, opened on first use from the store URI (provisional name; U9
    owns the wiring in `core/env.py`). The URI is never logged, echoed or kept in an error."""
    if not (uri := os.environ.get(URI_ENV, "").strip()):
        raise StoreSelectionError(f"{URI_ENV} is not set; the mongo store needs it")
    return MongoAuthStore(GuardedStore(uri))


def reset_auth_store() -> None:
    mongo_auth_store.cache_clear()
