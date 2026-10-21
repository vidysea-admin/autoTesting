"""Benchmark inputs a person supplies through the product (T-136 marks, T-218 answer list).

Routes: `GET /projects/{slug}/bench` (project.view), `POST /projects/{slug}/bench/marks` and
`POST /projects/{slug}/bench/atomic-list` (project.edit). The policy rows are in
`auth/policy.py`; the page renders the controls only for an account that may edit, and a request
without that permission is refused by the login gate before the handler runs. A mark is stored
beside the bench files (`stages/bench_marks.py`); the uploaded list goes under `.work/`
(`stages/bench_inputs.py`) and is never served back.
"""

from __future__ import annotations

import re
from html import escape

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.datastructures import UploadFile

from autotester.auth.context import current_principal
from autotester.stages import bench_inputs, bench_marks
from autotester.stages.acceptance_comparison import corpus_id_for
from autotester.ui import bench_inputs_view as view
from autotester.ui import theme
from autotester.ui.auth_middleware import safe_next
from autotester.ui.helpers import _load_project_or_404

router = APIRouter()

_KEY = re.compile(r"^[0-9a-f]{16}$")
_VERDICTS = {"real": "real", "false_positive": "false_positive", "clear": None}
_MAX_MARKS = 5000


def _who() -> str:
    who = current_principal()
    return who.email if who is not None and who.email else "unknown"


@router.get("/projects/{slug}/bench", response_class=HTMLResponse)
def bench_inputs_page(slug: str) -> str:
    store, project = _load_project_or_404(slug)
    marks = bench_marks.load_marks(store, corpus_id_for(slug))
    body = view.page_body(slug, project.name, marks, bench_inputs.load_pin(slug),
                          may_edit=view.may_mark(slug))
    return theme.page(f"{escape(project.name)} - benchmark inputs", body, active_slug=slug)


@router.post("/projects/{slug}/bench/marks")
def mark_finding(slug: str, finding: str = Form(""), verdict: str = Form(""),
                 next: str = Form("")) -> RedirectResponse:
    store, _project = _load_project_or_404(slug)
    if not _KEY.fullmatch(finding) or verdict not in _VERDICTS:
        raise HTTPException(400, "a finding and a ruling (real, false_positive or clear) are "
                                 "required")
    corpus_id = corpus_id_for(slug)
    ruling = _VERDICTS[verdict]
    stored = bench_marks.load_marks(store, corpus_id).marks
    if ruling is not None and finding not in stored and len(stored) >= _MAX_MARKS:
        raise HTTPException(400, "too many findings are already ruled on this project")
    bench_marks.set_mark(store, corpus_id, finding, ruling, _who())  # type: ignore[arg-type]
    target = safe_next(next)
    return RedirectResponse(
        target if target.startswith(f"/projects/{slug}/") else f"/projects/{slug}/bench",
        status_code=303)


@router.post("/projects/{slug}/bench/atomic-list")
async def upload_atomic_list(slug: str, request: Request) -> RedirectResponse:
    _load_project_or_404(slug)
    form = await request.form()
    upload = form.get("atomic_list")
    if not isinstance(upload, UploadFile):
        raise HTTPException(400, "choose the atomic answer list file to upload")
    raw = await upload.read(bench_inputs.MAX_BYTES + 1)
    try:
        bench_inputs.save_atomic_list(slug, raw, _who())
    except bench_inputs.ListRefused as exc:
        raise HTTPException(400, str(exc)) from None
    return RedirectResponse(f"/projects/{slug}/bench", status_code=303)
