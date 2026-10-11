"""Shared harness for the r1-B attack tables (t179a-lead-tester-core, fix cycle 1).

Import from a probe script run as:  <copy>/.venv/Scripts/python -I <probe.py> <copy-root> <out.json>
The first thing every probe does is `confirm_copy(copy_root)`: autotester.__file__ must sit inside it.
Everything is offline: execute.run_case / explore.run_crawl / grade.grade / catalog.catalog are spies,
open_session is a counting fake, secrets are FAKE canaries, each row gets its own temp data root.
Outputs carry LABELS (<APP_PASS>), never the canary values.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "r1b-probe-signing-key-not-real")

import autotester  # noqa: E402


def confirm_copy(copy_root: str) -> str:
    f = Path(autotester.__file__).resolve()
    root = Path(copy_root).resolve()
    assert root in f.parents, f"autotester imported from {f}, not inside {root}"
    print("autotester.__file__ =", f)
    return str(f)


from autotester.agents import guards, tools  # noqa: E402
from autotester.agents.context import AgentContext  # noqa: E402
from autotester.browser.secrets import SecretStore  # noqa: E402
from autotester.providers.mock import MockProvider  # noqa: E402
from autotester.schema.approval import RunApproval  # noqa: E402
from autotester.schema.case import Case  # noqa: E402
from autotester.schema.enums import (  # noqa: E402
    Action, ApprovalKind, CaseClass, CaseKind, Outcome, WritePolicy)
from autotester.schema.flowspec import Step  # noqa: E402
from autotester.schema.project import Project, SecretRef  # noqa: E402
from autotester.schema.run import RawResult  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402

BASE = "https://app.test"
DOMAIN = "app.test"
CANARY = {"APP_PASS": "Cnry-PASS-7Qx41-zeta-0993", "APP_USER": "cnry.user.5581@fake.test"}
LABEL = {v: f"<{k}>" for k, v in CANARY.items()}
POLICIES = [WritePolicy.READ_ONLY, WritePolicy.TEST_ACCOUNT, WritePolicy.ALLOW_WRITES]
MUTATING = {Action.CLICK, Action.PRESS_KEY, Action.FILL, Action.SELECT, Action.UPLOAD}


def label(text: Any) -> str:
    s = text if isinstance(text, str) else repr(text)
    for v, lab in LABEL.items():
        s = s.replace(v, lab)
    return s


def tree_state(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def tree_hash(root: Path) -> str:
    return hashlib.sha256(json.dumps(tree_state(root), sort_keys=True).encode()).hexdigest()


class Spies:
    def __init__(self) -> None:
        self.run_case: list[Case] = []
        self.crawl = 0
        self.grade = 0
        self.catalog = 0
        self.sessions = 0
        self.result_factory = None  # callable(case) -> RawResult
        self.raise_in: dict[str, BaseException] = {}


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def install_spies(spy: Spies) -> None:
    def fake_run_case(case: Case, session: Any) -> RawResult:
        spy.run_case.append(case)
        if "run_case" in spy.raise_in:
            raise spy.raise_in["run_case"]
        if spy.result_factory:
            return spy.result_factory(case)
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    tools.execute.run_case = fake_run_case  # type: ignore[assignment]

    def fake_crawl(*a: Any, **k: Any) -> Any:
        spy.crawl += 1
        if "crawl" in spy.raise_in:
            raise spy.raise_in["crawl"]
        from autotester.schema.crawl import Crawl
        return Crawl(project="demo")

    tools.explore.run_crawl = fake_crawl  # type: ignore[assignment]

    def fake_grade(rubric: Any, result: Any, run_id: str, *a: Any, **k: Any) -> Any:
        spy.grade += 1
        if "grade" in spy.raise_in:
            raise spy.raise_in["grade"]
        from autotester.schema.enums import Result
        from autotester.schema.verdict import Verdict
        if getattr(spy, "verdict_factory", None):
            return spy.verdict_factory(rubric, result, run_id)
        return Verdict(run_id=run_id, case_id=result.case_id, rubric_hash="h", result=Result.PASS,
                       grader_provider="mock")

    tools.grade.grade = fake_grade  # type: ignore[assignment]

    def fake_catalog(*a: Any, **k: Any) -> Any:
        spy.catalog += 1
        if "catalog" in spy.raise_in:
            raise spy.raise_in["catalog"]
        from autotester.schema.catalog import Catalog
        return Catalog(project="demo")

    tools.catalog.catalog = fake_catalog  # type: ignore[assignment]


def make_project(policy: WritePolicy, login_case_id: str | None = None,
                 declared: tuple[str, ...] = ("APP_PASS", "APP_USER"),
                 domains: tuple[str, ...] = (DOMAIN,)) -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=list(domains),
                   write_policy=policy, login_case_id=login_case_id,
                   secrets=[SecretRef(key=k, domains=[DOMAIN]) for k in declared])


def step(order: int, action: Action, target: str = "", value: str | None = None) -> Step:
    return Step(order=order, action=action, target=target, value=value)


def make_case(steps: list[Step], flow: str = "f1") -> Case:
    return Case(project="demo", flow_id=flow, kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="case", steps=steps)


def grant(store: ProjectStore, kind: ApprovalKind = ApprovalKind.LIVE_CASE, actions: int = 500,
          target: str = BASE) -> None:
    store.add_approval(RunApproval(
        project="demo", run_kind=kind, target=target, scope="r1b probe", max_actions=actions,
        wall_clock_s=900.0, granted_by="umesh", granted_at="2026-10-01",
        expires_at="2099-01-01").sign())


class Env:
    def __init__(self, ctx: AgentContext, spy: Spies, root: Path, case_ids: list[str]) -> None:
        self.ctx, self.spy, self.root, self.case_ids = ctx, spy, root, case_ids


def make_env(policy: WritePolicy, cases: list[list[Step]] | None = None, *,
             login_index: int | None = None, declared: tuple[str, ...] = ("APP_PASS", "APP_USER"),
             domains: tuple[str, ...] = (DOMAIN,), secret_values: dict[str, str] | None = None,
             approvals: bool = True, root: Path | None = None) -> Env:
    """Fresh temp data root; cases stored; login_index picks which case is the declared login."""
    root = root or Path(tempfile.mkdtemp(prefix="r1b-", dir=os.environ.get("R1B_TMP")))
    spy = Spies()
    install_spies(spy)
    project = make_project(policy, None, declared, domains)
    store = ProjectStore("demo", root)
    store.paths.ensure()
    store.save_project(project)
    ids = []
    for i, steps in enumerate(cases or []):
        c = store.add_case(make_case(steps, flow=f"f{i}"))
        ids.append(c.id)
    if login_index is not None:
        project = project.model_copy(update={"login_case_id": ids[login_index]})
    if approvals:
        grant(store)
    secrets = SecretStore(project, dict(secret_values or CANARY))

    def open_session(observer: object) -> Any:
        spy.sessions += 1
        return _Session()

    ctx = AgentContext(project=project, store=store, secrets=secrets, judge=MockProvider(),
                       run_id="run-1", open_session=open_session)
    return Env(ctx, spy, root, ids)


def run_case_row(env: Env, idx: int = 0) -> dict[str, Any]:
    """Call the real dispatch for run_case; return the facts about it."""
    before = tree_state(env.root)
    runs0, sess0 = len(env.spy.run_case), env.spy.sessions
    t0 = time.perf_counter()
    try:
        out = tools.dispatch(env.ctx, "run_case", {"case_id": env.case_ids[idx]})
        exc = None
    except BaseException as e:  # noqa: BLE001 - recorded, never swallowed silently
        out, exc = None, f"{type(e).__name__}: {label(str(e))[:200]}"
    dt = time.perf_counter() - t0
    after = tree_state(env.root)
    changed = sorted(k for k in after if before.get(k) != after[k])
    executed = len(env.spy.run_case) - runs0
    return {
        "executed": executed > 0, "run_case_calls": executed, "sessions": env.spy.sessions - sess0,
        "ok": None if out is None else out.ok,
        "refusal": None if out is None or out.refusal is None else out.refusal.value,
        "summary": None if out is None else label(out.summary)[:160],
        "files_written": changed, "n_files_written": len(changed), "raised": exc,
        "seconds": round(dt, 4),
    }


def goto_would_refuse(project: Project, secrets: SecretStore, url: str) -> str | None:
    """Run the REAL BrowserSession.goto (fake page) from this copy: None if it would navigate,
    else the exception class name that stops it."""
    from autotester.browser.session import BrowserSession

    class Page:
        url = "about:blank"

        def goto(self, real: str, **kw: Any) -> None:
            self.url = real

    s = object.__new__(BrowserSession)
    s.project, s.secrets, s._page, s.budget = project, secrets, Page(), None
    s._record = lambda *a, **k: None  # type: ignore[method-assign]
    try:
        s.goto(url)
    except Exception as e:  # noqa: BLE001
        return type(e).__name__
    return None


def spellings(secret: str) -> dict[str, str]:
    raw = secret.encode()
    return {
        "raw": secret, "reversed": secret[::-1],
        "base64": base64.b64encode(raw).decode(), "base64url": base64.urlsafe_b64encode(raw).decode(),
        "base32": base64.b32encode(raw).decode(), "hex": raw.hex(),
        "percent": "".join(f"%{b:02x}" for b in raw), "upper": secret.upper(), "lower": secret.lower(),
        "spaced": " ".join(secret), "dotted": ".".join(secret),
    }


def dump(path: str, obj: Any) -> None:
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=True, default=str), encoding="utf-8")
