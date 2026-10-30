"""Who may open a video, and how: the video resource, shares and share links (TP1, TP3).

One job: turn (project slug, video id) into the `ResourceRef` that `authorize()` judges, and
keep the people (`shared_with`) and the share-link tokens behind it. A video's owner is the
source's `uploaded_by` (TI11), its assignees are the project's, its `shared_with` is the people
shared on THIS video. A source with no recorded uploader matches only `@all` (fails closed).
Nothing here compares an email to a group or a role: the decision is always `authorize()`.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path

from autotester.auth import db
from autotester.auth.access import authorize, resource_for
from autotester.core.paths import SLUG_PATTERN
from autotester.schema.auth import PermissionKey, Principal, ResourceRef
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.schema.video_share import MAX_TOKEN_CHARS, TOKEN_BYTES
from autotester.store.project_store import ProjectStore
from autotester.store.run_store import local_blob

_SLUG = re.compile(SLUG_PATTERN)
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")


def clean_email(email: str) -> str:
    return email.strip().lower()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def find_video(slug: str, video_id: str) -> Source | None:
    """The video source with this id in this project, or None (unknown, unsafe or not a video)."""
    if not _SLUG.fullmatch(slug) or not _VIDEO_ID.fullmatch(video_id):
        return None
    for source in ProjectStore(slug).list_sources():
        if source.id == video_id and source.kind is SourceKind.VIDEO:
            return source
    return None


def shared_emails(slug: str, video_id: str) -> frozenset[str]:
    if not db.store_exists():
        return frozenset()
    with db.reading() as conn:
        return frozenset(r["email"] for r in conn.execute(
            "SELECT email FROM video_shares WHERE slug = ? AND video_id = ?", (slug, video_id)))


def _resource(slug: str, source: Source, project: ResourceRef) -> ResourceRef:
    return ResourceRef(project_slug=slug, owner_email=source.uploaded_by,
                       assignees=project.assignees, video_id=source.id,
                       shared_with=shared_emails(slug, source.id))


def video_resource(slug: str, video_id: str) -> ResourceRef | None:
    """What `authorize` judges a video key against; None when there is no such video."""
    source = find_video(slug, video_id)
    return None if source is None else _resource(slug, source, resource_for(slug))


def viewable_videos(who: Principal, slugs: list[str]) -> list[tuple[str, Source]]:
    """Every video in `slugs` this principal may open (`video.view`), project then upload order."""
    out: list[tuple[str, Source]] = []
    for slug in slugs:
        project = resource_for(slug)
        for source in ProjectStore(slug).list_sources():
            if source.kind is SourceKind.VIDEO and authorize(
                    who, PermissionKey.VIDEO_VIEW, _resource(slug, source, project)):
                out.append((slug, source))
    return out


def set_share(slug: str, video_id: str, email: str, present: bool, granted_by: str) -> None:
    """Add (idempotent) or remove one person on one video's `shared_with`."""
    who = clean_email(email)
    with db.transaction() as conn:
        if present:
            conn.execute("INSERT OR IGNORE INTO video_shares (slug, video_id, email, granted_by, "
                         "granted_at) VALUES (?, ?, ?, ?, ?)",
                         (slug, video_id, who, clean_email(granted_by), _now()))
        else:
            conn.execute("DELETE FROM video_shares WHERE slug = ? AND video_id = ? AND email = ?",
                         (slug, video_id, who))


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_link(slug: str, video_id: str, created_by: str) -> str:
    """A new share-link token (the only time it exists in the clear); any earlier link for this
    video is revoked, so a video has at most one live link."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    with db.transaction() as conn:
        conn.execute("UPDATE video_links SET revoked_at = ? WHERE slug = ? AND video_id = ? "
                     "AND revoked_at IS NULL", (_now(), slug, video_id))
        conn.execute("INSERT INTO video_links (token_hash, slug, video_id, created_by, "
                     "created_at) VALUES (?, ?, ?, ?, ?)",
                     (_digest(token), slug, video_id, clean_email(created_by), _now()))
    return token


def revoke_links(slug: str, video_id: str) -> int:
    with db.transaction() as conn:
        return conn.execute("UPDATE video_links SET revoked_at = ? WHERE slug = ? AND "
                            "video_id = ? AND revoked_at IS NULL",
                            (_now(), slug, video_id)).rowcount


def live_link_since(slug: str, video_id: str) -> str | None:
    """When this video's live link was made (ISO), or None. Never the token."""
    if not db.store_exists():
        return None
    with db.reading() as conn:
        row = conn.execute("SELECT created_at FROM video_links WHERE slug = ? AND video_id = ? "
                           "AND revoked_at IS NULL", (slug, video_id)).fetchone()
    return None if row is None else str(row["created_at"])


def resolve_link(token: str) -> tuple[str, str] | None:
    """(slug, video id) of a live link, or None. A revoked, unknown, truncated, oversized or
    malformed token all give the same None; the compare is constant time."""
    if not token or len(token) > MAX_TOKEN_CHARS or not _TOKEN.fullmatch(token):
        return None
    if not db.store_exists():
        return None
    digest = _digest(token)
    with db.reading() as conn:
        row = conn.execute("SELECT token_hash, slug, video_id FROM video_links "
                           "WHERE token_hash = ? AND revoked_at IS NULL", (digest,)).fetchone()
    if row is None or not hmac.compare_digest(str(row["token_hash"]), digest):
        return None
    return str(row["slug"]), str(row["video_id"])


def purge_video(slug: str, video_id: str) -> None:
    """The video is gone: its links, shares, requests and comments go with it (TP3)."""
    with db.transaction() as conn:
        for table in ("video_links", "video_shares", "access_requests", "video_comments"):
            conn.execute(f"DELETE FROM {table} WHERE slug = ? AND video_id = ?", (slug, video_id))


def purge_project_videos(slug: str) -> None:
    """The project is gone: every video's links, shares, requests and comments go with it."""
    with db.transaction() as conn:
        for table in ("video_links", "video_shares", "access_requests", "video_comments"):
            conn.execute(f"DELETE FROM {table} WHERE slug = ?", (slug,))


def media_path(slug: str, source: Source) -> Path | None:
    """The bytes of a video, resolved from the source's recorded path inside the project's own
    directory. Never from anything the client sent; a path outside the directory, a missing
    file or a symlink that leaves it gives None."""
    if not source.path:
        return None
    root = ProjectStore(slug).paths.dir.resolve()
    try:
        candidate = (root / source.path).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(root):
        return None
    candidate = local_blob(candidate)  # M51: a verified cache copy when the bytes are in GridFS
    return candidate if candidate.is_file() else None
