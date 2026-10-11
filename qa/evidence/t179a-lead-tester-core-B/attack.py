"""Blind black-box attack harness for t179a dispatcher. Scratch only; never imports the real .env."""
from __future__ import annotations

import base64
import contextlib
import io
import json
import logging
import math
import os
import re
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import quote

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
os.environ["AUTOTESTER_APPROVAL_KEY"] = "attack-harness-fake-signing-key-not-real"

from autotester.agents import tools  # noqa: E402
from autotester.agents.context import AgentContext  # noqa: E402
from autotester.browser.secrets import SecretStore  # noqa: E402
from autotester.providers.mock import MockProvider  # noqa: E402
from autotester.schema.agent_layer import AgentToolName, ToolOutcome  # noqa: E402
from autotester.schema.approval import RunApproval  # noqa: E402
from autotester.schema.case import Case  # noqa: E402
from autotester.schema.crawl import Crawl  # noqa: E402
from autotester.schema.enums import (  # noqa: E402
    Action, ApprovalKind, CaseClass, CaseKind, EvidenceKind, Outcome, Result, WritePolicy)
from autotester.schema.flowspec import Step  # noqa: E402
from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.schema.run import Evidence, RawResult  # noqa: E402
from autotester.schema.verdict import Criterion, Judgment, Rubric  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

BASE = "https://app.test"
CA, CB, CS = "CANARY_ALPHA_0xDEADBEEF_FAKE", "CANARY/BRAVO+0xCAFE=F00D&FAKE@1!", "CANARY_SHADOW_0xBADC0DE5_FAKE"
ENV = OUT / "scratch.env"  # NOT the repo .env
ENV.write_text(f"APP_PASS={CA}\nAPP_TOKEN={CB}\nOTHER_PROJ_KEY={CS}\n", encoding="utf-8")
CAN = {"A": CA, "B": CB, "S": CS}


def variants(v: str) -> dict[str, str]:
    b = v.encode()
    return {
        "raw": v, "b64": base64.b64encode(b).decode(), "b64url": base64.urlsafe_b64encode(b).decode(),
        "b64nopad": base64.b64encode(b).decode().rstrip("="), "b32": base64.b32encode(b).decode(),
        "hexl": b.hex(), "hexu": b.hex().upper(), "pct": quote(v, safe=""), "pct2": quote(quote(v, safe=""), safe=""),
        "rev": v[::-1], "upper": v.upper(), "lower": v.lower(), "spaced": " ".join(v.upper()),
        "zw": "​".join(v), "hexsp": " ".join(f"{c:02x}" for c in b),
    }


ALLV = [(f"{k}:{n}", s) for k, v in CAN.items() for n, s in variants(v).items()]
ALLV.sort(key=lambda t: -len(t[1]))


def leaks_in(text: str) -> list[str]:
    low = text.lower()
    found = []
    for label, s in ALLV:
        if s.lower() in low or s in text:
            found.append(label)
    # fold-insensitive check: strip punctuation/space
    squeezed = re.sub(r"[\s\-_.+~/:|,;!?*=^'\"`()\[\]{}<>\\​]+", "", text.lower())
    for k, v in CAN.items():
        if re.sub(r"[\s\-_.]+", "", v.lower()) in squeezed:
            found.append(f"{k}:fold")
    return sorted(set(found))


def lab(text: str) -> str:
    for label, s in ALLV:
        if len(s) >= 6:
            text = text.replace(s, f"<{label}>")
    return text


class Spy:
    def __init__(self) -> None:
        self.sessions = 0
        self.run_case = 0
        self.run_crawl = 0
        self.grade_prompts = 0


class _Session:
    def __enter__(self): return self
    def __exit__(self, *e): return None


REC: list[dict] = []
SPY = Spy()
_n = [0]
LOGBUF = io.StringIO()
_h = logging.StreamHandler(LOGBUF)
_h.setLevel(0)
logging.getLogger().addHandler(_h)
logging.getLogger().setLevel(0)


def project(policy=WritePolicy.READ_ONLY, slug="demo") -> Project:
    return Project(slug=slug, name="Demo", base_url=BASE, allowed_domains=["app.test"], write_policy=policy,
                   secrets=[SecretRef(key="APP_PASS", domains=["app.test"]),
                            SecretRef(key="APP_TOKEN", domains=["app.test"])])


def mkcase(steps, rubric=False, rubric_ref=None, slug="demo"):
    return Case(project=slug, flow_id="f1", kind=CaseKind.BEST, case_class=CaseClass.HAPPY, title="case",
                steps=steps, rubric_ref=rubric_ref or ("r1" if rubric else None))


NAV = Step(order=1, action=Action.NAVIGATE, target="/home")


def st(action, target="x", value=None, order=2):
    return Step(order=order, action=action, target=target, value=value)


def appr(kind, actions=50, wall=900.0, project_slug="demo", target=BASE, expires="2099-01-01", signed=True,
         key=None, tamper=None):
    a = RunApproval(project=project_slug, run_kind=kind, target=target, scope="attack fixture", max_actions=actions,
                    wall_clock_s=wall, granted_by="umesh", granted_at="2026-10-01", expires_at=expires)
    if signed:
        if key is not None:
            old = os.environ["AUTOTESTER_APPROVAL_KEY"]
            os.environ["AUTOTESTER_APPROVAL_KEY"] = key
            a = a.sign()
            os.environ["AUTOTESTER_APPROVAL_KEY"] = old
        else:
            a = a.sign()
    return a, tamper


