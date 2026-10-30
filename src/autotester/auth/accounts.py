"""Accounts: open signup, first-account admin, password check, admin account actions.

A new account joins no group, so it holds zero permissions until an admin adds it to
one (AU6). The first account becomes Admin/CEO atomically (AU7). Disable, delete and
password reset end the account's sessions in the same transaction (AU3, AU8), and no
change may leave the store without an enabled admin (AU9). While Admin/CEO has no member,
a signed-in account may claim it, first claim wins (D-109). Storage goes through the
`auth.store.AuthStore` seam; no SQL lives here.
"""

from __future__ import annotations

from collections.abc import Callable

from autotester.auth import access
from autotester.auth.config import first_admin_email, public_facing
from autotester.auth.passwords import hash_password, needs_rehash, verify_password
from autotester.auth.store import AuthTx, auth_store
from autotester.schema.auth import Principal, User

MAX_EMAIL_LENGTH = 254
MAX_DISPLAY_NAME = 80


class AccountError(ValueError):
    """A signup or admin action was refused; the message is safe to show."""


def normalize_email(email: str) -> str:
    """Trimmed, lower-cased, one '@' with a non-empty local part and a dotted domain."""
    value = email.strip().lower()
    local, sep, domain = value.partition("@")
    if (not sep or not local or "@" in domain or "." not in domain.strip(".")
            or len(value) > MAX_EMAIL_LENGTH or any(c.isspace() or ord(c) < 32 for c in value)):
        raise AccountError("enter a valid email address")
    return value


def _loaded(tx: AuthTx, user_id: int) -> User:
    user = tx.get_user(user_id)
    if user is None:
        raise AccountError("no such account")
    return user


def _becomes_first_admin(tx: AuthTx, address: str, secure_cookie: bool) -> bool:
    """AU7 / D-074 (d): with AUTOTESTER_FIRST_ADMIN_EMAIL set, only that address can become
    the first admin, while no admin exists. Unset: on a local loopback server the first
    account becomes admin; on a hosted / non-loopback server nobody does (the CLI
    `bootstrap-admin` creates the first admin)."""
    wanted = first_admin_email()
    if not wanted:
        if public_facing(secure_cookie):
            return False
        return tx.count_users() == 0
    return address == wanted and not tx.admin_has_member()


def _claim_refusal(tx: AuthTx, user: User | None) -> str | None:
    """Why this account may not claim Admin/CEO now (D-109), or None when it may."""
    if user is None or user.disabled:
        return "this account cannot claim admin"
    if tx.admin_group_id() is None:
        return "the Admin/CEO group was deleted; restore it first"
    if tx.admin_has_member():
        return "an administrator already exists"
    wanted = first_admin_email()
    if wanted and user.email != wanted:
        return "only the configured first-admin address may claim admin"
    return None


def may_claim_admin(email: str) -> bool:
    """D-109: whether the Claim admin button is shown to this signed-in address (a read;
    `claim_admin` re-checks inside its own transaction)."""
    with auth_store().reading() as tx:
        user = tx.find_user(email)
        return user is not None and _claim_refusal(tx, user) is None


def claim_admin(user_id: int) -> User:
    """D-109: while Admin/CEO has no member, put this account in it. One write transaction
    re-checks emptiness and inserts, so two concurrent claims yield exactly one admin.
    Raises AccountError (message safe to show) when refused."""
    with auth_store().transaction() as tx:
        refusal = _claim_refusal(tx, tx.get_user(user_id))
        if refusal is not None:
            raise AccountError(refusal)
        admin = tx.admin_group_id()
        if admin is None:  # unreachable: _claim_refusal already refused a missing group
            raise AccountError("the Admin/CEO group was deleted; restore it first")
        tx.add_membership(user_id, admin)
        tx.ensure_an_admin_remains()
        return _loaded(tx, user_id)


def signup(email: str, password: str, secure_cookie: bool = False) -> User:
    """Create an account; it gets a group only when it is the first admin.
    `secure_cookie`: the request's session cookie is Secure (AU7 counts that as hosted)."""
    address = normalize_email(email)
    password_hash = hash_password(password)
    with auth_store().transaction() as tx:
        if tx.find_user(address) is not None:
            raise AccountError("an account with this email already exists")
        first = _becomes_first_admin(tx, address, secure_cookie)
        user_id = tx.insert_user(address, password_hash)
        admin = tx.admin_group_id()
        if first and admin is not None:
            tx.add_membership(user_id, admin)
        return _loaded(tx, user_id)


def authenticate(email: str, password: str) -> User | None:
    """The account for a correct email + password, or None (wrong, unknown or disabled).
    Every path runs one hash verification (AU2)."""
    try:
        address = normalize_email(email)
    except AccountError:
        address = ""
    with auth_store().reading() as tx:
        record = tx.login_record(address)
        stored = record[1] if record is not None else None
        if not verify_password(stored, password) or record is None or record[0].disabled:
            return None
        user = record[0]
    if needs_rehash(stored):
        with auth_store().transaction() as tx:
            tx.set_password_hash(user.id, hash_password(password))
    return user


def list_waiting() -> list[User]:
    """Enabled accounts with no group: what a new signup is until an admin decides."""
    return [u for u in list_users() if not u.disabled and not u.groups]


