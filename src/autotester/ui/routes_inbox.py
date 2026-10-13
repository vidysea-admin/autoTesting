"""The website inbox, `GET /inbox` ("My reports", T-201 TT7; the owner-visible half of T-200
TS5/TS7 reads the same list). One job: show the signed-in person the requests whose report they
may read. The login gate requires `report.view` somewhere (route policy); each row is filtered
by `report.view` on its own project, so nothing the viewer may not read is listed.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from autotester.auth.context import current_principal
from autotester.stages.report_delivery import inbox_for
from autotester.ui import inbox_view
from autotester.ui.run_queue import get_queue

router = APIRouter()


@router.get("/inbox", response_class=HTMLResponse)
def inbox() -> str:
    who = current_principal()
    if who is None or not who.authenticated:
        raise HTTPException(401, "sign in to see your reports")
    return inbox_view.inbox_page(inbox_for(who, get_queue().snapshot()))
