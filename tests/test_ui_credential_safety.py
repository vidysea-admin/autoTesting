"""The credential path, end to end and safe. Contract: qa/contracts/ui.md U3.

Track 0, Unit 0.2. Before this, a user handed a password had no safe place to
put it in a test step: `cases.jsonl` is not gitignored, and a literal value
carries no `{{SECRET:KEY}}` placeholder, so `session.fill` never tags the field
and it appears in cleartext in every screenshot. A mistyped key surfaced only
mid-run as a stringified `UndeclaredSecret`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.schema.enums import Action, CaseClass
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

REAL_PASSWORD = "hunter2-this-is-the-real-one"


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _project_with_credential(client: TestClient, scratch_root: Path, *, value: str = "") -> None:
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": "demo.test",
    })
    client.post("/projects/demo/secrets", data={
        "key": "DEMO_PASSWORD", "domains": "demo.test", "mask_in_screenshot": "on",
    })
    if value:
        (scratch_root / ".env").write_text(f"DEMO_PASSWORD={value}\n", encoding="utf-8")


def _add_case(client: TestClient, value: str):
    return client.post("/projects/demo/cases", data={
        "title": "Log in", "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.FILL.value], "step_target": ["input[type=password]"],
        "step_value": [value], "step_expected": [""],
    }, follow_redirects=False)


# -- the plaintext hole ------------------------------------------------------

def test_pasting_the_real_credential_into_a_step_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = _add_case(client, REAL_PASSWORD)

    assert response.status_code == 400
    assert "looks like it contains a real credential" in response.text
    assert "a Value box" in response.text  # the message names the field (AT-077)
    assert ProjectStore("demo", scratch_root).list_cases() == []


def test_the_refused_value_never_reaches_the_cases_file(
    client: TestClient, scratch_root: Path
) -> None:
    """`cases.jsonl` is not gitignored — a leak here is a leak into the repo."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    _add_case(client, REAL_PASSWORD)

    cases_file = scratch_root / "projects" / "demo" / "cases.jsonl"
    assert not cases_file.exists() or REAL_PASSWORD not in cases_file.read_text(encoding="utf-8")


def test_the_placeholder_is_accepted_and_stored(
    client: TestClient, scratch_root: Path
) -> None:
    """The safe form of the same intent must work."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = _add_case(client, "{{SECRET:DEMO_PASSWORD}}")

    assert response.status_code == 303
    case = ProjectStore("demo", scratch_root).list_cases()[0]
    assert case.steps[0].value == "{{SECRET:DEMO_PASSWORD}}"
    assert REAL_PASSWORD not in case.model_dump_json()


def test_an_undeclared_key_is_refused_up_front(
    client: TestClient, scratch_root: Path
) -> None:
    """Previously this resolved only at typing time, deep inside `_value_for`,
    arriving as a stringified UndeclaredSecret in a generic ERRORED outcome."""
    _project_with_credential(client, scratch_root)

    response = _add_case(client, "{{SECRET:NOT_DECLARED}}")

    assert response.status_code == 400
    assert "NOT_DECLARED" in response.text
    assert ProjectStore("demo", scratch_root).list_cases() == []


def test_an_ordinary_value_is_untouched(client: TestClient, scratch_root: Path) -> None:
    """The guard must not get in the way of normal typing."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = _add_case(client, "  Bengaluru  ")

    assert response.status_code == 303
    assert ProjectStore("demo", scratch_root).list_cases()[0].steps[0].value == "Bengaluru"


# -- the form makes the safe thing the easy thing ----------------------------

def test_the_form_offers_the_declared_credentials(
    client: TestClient, scratch_root: Path
) -> None:
    _project_with_credential(client, scratch_root)

    response = client.get("/projects/demo/cases/new")

    assert "{{SECRET:DEMO_PASSWORD}}" in response.text
    assert "list='declared-credentials'" in response.text


def test_a_project_with_no_credentials_gets_no_picker(
    client: TestClient, scratch_root: Path
) -> None:
    """The box behaves exactly as before for a project that declares nothing."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })

    response = client.get("/projects/demo/cases/new")

    assert "declared-credentials" not in response.text


# -- fail fast, not mid-run --------------------------------------------------

def test_a_run_is_refused_when_a_declared_credential_has_no_value(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The UI loads secrets with strict=False, so a missing value used to
    surface only when a step tried to type it — as BLOCKED_HITL, after a
    browser had already been launched."""
    _project_with_credential(client, scratch_root)  # declared, no value
    _add_case(client, "{{SECRET:DEMO_PASSWORD}}")

    class _AvailableProvider:  # the provider gate is a different precondition
        def available(self) -> bool:
            return True

    import autotester.stages.run_launcher as run_launcher_module
    monkeypatch.setattr(run_launcher_module, "for_role", lambda *a, **k: _AvailableProvider())

    response = client.post("/projects/demo/run")

    assert response.status_code == 400
    assert "DEMO_PASSWORD" in response.text
    assert "Credentials page" in response.text


