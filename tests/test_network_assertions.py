"""T-170: first-party API/network assertions as evidence, during both a
crawl and a run. Contract: qa/contracts/network-assertions.md NA1-NA6.

`PageObserver` + `stages/network_capture.py` + `browser/assertions.py`'s
`network` field are exercised with fakes -- no real browser, same pattern as
`test_execute.py`/`test_observe.py`/`crawl_fake.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Outcome, WritePolicy
from autotester.schema.flowspec import ExpectedState, Step
from autotester.schema.project import Project, SecretRef
from autotester.stages import network_capture
from autotester.stages.execute import run_case
from autotester.store.project_store import ProjectStore

LOGIN = "https://app.pathlynks.test/login"


# -- fakes (test_execute.py's pattern) ---------------------------------------

class FakeLocator:
    def __init__(self, page: FakePage, selector: str) -> None:
        self.page, self.selector = page, selector

    def click(self) -> None:
        self.page.clicks.append(self.selector)

    def fill(self, value: str) -> None:
        self.page.filled[self.selector] = value

    def evaluate(self, script: str) -> None:
        return None

    def inner_text(self) -> str:
        return self.page.body_text

    def count(self) -> int:
        return 1


class FakePage:
    def __init__(self, url: str) -> None:
        self.url = url
        self.filled: dict[str, str] = {}
        self.clicks: list[str] = []
        self.shots: list[str] = []
        self.body_text = ""

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(self, selector)

    def add_style_tag(self, content: str) -> None:
        return None

    def screenshot(self, path: str, full_page: bool = False) -> None:
        self.shots.append(path)
        Path(path).write_bytes(b"png")

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url

    def wait_for_timeout(self, timeout: int) -> None:
        return None

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        return None


def make_project(*, secrets: list[SecretRef] | None = None) -> Project:
    return Project(slug="pathlynks", name="Pathlynks", base_url=LOGIN,
                   allowed_domains=["pathlynks.test"], secrets=secrets or [])


def session_with_fake_page(tmp_path: Path, project: Project, *, observed: bool = True,
                           env: str = "") -> BrowserSession:
    paths = ProjectPaths("pathlynks", tmp_path)
    (tmp_path / ".env").write_text(env, encoding="utf-8")
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    session = BrowserSession(project, secrets, tmp_path / "run", paths,
                             observer=PageObserver() if observed else None)
    session._page = FakePage(LOGIN)
    session.state.run_dir.mkdir(parents=True, exist_ok=True)
    return session


def make_case(steps: list[Step]) -> Case:
    return Case(project="pathlynks", flow_id="flow_x", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title="x", steps=steps)


# -- NA1: capture, every first-party response, independent of status --------

def test_na1_first_party_responses_are_captured_third_party_are_not() -> None:
    """Falsifiable per the contract: one first-party 200 + one third-party
    200 -> exactly one NETWORK evidence item, for the first-party call."""
    project = make_project()
    policy = SafetyPolicy(write_policy=WritePolicy.READ_ONLY)
    responses = [
        ("GET", "https://app.pathlynks.test/api/students", 200),
        ("GET", "https://cdn.unrelated-third.test/px.gif", 200),
    ]
    items = network_capture.first_party_evidence(responses, project, policy, Redactor({}))

    assert len(items) == 1
    assert items[0].kind is EvidenceKind.NETWORK
    assert "app.pathlynks.test/api/students" in items[0].path
    assert "-> 200" in items[0].path


def test_na1_captures_a_first_party_4xx_response_too_not_only_failures() -> None:
    """"not only the failing ones X9 already counts as CrawlIssue" -- a
    healthy 200 is captured exactly like a 500."""
    project = make_project()
    policy = SafetyPolicy(write_policy=WritePolicy.READ_ONLY)
    responses = [("GET", "https://app.pathlynks.test/api/x", 500)]
    items = network_capture.first_party_evidence(responses, project, policy, Redactor({}))

    assert len(items) == 1
    assert "-> 500" in items[0].path


def test_na1_run_case_folds_first_party_responses_into_evidence_every_run(
    tmp_path: Path,
) -> None:
    project = make_project()
    session = session_with_fake_page(tmp_path, project)
    session.observer.responses = [
        ("GET", "https://app.pathlynks.test/api/y", 200),
        ("GET", "https://analytics.unrelated.test/collect", 200),
    ]
    steps = [Step(order=1, action=Action.NAVIGATE, target=LOGIN)]
    result = run_case(make_case(steps), session)

    network = [e for e in result.evidence if e.kind is EvidenceKind.NETWORK]
    assert len(network) == 1
    assert "app.pathlynks.test/api/y" in network[0].path


# -- NA2: observation only, never judgement ----------------------------------

def test_na2_a_captured_error_status_alone_never_flips_the_outcome(tmp_path: Path) -> None:
    project = make_project()
    session = session_with_fake_page(tmp_path, project)
    session.observer.responses = [("GET", "https://app.pathlynks.test/api/broken", 500)]
    steps = [Step(order=1, action=Action.NAVIGATE, target=LOGIN)]  # no expected.network declared

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    assert any(e.kind is EvidenceKind.NETWORK for e in result.evidence)


def test_na2_no_grade_import_in_the_capture_path() -> None:
    import autotester.stages.network_capture as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "grade" not in src.lower()


# -- NA3: a declared network pattern gets a real met/unmet check ------------

def test_na3_a_matched_network_pattern_is_met_and_recorded(tmp_path: Path) -> None:
    project = make_project()
    session = session_with_fake_page(tmp_path, project)
    session.observer.responses = [("POST", "https://app.pathlynks.test/api/save", 200)]
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.ASSERT, target="",
             expected=ExpectedState(network=["/api/save"])),
    ]
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    asserts = [e for e in result.evidence
               if e.kind is EvidenceKind.NETWORK and e.path.startswith("assert network")]
    assert len(asserts) == 1
    assert "met" in asserts[0].path and "unmet" not in asserts[0].path


def test_na3_an_unmatched_network_pattern_is_unmet_and_fails_the_assertion(
    tmp_path: Path,
) -> None:
    project = make_project()
    session = session_with_fake_page(tmp_path, project)
    session.observer.responses = [("GET", "https://app.pathlynks.test/api/other", 200)]
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.ASSERT, target="",
             expected=ExpectedState(network=["/api/never-called"])),
    ]
    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ASSERTION_FAILED
    asserts = [e for e in result.evidence
               if e.kind is EvidenceKind.NETWORK and e.path.startswith("assert network")]
    assert len(asserts) == 1
    assert "unmet" in asserts[0].path


def test_na3_a_step_declaring_no_network_pattern_fabricates_no_evidence(
    tmp_path: Path,
) -> None:
    project = make_project()
    session = session_with_fake_page(tmp_path, project)
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.ASSERT, target="", expected=ExpectedState()),
    ]
    result = run_case(make_case(steps), session)

    asserts = [e for e in result.evidence if e.path.startswith("assert network")]
    assert asserts == []


# -- NA4: deterministic, no provider -----------------------------------------

def test_na4_no_provider_import_anywhere_in_the_capture_module() -> None:
    import autotester.stages.network_capture as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^(import|from) (anthropic|google)", src, re.MULTILINE)


# -- NA5: secrets never reach captured evidence ------------------------------

def test_na5_a_secret_value_in_a_captured_url_is_scrubbed(tmp_path: Path) -> None:
    project = make_project(secrets=[SecretRef(key="API_TOKEN", domains=["app.pathlynks.test"])])
    session = session_with_fake_page(tmp_path, project, env="API_TOKEN=hunter2\n")
    session.observer.responses = [
        ("GET", "https://app.pathlynks.test/api/x?token=hunter2", 200),
    ]
    steps = [Step(order=1, action=Action.NAVIGATE, target=LOGIN)]
    result = run_case(make_case(steps), session)

    network = [e for e in result.evidence if e.kind is EvidenceKind.NETWORK]
    assert len(network) == 1
    assert "hunter2" not in network[0].path
    assert "REDACTED" in network[0].path


# -- NA6: one capture mechanism, not two -------------------------------------

def test_na6_exactly_one_response_listener_exists_in_browser() -> None:
    src_dir = Path(__file__).parent.parent / "src" / "autotester" / "browser"
    hits = []
    for path in src_dir.glob("*.py"):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if 'on("response"' in line:
                hits.append(f"{path.name}:{lineno}")
    assert len(hits) == 1, hits
    assert hits[0].startswith("observe.py:"), hits


# -- crawl side: NA1 "every crawl" -------------------------------------------

def test_na1_crawl_folds_first_party_responses_into_stored_network_evidence(
    tmp_path: Path,
) -> None:
    from crawl_fake import grant_crawl_approval, make_session

    from autotester.stages.explore import run_crawl

    project = Project(slug="demo", name="Demo", base_url="https://app.test/",
                      allowed_domains=["app.test"])
    session, _page = make_session(tmp_path, project)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    observer = PageObserver()
    observer.responses = [
        ("GET", "https://app.test/api/home", 200),
        ("GET", "https://ads.unrelated-third.test/beacon", 200),
    ]
    crawl = run_crawl(project, session, store, observer=observer, bounds=CrawlBounds())

    network = store.list_crawl_network(crawl.id)
    assert len(network) == 1
    assert "app.test/api/home" in network[0].path
