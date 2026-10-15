"""Offline sessions and typed fixtures for the downstream checkpoint adapters."""

from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession, check_destination
from autotester.providers.mock import MockProvider
from autotester.schema.approval import RunApproval
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, ApprovalKind, EvidenceKind, Result, SourceKind
from autotester.schema.flowspec import Flow, FlowSpec, SourceRef, Step
from autotester.schema.project import Project, Source
from autotester.schema.run import Evidence
from autotester.schema.verdict import Judgment
from autotester.stages.expand import applicable_classes
from autotester.stages.orchestrate import StageContext
from autotester.stages.orchestrate_downstream import downstream_runners
from autotester.store.filestore import write_json
from autotester.store.project_store import ProjectStore


class DownstreamSession(BrowserSession):
    """Exercise actual execution/replay code without launching a browser."""

    instances: ClassVar[list] = []

    def start(self):
        self._page = SimpleNamespace(url="about:blank")
        self.calls = []
        self.closed = False
        self.entry_profile_clean = not (self.paths.profile_dir / "prior-login").exists()
        self.state.run_dir.mkdir(parents=True, exist_ok=True)
        self.instances.append(self)
        return self

    def goto(self, url):
        check_destination(self.project, url)
        self.calls.append(url)
        self._page.url = url

    def settle(self, expected):
        pass

    def screenshot(self, name, step_order=None):
        self.state.evidence.append(Evidence(kind=EvidenceKind.URL, path=self.page.url,
                                            step_order=step_order))

    def close(self):
        self.closed = True


def downstream_fixture(tmp_path: Path, *, grant=True):
    store = ProjectStore("demo", tmp_path)
    project = Project(slug="demo", name="Demo", base_url="https://demo.test/login",
                      allowed_domains=["demo.test"])
    store.save_project(project)
    source = store.add_source(Source(project="demo", kind=SourceKind.TEXT,
                                     text="open the home page"))
    flow = Flow(id="flow-home", name="Home", entry_screen="scr-home", kind="ideal",
                steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/home",
                            source_ref=SourceRef(source_id=source.id))])
    spec = FlowSpec(project="demo", flows=[flow])
    model_ref = store.paths.pipeline_artifact("run-downstream", "model")
    write_json(model_ref, spec)
    generator = MockProvider(responses={"agent": [
        ExpandedSteps(steps=[], rationale="not applicable") for _ in applicable_classes(flow)]})
    judge = MockProvider(responses={"judge": [Judgment(result=Result.INCONCLUSIVE,
                                                      criteria_total=1, criteria_met=0,
                                                      scoreboard="offline fixture")
                                          for _ in range(20)]})
    if grant:
        store.add_approval(RunApproval(project="demo", run_kind=ApprovalKind.LIVE_CASE,
                                      target=project.base_url, scope="offline fixture",
                                      max_actions=100, max_probes=100, wall_clock_s=10000,
                                      granted_by="fixture", granted_at="2026-10-15",
                                      expires_at="2099-01-01").sign())
    secrets = SecretStore.load(project, store.paths.env_file, strict=False)
    DownstreamSession.instances = []
    runners = downstream_runners(project, store, generator=generator, judge=judge,
                                 session_cls=DownstreamSession)
    ctx = StageContext(store=store, run_id="run-downstream", runners=runners, secrets=secrets)
    return store, project, spec, str(model_ref), generator, judge, ctx
