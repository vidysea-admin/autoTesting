"""Fixture for the T-174 CLI / MCP tests (qa/contracts/cli-mcp.md).

One job: seed an onboarded project with cases, and replace the browser and the grader with
fakes so a run is real in its control flow (the launcher's approval gate, tiers, persistence)
and offline in everything else. Not a test module.

`install_fakes(..., strict=True)` makes every outward-facing seam RAISE when touched -- the
dry-run proof (CM3) is that nothing reaches them. The fakes enter through `run_ops.RUN_SEAMS`
(the launcher's own `RunSeams`) and the same browser / grading seams `test_run_launcher_approval`
uses; there is no second launcher.
"""

from __future__ import annotations

import hashlib
import socket
from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import RawResult
from autotester.schema.verdict import Failure, Verdict
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import RunSeams
from autotester.store.project_store import ProjectStore

SECRET_KEY = "DEMO_PASSWORD"
SECRET_VALUE = "hunter2-planted-VALUE-9f3a"


def seed_project(root: Path, titles: tuple[str, ...] = ("ok",), *, secret: bool = False,
                 approve: bool = False) -> ProjectStore:
    """An onboarded `demo` project with one runnable case per title."""
    store = ProjectStore("demo", root)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key=SECRET_KEY, domains=["demo.test"])] if secret else [],
    ))
    for i, title in enumerate(titles):
        target = f"{{{{SECRET:{SECRET_KEY}}}}}" if secret else f"#t{i}"
        store.add_case(Case(
            project="demo", flow_id=f"flow-{i}", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
            title=title, steps=[Step(order=0, action=Action.CLICK, target=target)]))
    if secret:
        (root / ".env").write_text(f"{SECRET_KEY}={SECRET_VALUE}\n", encoding="utf-8")
    if approve:
        grant_live_case_approval(store, target="https://demo.test")
    return store


def install_fakes(monkeypatch: pytest.MonkeyPatch, results: dict[str, Result] | None = None,
                  *, judge_available: bool = True, strict: bool = False) -> None:
    """Fake browser + grader. `results` maps a case title to the verdict it gets.
    With `strict`, the browser, the grader and the network all raise on use."""
    import autotester.ui.run_execution as run_execution_module
    from autotester import run_ops
    from autotester.browser.session import BrowserSession

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("an outward-facing seam was touched")

    class _Judge:
        trace = None

        def __init__(self, _project: Project) -> None:
            if strict:
                boom()

        def available(self) -> bool:
            return judge_available

    def fake_run_and_grade(case_, session, judge, run_id, store_):
        result = (results or {}).get(case_.title, Result.PASS)
        failures = [] if result is Result.PASS else [Failure(
            criterion_id="c1", reason=f"expected the page to load with {SECRET_VALUE}")]
        raw = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED,
                        error=None if result is Result.PASS else f"saw {SECRET_VALUE}")
        return raw, Verdict(run_id=run_id, case_id=case_.id, result=result,
                            failures=failures, grader_provider="mock")

    plan = ParallelPlan(1, 1, 1, "config", 99999.0, 8)
    monkeypatch.setattr(run_ops, "RUN_SEAMS",
                        RunSeams(judge_factory=_Judge, planner=lambda *a, **k: plan))
    monkeypatch.setattr(BrowserSession, "start", boom if strict else lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        boom if strict else fake_run_and_grade)
    if strict:
        monkeypatch.setattr(socket.socket, "connect", boom)


def tree_hash(root: Path) -> str:
    """Digest of every path and byte under `root` -- identical before/after = nothing written."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
