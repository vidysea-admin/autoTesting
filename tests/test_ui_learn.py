"""The learning loop on screen — review, generate, and the video queue.

AT-241: a freshly onboarded product's ONLY route to being runnable was hand-
writing cases one at a time. INGEST was CLI-only, the review gate was CLI-only,
and EXPAND had no entry point at all — so T-100's own acceptance note ("full
onboarding -> report without touching the CLI") was false when driven in a real
browser, and the business-truth campaign proved it live.

These tests pin the three surfaces that close the cold start: the FlowSpec
review page (the gate, both directions, with a signer), the Generate-cases
button (EXPAND's UI entry point), and the video-request queue — the first place
the product's "ask me for a video" promise is visible to the human it asks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from litellm_fake import install

from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Screen, Step
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _spec(status: ReviewStatus) -> FlowSpec:
    return FlowSpec(
        project="demo", review=Review(status=status),
        screens=[Screen(id="scr_signin", name="Sign in", url_pattern="/signin")],
        flows=[Flow(
            id="flow-login", name="Sign in", entry_screen="scr_signin",
            steps=[
                Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
                Step(order=2, action=Action.FILL, target="Email", value="a@demo.test"),
                Step(order=3, action=Action.CLICK, target="Sign in"),
            ],
        )],
    )


def _project(root: Path, *, spec: FlowSpec | None = None, name: str = "Demo") -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name=name, base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    if spec is not None:
        store.save_flowspec(spec)
    return store


def _mock_generator(monkeypatch: pytest.MonkeyPatch, *, available: bool = True) -> None:
    class _Provider(MockProvider):
        def available(self) -> bool:
            return available

    provider = _Provider(responses={"agent": [ExpandedSteps(
        steps=[Step(order=1, action=Action.CLICK, target="Sign in")],
        rationale="exercises the class",
    )] * 60})
    import autotester.ui.routes_learn as routes_learn_module

    monkeypatch.setattr(routes_learn_module, "for_role", lambda project, role: provider)


# -- the review page ---------------------------------------------------------

def test_the_flowspec_page_shows_what_the_system_thinks_it_learned(
    client: TestClient, scratch_root: Path
) -> None:
    _project(scratch_root, spec=_spec(ReviewStatus.DRAFT))

    response = client.get("/projects/demo/flowspec")

    assert response.status_code == 200
    assert "Sign in" in response.text
    assert "/signin" in response.text
    assert "draft" in response.text
    assert "href='/projects/demo/sources'" in response.text
    assert "Add a recording" in response.text


def test_the_flowspec_page_of_a_project_with_no_flowspec_says_so_without_erroring(
    client: TestClient, scratch_root: Path
) -> None:
    """The cold-start page itself. This is the state a freshly onboarded product
    is in, so it is the one page that must never be a dead end or a 500."""
    _project(scratch_root)

    response = client.get("/projects/demo/flowspec")

    assert response.status_code == 200
    assert "no flowspec" in response.text.lower()


def test_the_flowspec_page_404s_an_unknown_project(
    client: TestClient, scratch_root: Path
) -> None:
    assert client.get("/projects/nope/flowspec").status_code == 404


def test_approving_from_the_ui_records_who_approved_it(
    client: TestClient, scratch_root: Path
) -> None:
    """review-gate R1-R3 reaching a non-technical operator. An approval nobody
    signed is not an approval, so `by` is carried through to disk."""
    store = _project(scratch_root, spec=_spec(ReviewStatus.DRAFT))

    response = client.post("/projects/demo/flowspec/approve",
                           data={"by": "umesh", "note": "looks right"},
                           follow_redirects=False)

    assert response.status_code == 303
    saved = store.load_flowspec()
    assert saved is not None
    assert saved.review.status is ReviewStatus.APPROVED
    assert saved.review.by == "umesh"


def test_approving_without_a_name_is_refused_and_changes_nothing(
    client: TestClient, scratch_root: Path
) -> None:
    store = _project(scratch_root, spec=_spec(ReviewStatus.DRAFT))

    response = client.post("/projects/demo/flowspec/approve", data={"by": "  "},
                           follow_redirects=False)

    assert response.status_code == 400
    assert "This review is not signed" in response.text
    assert "<title>" in response.text and '"detail"' not in response.text
    saved = store.load_flowspec()
    assert saved is not None
    assert saved.review.status is ReviewStatus.DRAFT


def test_the_gate_swings_both_ways_from_the_ui(
    client: TestClient, scratch_root: Path
) -> None:
    """A review page with only an Approve button is a rubber stamp, not a gate."""
    store = _project(scratch_root, spec=_spec(ReviewStatus.APPROVED))

    response = client.post("/projects/demo/flowspec/request-edit",
                           data={"by": "umesh", "note": "screen 2 is wrong"},
                           follow_redirects=False)

    assert response.status_code == 303
    saved = store.load_flowspec()
    assert saved is not None
    assert saved.review.status is ReviewStatus.NEEDS_EDIT
    assert saved.review.note == "screen 2 is wrong"


def test_an_undeclared_credential_placeholder_in_the_review_note_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """ui.md U8/U9's rule applied to the new door: `flowspec.json` is a
    git-tracked file in a public repo, so its free-text fields get the same
    guard the case form has."""
    store = _project(scratch_root, spec=_spec(ReviewStatus.DRAFT))

    response = client.post("/projects/demo/flowspec/approve",
                           data={"by": "umesh", "note": "{{SECRET:NOPE}}"},
                           follow_redirects=False)

    assert response.status_code == 400
    assert "This review cannot be saved" in response.text
    assert "Return to the review" in response.text and '"detail"' not in response.text
    saved = store.load_flowspec()
    assert saved is not None
    assert saved.review.status is ReviewStatus.DRAFT


# -- the generate button -----------------------------------------------------

def test_generate_creates_real_cases_in_the_projects_cases_file(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AT-239's UI half: EXPAND finally has a button. The cases must land in
    `cases.jsonl` — the same file the cases page lists and ▶ Run tests runs."""
    store = _project(scratch_root, spec=_spec(ReviewStatus.APPROVED))
    _mock_generator(monkeypatch)

    response = client.post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/projects/demo/cases"
    assert len(store.list_cases()) > 1


