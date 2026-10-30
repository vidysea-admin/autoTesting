"""POST /projects/{slug}/videos/{video_id}/review: the "Run review" button (TA5, TV7).

One job: turn the form into the SAME `stages.video_review.run_review` call that
`autotester ingest review` makes, with the same gate (`cli_video_review.build_gate`: permission,
then a signed per-use approval wide enough for the plan). The login gate's `video` rule already
answers 404 (cannot see the video) or 403 (lacks `video.upload`); the gate's permission step
re-checks it. Secrets are scrubbed by the stage before any model call. The stored review is
shown on the video page.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from autotester import providers
from autotester.auth import audit
from autotester.auth.access import authorize
from autotester.auth.context import current_principal
from autotester.browser.secrets import SecretStore
from autotester.cli_video_review import build_gate
from autotester.media.probe import probe
from autotester.providers.base import Provider, ProviderError
from autotester.schema.auth import PermissionKey
from autotester.stages import video_access as access
from autotester.stages.analyze_video import load_transcript
from autotester.stages.video_pointers import MAX_POINTER_FILE_BYTES
from autotester.stages.video_review import (
    PointerErrors,
    ReviewRefused,
    preview_review,
    run_review,
    unreadable_reason,
)
from autotester.store.project_store import ProjectStore
from autotester.store.run_store import local_blob
from autotester.ui.video_review_view import review_refusal_page

router = APIRouter()


def default_provider(store: ProjectStore) -> Provider:
    """The project's first configured vision provider (the model chain default)."""
    project = store.load_project()
    names = project.providers.vision_ensemble() if project else []
    try:
        return providers.get(names[0])
    except (IndexError, ProviderError) as exc:
        raise ReviewRefused(f"no model provider is configured here ({exc})") from exc


provider_factory = default_provider
"""Seam: tests swap this for a recording fake; production uses the project's chain."""
probe_fn = probe
frames_fn = None   # None = the stage's own RedactedFrames (ffmpeg); tests pass a fake


def _page(slug: str, video_id: str) -> str:
    return f"/projects/{slug}/videos/{video_id}"


@router.post("/projects/{slug}/videos/{video_id}/review")
def run_video_review(slug: str, video_id: str, pointers: str = Form("")) -> Response:
    who = current_principal()
    if who is None or not who.authenticated:
        raise HTTPException(401, "authentication required")
    source, res = access.find_video(slug, video_id), access.video_resource(slug, video_id)
    if source is None or res is None or not source.path:
        raise HTTPException(404, "no such video")
    back = _page(slug, video_id)
    if len(pointers.encode("utf-8")) > MAX_POINTER_FILE_BYTES:
        return HTMLResponse(review_refusal_page(back, "Pointers too long", [
            "The pointer text is over the size limit; nothing was sent to a model."]), 400)
    store = ProjectStore(slug)
    video = access.media_path(slug, source) or local_blob(Path(source.path))

    def permission() -> None:
        if not authorize(who, PermissionKey.VIDEO_UPLOAD, res):
            raise ReviewRefused("you do not have permission to run a review on this video")

    try:
        permission()
        if why := unreadable_reason(video, probe_fn):
            return HTMLResponse(review_refusal_page(back, "Recording unreadable", [why]), 422)
        prov = provider_factory(store)
        if not prov.available():
            raise ReviewRefused(f"provider '{prov.id}' is not available here (no credentials)")
        plan_fn = partial(preview_review, video, pointers, [], provider_label=prov.label,
                          probe_fn=probe_fn)
        gate = build_gate(store, slug, prov, plan_fn, permission)
        secrets = SecretStore.load(store.load_project(), store.paths.env_file,
                                   strict=False).scrub_values()
        extra = {"frames_fn": frames_fn} if frames_fn is not None else {}
        run_review(store.paths, source, video, prov, load_transcript(store, source), gate=gate,
                   secrets=secrets, pointer_text=pointers, probe_fn=probe_fn, **extra)
    except PointerErrors as exc:
        lines = [f"line {e.line_no}: {e.reason}" for e in exc.parse.errors]
        return HTMLResponse(review_refusal_page(back, "Pointers refused", [
            "Nothing was sent to a model.", *lines]), 400)
    except ReviewRefused as exc:
        return HTMLResponse(review_refusal_page(back, "Review not run", [str(exc)]), 403)
    audit.record_action(actor=who.email, target=f"{slug}:{video_id}", action="video.review.run")
    return RedirectResponse(back + "#review", status_code=303)
