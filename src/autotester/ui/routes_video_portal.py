"""The video page, its byte route and the sharing controls (T-198b / G9, TP1, TP3).

Who may reach what is decided twice, both server-side: the login gate's `video` rules
(`auth/policy.py::PORTAL_POLICY`) answer a missing or unviewable video 404 before this module
runs, and the page route below shows a person with no access the request-access page and no
bytes. The bytes come from the source's recorded path inside the project, never from the URL.
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

from autotester.auth import accounts, audit
from autotester.auth.access import authorize, resource_for
from autotester.auth.context import current_principal
from autotester.schema.auth import PermissionKey, Principal, ResourceRef
from autotester.stages import video_access as access
from autotester.stages import video_comments as comments
from autotester.stages.video_requests import latest_request, requests_by
from autotester.ui import video_portal_view as view
from autotester.ui.helpers import _project_slugs

router = APIRouter()
K = PermissionKey


def who_is() -> Principal:
    who = current_principal()
    if who is None or not who.authenticated:
        raise HTTPException(401, "authentication required")
    return who


def _page_path(slug: str, video_id: str) -> str:
    return f"/projects/{slug}/videos/{video_id}"


@router.get("/shared", response_class=HTMLResponse)
def shared_videos() -> str:
    who = who_is()
    videos = access.viewable_videos(who, _project_slugs())
    mine = requests_by(who.email)
    labels = {}
    for r in mine:
        found = access.find_video(r.slug, r.video_id)
        if found is not None:
            labels[(r.slug, r.video_id)] = found.label or "A video"
    return view.shared_page(videos, mine, labels)


def _share_panel_data(who: Principal, slug: str, res: ResourceRef,
                      video_id: str) -> tuple[str | None, list[str]] | None:
    if not authorize(who, K.VIDEO_SHARE, res):
        return None
    return access.live_link_since(slug, video_id), sorted(res.shared_with)


@router.get("/projects/{slug}/videos/{video_id}")
def video_page(slug: str, video_id: str) -> Response:
    """The player for a person with access; the request-access page (404, no bytes) otherwise,
    and the very same page for a video that does not exist."""
    who = who_is()
    res = access.video_resource(slug, video_id)
    source = access.find_video(slug, video_id)
    if res is None or source is None or not authorize(who, K.VIDEO_VIEW, res):
        known = latest_request(slug, video_id, who.email) if res is not None else None
        return HTMLResponse(view.request_access_page(
            _page_path(slug, video_id) + "/request-access", known), status_code=404)
    project = resource_for(slug)
    return HTMLResponse(view.player_page(
        slug, source, comments.list_comments(slug, video_id), viewer=who.email.lower(),
        moderator=authorize(who, K.COMMENT_CREATE, ResourceRef(project_slug=slug)),
        can_comment=authorize(who, K.COMMENT_CREATE, res),
        can_promote=authorize(who, K.PROJECT_EDIT, project),
        share=_share_panel_data(who, slug, res, video_id)))


@router.get("/projects/{slug}/videos/{video_id}/media")
def video_media(slug: str, video_id: str) -> Response:
    """The recording's bytes (range requests included). The gate has already answered 404 for
    anyone without `video.view` on this video; the file is found by id, not by a client path."""
    source = access.find_video(slug, video_id)
    path = access.media_path(slug, source) if source is not None else None
    if path is None:
        raise HTTPException(404, "no such video")
    kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=kind, filename=f"video{path.suffix}",
                        content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff"})


@router.post("/projects/{slug}/videos/{video_id}/share-link")
def create_share_link(request: Request, slug: str, video_id: str) -> Response:
    who = who_is()
    token = access.create_link(slug, video_id, who.email)
    audit.record_action(actor=who.email, target=f"{slug}:{video_id}", action="video.link.create")
    link = str(request.base_url).rstrip("/") + f"/v/{token}"
    return HTMLResponse(view.share_link_page(link, _page_path(slug, video_id)))


@router.post("/projects/{slug}/videos/{video_id}/share-link/revoke")
def revoke_share_link(slug: str, video_id: str) -> Response:
    who = who_is()
    access.revoke_links(slug, video_id)
    audit.record_action(actor=who.email, target=f"{slug}:{video_id}", action="video.link.revoke")
    return RedirectResponse(_page_path(slug, video_id), status_code=303)


@router.post("/projects/{slug}/videos/{video_id}/shares")
def change_shares(slug: str, video_id: str, email: str = Form(...),
                  change: str = Form("add")) -> Response:
    who = who_is()
    target = accounts.find_user(email)
    if target is None:
        raise HTTPException(400, "no account with that email")
    present = change != "remove"
    access.set_share(slug, video_id, target.email, present, who.email)
    audit.record_action(actor=who.email, target=f"{slug}:{video_id}:{target.email}",
                        action=f"video.share.{'add' if present else 'remove'}")
    return RedirectResponse(_page_path(slug, video_id), status_code=303)