def test_generate_when_the_model_fails_midway_is_refused_as_a_page_not_a_500(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AT-264. Every other refusal in this route is a themed page; a
    `ProviderError` raised by the model mid-generation used to reach the
    operator as a raw `text/plain` 500 instead. Starved the mock's queue so it
    raises exactly the way `providers/gemini.py` does on an unparsed response
    or a schema mismatch -- not a synthetic exception, the real failure shape."""
    from autotester.providers.mock import MockProvider

    store = _project(scratch_root, spec=_spec(ReviewStatus.APPROVED))

    class _StarvedProvider(MockProvider):
        def available(self) -> bool:
            return True

    provider = _StarvedProvider(responses={"agent": []})  # empty queue -> ProviderError
    import autotester.ui.routes_learn as routes_learn_module

    monkeypatch.setattr(routes_learn_module, "for_role", lambda project, role: provider)

    response = client.post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "Internal Server Error" not in response.text
    assert "AutoTester" in response.text
    assert store.list_cases() == [], "a partial failure must not leave partial cases"


def test_generate_failure_page_does_not_carry_a_vendor_echoed_key(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AT-790 (LL8). The route prints the ProviderError on its refusal page, so a
    vendor error that echoes a vendor-native key must not get that far."""
    canary = "AIza-ROUTE-CANARY-555"
    store = _project(scratch_root, spec=_spec(ReviewStatus.APPROVED))
    install(monkeypatch, [RuntimeError(f"403 at https://vendor.test/x?key={canary}")] * 60)
    monkeypatch.setenv("LITELLM_API_KEY", "k-for-test")
    monkeypatch.setenv("GEMINI_API_KEY", canary)
    provider = LiteLLMProvider(model="gemini/gemini-2.5-pro")
    import autotester.ui.routes_learn as routes_learn_module

    monkeypatch.setattr(routes_learn_module, "for_role", lambda project, role: provider)

    response = client.post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 400 and "could not complete" in response.text
    assert canary not in response.text
    assert store.list_cases() == []


def test_generate_on_an_unapproved_flowspec_is_refused_as_a_page_not_raw_json(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two properties at once. The gate holds (expand.md X1), and the refusal an
    operator reaches by clicking a button is a themed page with a way onward —
    not the raw `{"detail": ...}` blob AT-244 was filed for."""
    store = _project(scratch_root, spec=_spec(ReviewStatus.DRAFT))
    _mock_generator(monkeypatch)

    response = client.post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert '"detail"' not in response.text
    assert "AutoTester" in response.text
    assert store.list_cases() == []


def test_generate_without_a_flowspec_is_refused_as_a_page(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _project(scratch_root)
    _mock_generator(monkeypatch)

    response = client.post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert store.list_cases() == []


def test_generate_without_a_configured_provider_is_refused_as_a_page(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _project(scratch_root, spec=_spec(ReviewStatus.APPROVED))
    _mock_generator(monkeypatch, available=False)

    response = client.post("/projects/demo/cases/generate", follow_redirects=False)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert store.list_cases() == []
