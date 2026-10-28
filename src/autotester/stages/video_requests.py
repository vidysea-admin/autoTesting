"""The request-access flow (TP5): ask, route to the people who may approve, decide once.

One job: store an `AccessRequest`, work out who may act on it (always through `authorize()`),
and apply an approve or decline exactly once. Approving creates one `Share` on that video for
that requester; a second approve, a double click or a replay changes nothing. The optional
notification mail goes only through the shared transport (`delivery/email.py`), carries a link
and nothing else, and a mail failure never blocks the request.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime

from autotester.auth import db
from autotester.auth.access import authorize
from autotester.core.paths import repo_root
from autotester.delivery import email as mail
from autotester.schema.auth import PermissionKey, Principal, ResourceRef
from autotester.schema.delivery import Recipient, RenderedMessage
from autotester.schema.team_enums import AccessRequestStatus as Status
from autotester.schema.video_share import AccessRequest
from autotester.stages.video_access import clean_email, video_resource

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row(row: sqlite3.Row) -> AccessRequest:
    return AccessRequest(id=row["id"], slug=row["slug"], video_id=row["video_id"],
                         requester=row["requester"], status=Status(row["status"]),
                         created_at=row["created_at"], decided_by=row["decided_by"],
                         decided_at=row["decided_at"])


def request_access(slug: str, video_id: str, requester: str) -> tuple[AccessRequest | None, bool]:
    """(the pending request, whether this call made it). (None, False) when there is no such
    video. Asking twice for the same video is one pending request: a unique index, so a double
    POST cannot make two."""
    if video_resource(slug, video_id) is None:
        return None, False
    who = clean_email(requester)
    with db.transaction() as conn:
        made = conn.execute(
            "INSERT OR IGNORE INTO access_requests (slug, video_id, requester, status, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (slug, video_id, who, Status.PENDING.value, _now())).rowcount == 1
        row = conn.execute("SELECT * FROM access_requests WHERE slug = ? AND video_id = ? AND "
                           "requester = ? AND status = ?",
                           (slug, video_id, who, Status.PENDING.value)).fetchone()
    return (None if row is None else _row(row)), made


def latest_request(slug: str, video_id: str, requester: str) -> AccessRequest | None:
    if not db.store_exists():
        return None
    with db.reading() as conn:
        row = conn.execute("SELECT * FROM access_requests WHERE slug = ? AND video_id = ? AND "
                           "requester = ? ORDER BY id DESC LIMIT 1",
                           (slug, video_id, clean_email(requester))).fetchone()
    return None if row is None else _row(row)


def requests_by(requester: str) -> list[AccessRequest]:
    """Everything this person has asked for, newest first (they see the outcome here)."""
    if not db.store_exists():
        return []
    with db.reading() as conn:
        return [_row(r) for r in conn.execute(
            "SELECT * FROM access_requests WHERE requester = ? ORDER BY id DESC",
            (clean_email(requester),))]


def may_decide(who: Principal, req: AccessRequest, res: ResourceRef | None = None) -> bool:
    """True when `who` may approve or decline `req`: holds `access.approve` covering that video,
    and is not the requester (nobody approves their own request)."""
    res = res or video_resource(req.slug, req.video_id)
    return (res is not None and clean_email(who.email) != req.requester
            and authorize(who, PermissionKey.ACCESS_APPROVE, res))


def pending_for(who: Principal) -> list[AccessRequest]:
    """The pending requests `who` may act on and no others (absence, not 403, for the rest)."""
    if not db.store_exists():
        return []
    with db.reading() as conn:
        rows = [_row(r) for r in conn.execute(
            "SELECT * FROM access_requests WHERE status = ? ORDER BY id", (Status.PENDING.value,))]
    return [r for r in rows if may_decide(who, r)]


def get_request(request_id: int) -> AccessRequest | None:
    if not db.store_exists():
        return None
    with db.reading() as conn:
        row = conn.execute("SELECT * FROM access_requests WHERE id = ?", (request_id,)).fetchone()
    return None if row is None else _row(row)


def decide(who: Principal, request_id: int, approve: bool) -> AccessRequest | None:
    """Apply the decision once. None when `who` may not act on it (the caller answers as for a
    request that does not exist). A request already decided is returned unchanged, with no
    second `Share` and no second audit-worthy change."""
    req = get_request(request_id)
    if req is None or not may_decide(who, req):
        return None
    new = Status.APPROVED if approve else Status.DECLINED
    with db.transaction() as conn:
        won = conn.execute(
            "UPDATE access_requests SET status = ?, decided_by = ?, decided_at = ? "
            "WHERE id = ? AND status = ?",
            (new.value, clean_email(who.email), _now(), request_id, Status.PENDING.value)).rowcount
        if won and approve:
            conn.execute("INSERT OR IGNORE INTO video_shares (slug, video_id, email, granted_by, "
                         "granted_at) VALUES (?, ?, ?, ?, ?)",
                         (req.slug, req.video_id, req.requester, clean_email(who.email), _now()))
    return get_request(request_id)


def _permissions(conn: sqlite3.Connection, email: str) -> frozenset[str]:
    return frozenset(r["permission"] for r in conn.execute(
        "SELECT DISTINCT p.permission FROM users u JOIN memberships m ON m.user_id = u.id "
        "JOIN group_permissions p ON p.group_id = m.group_id WHERE u.email = ? AND u.disabled = 0",
        (email,)))


def approvers(res: ResourceRef, requester: str) -> list[str]:
    """Emails of everyone who may approve a request on `res`: the uploader, the project's
    sub-admins and any admin (each by `authorize`), never the requester."""
    candidates: set[str] = set(res.assignees) | ({res.owner_email} if res.owner_email else set())
    with db.reading() as conn:
        candidates |= {r["email"] for r in conn.execute(
            "SELECT DISTINCT u.email FROM users u JOIN memberships m ON m.user_id = u.id "
            "JOIN group_permissions p ON p.group_id = m.group_id "
            "WHERE p.permission = ? AND u.disabled = 0",
            (f"{PermissionKey.ACCESS_APPROVE.value}@all",))}
        out = []
        for email in sorted(candidates - {clean_email(requester)}):
            person = Principal(user_id=1, email=email, permissions=_permissions(conn, email))
            if authorize(person, PermissionKey.ACCESS_APPROVE, res):
                out.append(email)
    return out


def notify_approvers(emails: list[str], link: str, *, environ: Mapping[str, str] | None = None,
                     transport: mail.MailTransport | None = None, subject: str | None = None,
                     body: str | None = None) -> int:
    """Mail each approver a link to the requests page, only when SMTP is configured (HO27).
    The text carries a link and no video, thumbnail or comment text. Returns how many were
    handed to the transport; a failure is logged by class and never raised. `subject` and
    `body` (a template with `{link}`) let another request kind, such as a new account waiting
    for a group, reuse this transport."""
    env = os.environ if environ is None else environ
    if transport is None and not mail.is_configured(env):
        return 0
    sender = transport or mail.select_transport(env, repo_root() / ".work" / "outbox")
    text = body or ("Someone asked for access to a video you can approve.\n"
                    "Open the requests page: {link}\n")
    message = RenderedMessage(subject=subject or "AutoTester: someone asked for access to a video",
                              body=text.replace("{link}", link))
    sent = 0
    for address in emails:
        try:
            sender.send(Recipient(user_id=f"u{sent}", address=address), message,
                        key=f"access-request-{sent}")
            sent += 1
        except (mail.TransportError, ValueError) as exc:
            log.warning("access-request mail not sent (%s)", type(exc).__name__)
    return sent

