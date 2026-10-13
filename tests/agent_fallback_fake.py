"""Fixtures for tests/test_agent_fallback.py's pipeline (AF5) tests: a fake demo product."""

from __future__ import annotations

from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.mock import MockProvider
from autotester.schema.case import AgentFix, Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.verdict import Judgment
from autotester.store.project_store import ProjectStore

DEMO = "https://demo.test/"


def demo_case() -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="open home", rationale="home opens",
                steps=[Step(order=1, action=Action.NAVIGATE, target="https://elsewhere.example/")])


def demo_env(tmp_path: Path):
    project = Project(slug="demo", name="Demo", base_url=DEMO, allowed_domains=["demo.test"])
    store = ProjectStore("demo", tmp_path)
    store.save_project(project)
    paths = ProjectPaths("demo", tmp_path)
    session = BrowserSession(project, SecretStore.load(project, paths.env_file, strict=False),
                             tmp_path / "run", paths)
    session._page = type("P", (), {
        "url": DEMO, "add_style_tag": lambda s, content: None,
        "screenshot": lambda s, path, full_page=False: Path(path).write_bytes(b"png"),
        "goto": lambda s, url, wait_until="": setattr(s, "url", url),
        "wait_for_load_state": lambda s, *a, **k: None,
        "wait_for_timeout": lambda s, *a: None})()
    session.state.run_dir.mkdir(parents=True, exist_ok=True)
    return store, session


def judge() -> MockProvider:
    ok = Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")
    return MockProvider(responses={"judge": [ok, ok]})


def fix_agent() -> MockProvider:
    fix = AgentFix(action=Action.NAVIGATE, target=DEMO + "home", reasoning="stay on the product")
    return MockProvider(responses={"agent": [fix]})