# -- AT-070/AT-071: the guard covers the whole form, not one box -------------

def _add_case_fields(client: TestClient, *, title: str = "Log in", target: str = "input#x",
                     value: str = "", expect: str = ""):
    return client.post("/projects/demo/cases", data={
        "title": title, "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.FILL.value], "step_target": [target],
        "step_value": [value], "step_expected": [expect],
    }, follow_redirects=False)


@pytest.mark.parametrize("field", ["title", "target", "expect"])
def test_a_credential_in_any_field_is_refused_not_just_the_value_box(
    client: TestClient, scratch_root: Path, field: str
) -> None:
    """AT-070: the guard was wired to `step_value` alone. `cases.jsonl` is
    git-TRACKED in a public repo, so a credential in the title, target or expect
    box was a credential committed in cleartext. The title was worst: U6 leaves
    `rationale=None`, so `claim_of` falls back to it and feeds the grade prompt."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = _add_case_fields(client, **{field: REAL_PASSWORD})

    assert response.status_code == 400, f"{field} accepted a real credential"
    assert ProjectStore("demo", scratch_root).list_cases() == []


def test_a_credential_split_across_two_rows_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-071: the guard ran once per row, so the halves passed individually and
    reassembled byte-for-byte on disk."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)
    half = len(REAL_PASSWORD) // 2

    response = client.post("/projects/demo/cases", data={
        "title": "Split", "case_class": CaseClass.HAPPY.value,
        "step_action": [Action.FILL.value, Action.FILL.value],
        "step_target": ["input#a", "input#b"],
        "step_value": [REAL_PASSWORD[:half], REAL_PASSWORD[half:]],
        "step_expected": ["", ""],
    }, follow_redirects=False)

    assert response.status_code == 400
    assert ProjectStore("demo", scratch_root).list_cases() == []


def test_renaming_a_case_to_a_credential_is_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """Rename is a second door into the same field."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)
    _add_case_fields(client, title="Honest title")
    case_id = ProjectStore("demo", scratch_root).list_cases()[0].id

    response = client.post(f"/projects/demo/cases/{case_id}/rename",
                            data={"title": REAL_PASSWORD})

    assert response.status_code == 400
    assert ProjectStore("demo", scratch_root).list_cases()[0].title == "Honest title"


def test_an_ordinary_multi_field_case_still_works(
    client: TestClient, scratch_root: Path
) -> None:
    """The widened guard must not block normal use."""
    _project_with_credential(client, scratch_root, value=REAL_PASSWORD)

    response = _add_case_fields(
        client, title="Sign in works", target="input[type=email]",
        value="tester@demo.test", expect="Welcome",
    )

    assert response.status_code == 303
    assert len(ProjectStore("demo", scratch_root).list_cases()) == 1


def test_a_credential_reaching_the_grade_prompt_blocks_instead_of_crashing(
    tmp_path: Path
) -> None:
    """AT-070's second half: refusing to send the prompt is right, but raising an
    unhandled ValueError 500d every later run with no way back."""
    from autotester.browser.secrets import SecretStore
    from autotester.providers.mock import MockProvider
    from autotester.schema.enums import Outcome, Result
    from autotester.schema.project import Project, SecretRef
    from autotester.schema.run import RawResult
    from autotester.schema.verdict import Criterion, Rubric
    from autotester.stages.grade import grade

    env = tmp_path / ".env"
    env.write_text(f"DEMO_PASSWORD={REAL_PASSWORD}\n", encoding="utf-8")
    project = Project(slug="demo", name="Demo", base_url="https://demo.test",
                       allowed_domains=["demo.test"],
                       secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    secrets = SecretStore.load(project, env)
    poisoned = Rubric(id="rub_x", case_id="case_x",
                       criteria=[Criterion(id="c1", text=f"evidence shows {REAL_PASSWORD}")])
    result = RawResult(case_id="case_x", outcome=Outcome.COMPLETED)

    verdict = grade(poisoned, result, "run_1", MockProvider(), secrets=secrets)

    assert verdict.result is Result.BLOCKED
    assert REAL_PASSWORD not in verdict.model_dump_json()