def user_managers() -> list[str]:
    """Emails of enabled accounts that can act on a signup, i.e. open /access-requests with its
    New accounts section: users.manage AND access.approve in some scope (F2). A users.manage-only
    holder is not mailed a link that 403s; they see the Waiting pill on /admin/users instead."""
    with auth_store().reading() as tx:
        return tx.user_manager_emails()


def get_user(user_id: int) -> User | None:
    with auth_store().reading() as tx:
        return tx.get_user(user_id)


def find_user(email: str) -> User | None:
    with auth_store().reading() as tx:
        return tx.find_user(email.strip().lower())


def list_users() -> list[User]:
    with auth_store().reading() as tx:
        return tx.list_users()


def _update(change: Callable[[AuthTx], bool], user_id: int, end_sessions: bool,
            deleting: bool = False, actor: Principal | None = None) -> None:
    with auth_store().transaction() as tx:
        access.require_may_touch(tx, actor, user_id)
        if not change(tx):
            raise AccountError("no such account")
        if end_sessions:
            tx.delete_user_sessions(user_id)
        tx.ensure_an_admin_remains(after_delete=deleting)


def set_disabled(user_id: int, disabled: bool, actor: Principal | None = None) -> None:
    _update(lambda tx: tx.set_disabled(user_id, disabled), user_id,
            end_sessions=disabled, actor=actor)


def delete_user(user_id: int, actor: Principal | None = None) -> None:
    """Sessions, memberships and project relations go with the account (ON DELETE
    CASCADE), so a project it owned has no owner afterwards (AU8)."""
    _update(lambda tx: tx.delete_user(user_id), user_id, end_sessions=False,
            deleting=True, actor=actor)


def reset_password(user_id: int, password: str, actor: Principal | None = None) -> None:
    """Admin reset: a new hash and every existing session of that user revoked (AU8).
    Only an Admin/CEO member may reset an admin's password (P5)."""
    new_hash = hash_password(password)
    _update(lambda tx: tx.set_password_hash(user_id, new_hash), user_id,
            end_sessions=True, actor=actor)


def set_display_name(user_id: int, name: str) -> None:
    clean = " ".join(name.split())
    if len(clean) > MAX_DISPLAY_NAME or any(ord(c) < 32 for c in clean):
        raise AccountError(f"a display name has at most {MAX_DISPLAY_NAME} printable characters")
    _update(lambda tx: tx.set_display_name(user_id, clean), user_id, end_sessions=False)


def set_user_groups(user_id: int, group_ids: list[int],
                    actor: Principal | None = None) -> None:
    """Replace the account's group memberships with exactly `group_ids`. With an `actor`
    (P5): only an Admin/CEO member changes Admin/CEO membership, and a group may be added
    only if the actor holds every permission it carries (users.manage alone never mints
    more access than its holder has)."""
    with auth_store().transaction() as tx:
        if tx.get_user(user_id) is None:
            raise AccountError("no such account")
        if not set(group_ids) <= tx.known_group_ids():
            raise AccountError("unknown group")
        access.require_may_regroup(tx, actor, user_id, set(group_ids))
        tx.set_user_groups(user_id, set(group_ids))
        tx.ensure_an_admin_remains()


def _require_waiting(tx: AuthTx, user_id: int) -> None:
    user = tx.get_user(user_id)
    if user is None:
        raise AccountError("no such account")
    if user.disabled or tx.user_group_ids(user_id):
        raise AccountError("this account is not waiting for access")


def approve_waiting(user_id: int, group_id: int, actor: Principal | None = None) -> None:
    """Put a waiting account (enabled, no group) into `group_id`. Same limits as
    `set_user_groups`; refused, changing nothing, once it already has a group."""
    with auth_store().transaction() as tx:
        _require_waiting(tx, user_id)
        if group_id not in tx.known_group_ids():
            raise AccountError("unknown group")
        access.require_may_regroup(tx, actor, user_id, {group_id})
        tx.add_membership(user_id, group_id)


def decline_waiting(user_id: int, actor: Principal | None = None) -> None:
    """Disable a waiting account and end its sessions; refused once it has a group."""
    with auth_store().transaction() as tx:
        _require_waiting(tx, user_id)
        access.require_may_touch(tx, actor, user_id)
        tx.set_disabled(user_id, True)
        tx.delete_user_sessions(user_id)


def bootstrap_admin(email: str, password: str) -> tuple[User, bool]:
    """CLI break-glass: create the account or reset its password, enable it, put it in
    Admin/CEO and end its old sessions. Returns (user, created)."""
    address = normalize_email(email)
    password_hash = hash_password(password)
    with auth_store().transaction() as tx:
        existing = tx.find_user(address)
        if existing is None:
            user_id = tx.insert_user(address, password_hash)
        else:
            user_id = existing.id
            tx.enable_with_password_hash(user_id, password_hash)
            tx.delete_user_sessions(user_id)
        admin = tx.admin_group_id()
        if admin is None:
            raise AccountError("the Admin/CEO group was deleted; restore it before bootstrap")
        tx.add_membership(user_id, admin, ignore_existing=True)
        return _loaded(tx, user_id), existing is None
