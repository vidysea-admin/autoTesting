"""Comment routes of the video portal (T-198b / G9, TP2, TP6).

The login gate has already answered 404 for a video the account may not view and 403 for one it
may view but not comment on (`video` rules). Here the author comes from the session only (a
posted `author` is never read), an edit is the author's alone, a delete is the author's or a
holder of `comment.create@all`, and promoting needs `project.edit` (a `project` rule).
"""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from autotester.auth.access import authorize
from autotester.schema.auth import PermissionKey as K
from autotester.schema.auth import ResourceRef
from autotester.schema.video_share import VideoComment
from autotester.stages import video_access as access
from autotester.stages import video_comments as comments
from autotester.ui.routes_video_portal import render_player, who_is

router = APIRouter()


def _back(slug: str, video_id: str) -> Response:
    return RedirectResponse(f"/projects/{slug}/videos/{video_id}", status_code=303)


def _comment(slug: str, video_id: str, comment_id: int) -> VideoComment:
    found = comments.get_comment(slug, video_id, comment_id)
    if found is None:
        raise HTTPException(404, "no such comment")
    return found


def _refused(exc: comments.CommentError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.get("/projects/{slug}/videos/{video_id}/comments")
def comments_json(slug: str, video_id: str) -> Response:
    """The comments as data (JSON); the text is as stored and the page escapes it."""
    rows = [{"id": c.id, "at_s": c.at_s, "author": c.author, "text": c.text,
             "created_at": c.created_at.isoformat(), "edited": c.edited_at is not None,
             "promoted": c.pointer_line is not None}
            for c in comments.list_comments(slug, video_id)]
    return JSONResponse({"comments": rows})


@router.post("/projects/{slug}/videos/{video_id}/comments")
def comment_create(request: Request, slug: str, video_id: str, at_s: str = Form(""),
                   text: str = Form("")) -> Response:
    """A refused comment stays a 400 and stores nothing. A browser gets the video page back with
    the reason inline and its typed time and text kept (escaped); an API client gets the JSON."""
    who = who_is()
    source = access.find_video(slug, video_id)
    try:
        second = comments.parse_at_s(at_s, source.duration_s if source else None)
        body = comments.clean_text(text)
    except comments.CommentError as exc:
        res = access.video_resource(slug, video_id)
        if source is None or res is None or "text/html" not in request.headers.get("accept", ""):
            raise _refused(exc) from None
        page = render_player(who, slug, video_id, res, source, (str(exc), at_s, text))
        return HTMLResponse(page, status_code=400)
    comments.add_comment(slug, video_id, who.email, second, body)
    return _back(slug, video_id)


@router.post("/projects/{slug}/videos/{video_id}/comments/{comment_id}/edit")
def comment_edit(slug: str, video_id: str, comment_id: int, text: str = Form("")) -> Response:
    who = who_is()
    found = _comment(slug, video_id, comment_id)
    if found.author != who.email.lower():
        raise HTTPException(403, "only the author can edit a comment")
    try:
        body = comments.clean_text(text)
    except comments.CommentError as exc:
        raise _refused(exc) from None
    comments.edit_comment(comment_id, body)
    return _back(slug, video_id)


@router.post("/projects/{slug}/videos/{video_id}/comments/{comment_id}/delete")
def comment_delete(slug: str, video_id: str, comment_id: int) -> Response:
    who = who_is()
    found = _comment(slug, video_id, comment_id)
    moderator = authorize(who, K.COMMENT_CREATE, ResourceRef(project_slug=slug))  # @all only
    if found.author != who.email.lower() and not moderator:
        raise HTTPException(403, "only the author or an admin can delete a comment")
    comments.delete_comment(comment_id)
    return _back(slug, video_id)


@router.post("/projects/{slug}/videos/{video_id}/comments/{comment_id}/promote")
def comment_promote(slug: str, video_id: str, comment_id: int) -> Response:
    """Turn the comment into a pointer line once; the comment itself stays."""
    who_is()
    found = _comment(slug, video_id, comment_id)
    source = access.find_video(slug, video_id)
    line = comments.pointer_line(found.at_s, found.text, source.duration_s if source else None)
    comments.promote(comment_id, line)
    return _back(slug, video_id)
