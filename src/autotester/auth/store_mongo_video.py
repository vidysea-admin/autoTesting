"""Video shares, share links, access requests and comments on the Mongo auth store (mongo-store
U6c, D-129): the Mongo side of what `stages/video_access.py`, `video_requests.py` and
`video_comments.py` keep in SQLite tables.

`VideoOps` adds these operations to the transaction object of `store_mongo.py`; every write goes
through the journal and the fence of `store_mongo_tx.py` / `store_mongo_fence.py`, so a refused or
interrupted change is undone whole and a stalled writer lands nothing. The lease serialises all
writers, which is what makes "one pending request per person per video" hold without a unique
index. Rows come back as plain dicts keyed by the SQLite column names (`id` for the numeric
ones), so the callers' row-to-model functions are shared by both backends. A share's id carries
the sha256 of the address, never the address (a deleted share leaves a hidden slot: M30, AT-1431).
"""

from __future__ import annotations

import hashlib
from typing import Any

from autotester.auth.store_mongo_tx import Doc, MongoTxBase

__all__ = ["VIDEO_INDEXES", "VideoOps"]

SHARES, LINKS = "video_shares", "video_links"
REQUESTS, COMMENTS = "access_requests", "video_comments"
PENDING = "pending"
VIDEO_INDEXES: tuple[tuple[str, str, bool], ...] = (
    (SHARES, "slug", False), (LINKS, "slug", False), (REQUESTS, "slug", False),
    (REQUESTS, "requester", False), (COMMENTS, "slug", False))


def _row(doc: Doc | None) -> Doc | None:
    """The document as a SQLite-shaped row: no stamp, the numeric id under `id`."""
    return None if doc is None else {**{k: v for k, v in doc.items() if k not in ("_id", "_e")},
                                     "id": doc["_id"]}


def _video(slug: str, video_id: str) -> Doc: return {"slug": slug, "video_id": video_id}


class VideoOps(MongoTxBase):
    # -- shares and links -----------------------------------------------------------
    def share_emails(self, slug: str, video_id: str) -> frozenset[str]:
        return frozenset(d["email"] for d in self._docs(SHARES, _video(slug, video_id)))

    def set_share(self, slug: str, video_id: str, email: str, present: bool, granted_by: str,
                  now: str) -> None:
        sid = f"{slug}|{video_id}|{hashlib.sha256(email.encode()).hexdigest()}"
        if not present:
            self._drop(SHARES, sid)
        elif self._get(SHARES, sid) is None:
            self._insert(SHARES, {"_id": sid, **_video(slug, video_id), "email": email,
                                  "granted_by": granted_by, "granted_at": now})

    def _live_links(self, slug: str, video_id: str) -> list[Doc]:
        return [d for d in self._docs(LINKS, _video(slug, video_id)) if d["revoked_at"] is None]

    def create_link(self, digest: str, slug: str, video_id: str, created_by: str, now: str) -> None:
        """A new link; any earlier live link of this video is revoked in the same transaction."""
        self.revoke_links(slug, video_id, now)
        self._insert(LINKS, {"_id": digest, **_video(slug, video_id), "created_by": created_by,
                             "created_at": now, "revoked_at": None})

    def revoke_links(self, slug: str, video_id: str, now: str) -> int:
        live = self._live_links(slug, video_id)
        for doc in live:
            self._patch(LINKS, doc["_id"], revoked_at=now)
        return len(live)

    def link_since(self, slug: str, video_id: str) -> str | None:
        live = self._live_links(slug, video_id)
        return str(live[0]["created_at"]) if live else None

    def link_target(self, digest: str) -> tuple[str, str] | None:
        doc = self._get(LINKS, digest)
        return None if doc is None or doc["revoked_at"] is not None else (doc["slug"],
                                                                          doc["video_id"])

    def purge_video_data(self, slug: str, video_id: str | None = None) -> None:
        """A video (or, without `video_id`, a whole project) is gone: all four kinds go with it."""
        flt = {"slug": slug} if video_id is None else _video(slug, video_id)
        for name in (LINKS, SHARES, REQUESTS, COMMENTS):
            self._drop_where(name, flt)

    # -- access requests --------------------------------------------------------------
    def request_access(self, slug: str, video_id: str, requester: str,
                       now: str) -> tuple[Doc | None, bool]:
        """(the pending request, whether this call made it): one pending per person per video."""
        flt = {**_video(slug, video_id), "requester": requester, "status": PENDING}
        pending = self._docs(REQUESTS, flt)
        if pending:
            return _row(pending[0]), False
        rid = self._allocate(REQUESTS)
        self._insert(REQUESTS, {"_id": rid, **flt, "created_at": now, "decided_by": None,
                                "decided_at": None})
        return _row(self._get(REQUESTS, rid)), True

    def request_rows(self, **match: Any) -> list[Doc]:
        """Requests matching every given column (`requester`, `status`, `slug`, `video_id`),
        oldest first."""
        return [r for d in sorted(self._docs(REQUESTS, match), key=lambda d: d["_id"])
                if (r := _row(d)) is not None]

    def get_request(self, request_id: int) -> Doc | None:
        return _row(self._get(REQUESTS, request_id))

    def decide_request(self, request_id: int, status: str, by: str, now: str,
                       share: bool) -> bool:
        """Decide a still-pending request exactly once; an approval adds the one share."""
        doc = self._get(REQUESTS, request_id)
        if doc is None or doc["status"] != PENDING:
            return False
        self._patch(REQUESTS, request_id, status=status, decided_by=by, decided_at=now)
        if share:
            self.set_share(doc["slug"], doc["video_id"], doc["requester"], True, by, now)
        return True

    # -- comments ---------------------------------------------------------------------
    def add_comment(self, slug: str, video_id: str, author: str, at_s: float, text: str,
                    now: str) -> Doc:
        cid = self._allocate(COMMENTS)
        self._insert(COMMENTS, {"_id": cid, **_video(slug, video_id), "author": author,
                                "at_s": at_s, "text": text, "created_at": now,
                                "edited_at": None, "pointer_line": None})
        return self.comment_row(cid) or {}

    def comment_row(self, comment_id: int) -> Doc | None:
        return _row(self._get(COMMENTS, comment_id))

    def comment_rows(self, slug: str, video_id: str) -> list[Doc]:
        """Oldest second first, then oldest comment first."""
        docs = sorted(self._docs(COMMENTS, _video(slug, video_id)),
                      key=lambda d: (d["at_s"], d["_id"]))
        return [r for d in docs if (r := _row(d)) is not None]

    def edit_comment(self, comment_id: int, text: str, now: str) -> Doc | None:
        self._patch(COMMENTS, comment_id, text=text, edited_at=now)
        return self.comment_row(comment_id)

    def delete_comment(self, comment_id: int) -> None: self._drop(COMMENTS, comment_id)

    def promote_comment(self, comment_id: int, line: str) -> Doc | None:
        doc = self._get(COMMENTS, comment_id)
        if doc is not None and doc["pointer_line"] is None:
            self._patch(COMMENTS, comment_id, pointer_line=line)
        return self.comment_row(comment_id)