def build(callroot: Path, policy, approvals, cases, extra_setup=None):
    prj = project(policy)
    store = ProjectStore("demo", callroot)
    store.paths.ensure()
    store.save_project(prj)
    for a, tamper in approvals:
        store.add_approval(a)
        if tamper:
            p = store.paths.approvals
            txt = p.read_text("utf-8")
            new = re.sub(tamper[0], tamper[1], txt)
            assert new != txt, "tamper no-op"
            p.write_text(new, "utf-8")
    ids = [store.add_case(c).id for c in cases]

    def open_session(observer):
        SPY.sessions += 1
        return _Session()

    judge = MockProvider(responses={"judge": [Judgment(result=Result.PASS)] * 3})
    ctx = AgentContext(project=prj, store=store, secrets=SecretStore.load(prj, ENV), judge=judge,
                       run_id="run-1", open_session=open_session)
    if extra_setup:
        extra_setup(ctx)
    return ctx, ids


ORIG_H = dict(tools._HANDLERS)
ORIG_CAT = tools.catalog.catalog


def install_spies(patch=None):
    tools._HANDLERS.clear(); tools._HANDLERS.update(ORIG_H)
    tools.catalog.catalog = ORIG_CAT
    def rc(case, session):
        SPY.run_case += 1
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    def crawl(*a, **k):
        SPY.run_crawl += 1
        return Crawl(project="demo")
    tools.execute.run_case = rc
    tools.explore.run_crawl = crawl
    if patch:
        patch()


def run(cat, desc, tool, args, *, policy=WritePolicy.READ_ONLY, approvals=(), cases=(), setup=None, patch=None,
        argsfn=None, judge=None):
    _n[0] += 1
    cid = _n[0]
    callroot = OUT / "calls" / f"c{cid:03d}"
    callroot.mkdir(parents=True, exist_ok=True)
    LOGBUF.seek(0); LOGBUF.truncate()
    SPY.sessions = SPY.run_case = SPY.run_crawl = 0
    install_spies(patch)
    ctx, ids = build(callroot, policy, list(approvals), list(cases), setup)
    if judge is not None:
        ctx.judge = judge
    a = argsfn(ids) if argsfn else args
    before_prompts = len(getattr(ctx.judge, "prompts", []))
    out = None
    exc_text = ""
    exc_type = ""
    ret_text = ""
    so, se = io.StringIO(), io.StringIO()
    t0 = time.monotonic()
    with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
        try:
            out = tools.dispatch(ctx, tool, a)
            ret_text = out.model_dump_json()
        except BaseException as e:  # noqa: BLE001 - the attack wants everything
            exc_type = type(e).__name__
            exc_text = "".join(traceback.format_exception(type(e), e, e.__traceback__, limit=40))[:200000]
    dt = time.monotonic() - t0
    arg_in_exc = False
    if exc_text:
        def strs(o, d=0):
            if d > 5: return
            if isinstance(o, str): yield o
            elif isinstance(o, dict):
                for k, v in list(o.items())[:50]:
                    yield from strs(k, d+1); yield from strs(v, d+1)
            elif isinstance(o, (list, tuple)):
                for v in o[:50]: yield from strs(v, d+1)
        try:
            arg_in_exc = any(len(x) >= 6 and len(x) < 5000 and x in exc_text for x in strs(a))
        except RecursionError:
            arg_in_exc = False
    prompts = getattr(ctx.judge, "prompts", [])[before_prompts:]
    files = []
    for p in callroot.rglob("*"):
        if p.is_file():
            try:
                files.append((str(p.relative_to(callroot)), p.read_text("utf-8", errors="ignore")))
            except OSError:
                pass
    leak_ret = leaks_in(ret_text)
    leak_exc = leaks_in(exc_text) if exc_text else []
    leak_files = sorted({f"{n}:{','.join(leaks_in(t))}" for n, t in files if leaks_in(t)})
    leak_logs = leaks_in(LOGBUF.getvalue() + so.getvalue() + se.getvalue())
    leak_prompt = sorted({x for _, p in prompts for x in leaks_in(p)})
    if out is not None:
        verdict = "EXECUTED" if out.ok else f"REFUSED:{out.refusal.value if out.refusal else '?'}"
        text = out.summary
    else:
        verdict = f"RAISED:{exc_type}"
        text = exc_text.strip().splitlines()[-1] if exc_text else ""
    REC.append(dict(n=cid, cat=cat, desc=lab(desc), tool=lab(str(tool))[:60], verdict=verdict,
                    text=lab(text)[:160].replace("\n", " "), browser=SPY.sessions, run_case=SPY.run_case,
                    run_crawl=SPY.run_crawl, grade_prompts=len(prompts), leak_ret=leak_ret, leak_exc=leak_exc,
                    leak_files=[lab(x) for x in leak_files], leak_logs=leak_logs, leak_prompt=leak_prompt,
                    secs=round(dt, 2), arg_in_exc=arg_in_exc))
    return out


exec(open(Path(__file__).with_name("attack_cases.py"), encoding="utf-8").read())

(OUT / "results.json").write_text(json.dumps(REC, indent=1), encoding="utf-8")
print(len(REC), "calls")
