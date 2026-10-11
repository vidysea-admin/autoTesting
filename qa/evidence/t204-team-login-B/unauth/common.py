"""Blind-check harness (read-only toward the repo): drives the app in-process over raw ASGI.

Usage: common.setup(mode, scratch_dir) BEFORE importing autotester. Everything here writes
only under the scratch dir it is handed.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import unquote

SENT = {
    "alpha": "SENTINEL-ALPHA-PW-9d41c7",
    "beta": "SENTINEL-BETA-PW-3b7e22",
    "video": "SENTINEL-VIDEO-BYTES-55aa",
    "case": "SENTINEL-CASE-TITLE-71f0",
}
PW = "scratch-" + secrets.token_hex(8)
STATE = {"n": 0, "mode": "", "root": None}
LOOP = asyncio.new_event_loop()


def setup(mode: str, scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    STATE["mode"], STATE["root"] = mode, scratch
    os.environ["AUTOTESTER_ROOT"] = str(scratch)
    os.environ["AUTOTESTER_TEST_NO_AUTO_LOGIN"] = "1"
    os.environ["AUTOTESTER_ALLOWED_HOSTS"] = "testserver"
    for k in ("AUTOTESTER_AUTH_DIR", "AUTOTESTER_AUTH_DISABLED", "AUTOTESTER_HOSTED",
              "AUTOTESTER_FIRST_ADMIN_EMAIL", "AUTOTESTER_COOKIE_SECURE",
              "AUTOTESTER_ALLOWED_ORIGINS", "AUTOTESTER_SESSION_HOURS", "UVICORN_HOST"):
        os.environ.pop(k, None)
    if mode == "hosted":
        os.environ["AUTOTESTER_HOSTED"] = "1"
        os.environ["AUTOTESTER_ALLOWED_ORIGINS"] = "http://testserver,https://testserver"
        os.environ["AUTOTESTER_COOKIE_SECURE"] = "0"
        os.environ["AUTOTESTER_FIRST_ADMIN_EMAIL"] = "admin-b@scratch.test"


def host() -> str:
    return "testserver" if STATE["mode"] == "hosted" else "localhost:8000"


def good_origin() -> str:
    return "http://" + host()


class Resp:
    def __init__(self, status, headers, body, exc=None):
        self.status, self.headers, self.body, self.exc = status, headers, body, exc

    def h(self, name):
        return [v for k, v in self.headers if k == name.lower()]

    @property
    def text(self):
        return self.body.decode("utf-8", "replace")

    @property
    def location(self):
        v = self.h("location")
        return v[0] if v else None


def call(method, raw_path, headers=(), body=b"", query="", client="198.51.100.7",
         with_host=True, host_override=None) -> Resp:
    from autotester.ui.app import app
    STATE["n"] += 1
    hs = [(k.lower(), v) for k, v in headers]
    if with_host and not any(k == "host" for k, _ in hs):
        hs.append(("host", host_override or host()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": method, "scheme": "http", "path": unquote(raw_path),
             "raw_path": raw_path.encode("latin-1", "replace"),
             "query_string": query.encode("latin-1", "replace"), "root_path": "",
             "headers": [(k.encode("latin-1"), v.encode("latin-1")) for k, v in hs],
             "client": (client, 50000), "server": ("testserver", 80), "state": {}}
    out = {"status": None, "headers": [], "body": b""}
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.sleep(3600)

    async def send(msg):
        if msg["type"] == "http.response.start":
            out["status"] = msg["status"]
            out["headers"] = [(k.decode("latin-1").lower(), v.decode("latin-1"))
                              for k, v in msg["headers"]]
        elif msg["type"] == "http.response.body":
            out["body"] += msg.get("body", b"")

    exc = None
    try:
        LOOP.run_until_complete(asyncio.wait_for(app(scope, receive, send), 30))
    except BaseException as e:  # noqa: BLE001
        exc = repr(e)[:200]
    return Resp(out["status"], out["headers"], out["body"], exc)


def snapshot(root: Path) -> dict[str, tuple[int, str]]:
    snap = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            try:
                data = p.read_bytes()
            except OSError:
                continue
            snap[p.relative_to(root).as_posix()] = (len(data), hashlib.sha256(data).hexdigest()[:16])
    return snap


def diff(a, b):
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            out.append(("added" if k not in a else "removed" if k not in b else "changed", k))
    return out


def seed() -> dict:
    """Accounts, groups, projects, sentinel creds, one run with a video."""
    from autotester.auth import accounts, groups
    from autotester.auth.access import set_owner
    from autotester.browser.secrets import SecretStore  # noqa: F401
    from autotester.schema.case import Case
    from autotester.schema.enums import (CaseClass, CaseKind, EvidenceKind, Outcome, Result)
    from autotester.schema.project import Project, SecretRef
    from autotester.schema.run import Evidence, RawResult, Run
    from autotester.schema.verdict import Verdict
    from autotester.store.project_store import ProjectStore
    from autotester.ui.env_editor import set_env_value

    root = STATE["root"]
    gid = {g.seed: g.id for g in groups.list_groups()}
    ids = {}
    for name, seedname in (("admin", None), ("dev", "developer"), ("tester", "tester"),
                           ("sub", "sub-admin"), ("nogroup", None)):
        u = accounts.signup(f"{name}-b@scratch.test", PW, STATE["mode"] == "hosted")
        if seedname:
            accounts.set_user_groups(u.id, [gid[seedname]])
        ids[name] = u.id
    ids["_admin_group"] = gid["admin"]
    run_id = "runb1"
    for slug, owner, key, val in (("alpha", "dev", "ALPHA_PASSWORD", SENT["alpha"]),
                                  ("beta", "admin", "BETA_PASSWORD", SENT["beta"]),
                                  ("gamma", "admin", "GAMMA_PASSWORD", "gamma-not-sentinel")):
        st = ProjectStore(slug, root)
        st.save_project(Project(slug=slug, name=f"{slug.title()} Co", base_url=f"https://{slug}.test",
                                allowed_domains=[f"{slug}.test"],
                                secrets=[SecretRef(key=key, domains=[f"{slug}.test"])]))
        set_env_value(root / ".env", key, val)
        set_owner(slug, ids[owner])
    st = ProjectStore("alpha", root)
    case = Case(id="case_a1", project="alpha", flow_id="flow_login", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title=SENT["case"])
    st.add_case(case)
    st.save_run(Run(id=run_id, project="alpha", case_ids=["case_a1"]))
    rd = st.paths.run_dir(run_id)
    (rd / "video.webm").write_bytes(SENT["video"].encode())
    st.save_result(run_id, RawResult(case_id="case_a1", outcome=Outcome.COMPLETED,
                                     evidence=[Evidence(kind=EvidenceKind.VIDEO, path="video.webm",
                                                        masked=True)]))
    st.save_verdict(run_id, Verdict(run_id=run_id, case_id="case_a1", result=Result.FAIL,
                                    criteria_met=0, criteria_total=1, grader_provider="mock"))
    ids["run"] = run_id
    return ids


def session_cookie(user_id: int) -> str:
    from autotester.auth.sessions import create_session
    return "at_session=" + create_session(user_id)


def routes():
    """(method, path template, route class name) for every route incl. mounts."""
    from autotester.ui.app import app
    out, pending = [], list(app.routes)
    while pending:
        r = pending.pop()
        inner = getattr(r, "original_router", None)
        if inner is not None:
            pending.extend(inner.routes)
            continue
        ms = sorted(getattr(r, "methods", None) or ())
        out.append((ms, r.path, type(r).__name__))
    return out


def fill(template: str, ids: dict, real: bool, fuzz: str | None = None) -> str:
    vals = {"slug": "alpha" if real else "nosuchproject", "run_id": ids["run"] if real else "run1",
            "case_id": "case_a1" if real else "c1", "user_id": str(ids["admin"] if real else 7),
            "group_id": str(ids["_admin_group"] if real else 9), "key": "ALPHA_PASSWORD" if real else "K",
            "video_path": "video.webm", "name": "a.png", "action": "disable" if real else "x"}

    def rep(m):
        name = m.group(1).split(":")[0]
        if fuzz is not None:
            return fuzz
        return vals.get(name, "x1")
    return re.sub(r"\{([^}]+)\}", rep, template)


def leaks(resp: Resp) -> list[str]:
    return [k for k, v in SENT.items() if v in resp.text or v.encode() in resp.body]


def dump(name: str, obj) -> None:
    p = Path(__file__).parent / f"{name}-{STATE['mode']}.json"
    p.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
