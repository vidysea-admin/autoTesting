"""`autotester expand` — the first production caller of `stages/expand.py`.

AT-239/AT-250: `expand` is the feature this repo's own ledger calls "the
differentiator", and until this command existed it had **zero** production
callers — `tests/test_expand.py:11` was the only importer in the whole
codebase. Measured consequence: across four real projects the product held 52
cases of which 49 were `happy`, and not one case in its life had been
generated. A stage nothing calls is not a feature.

The oracle here is deliberately the FILE, not the function: `expand()` returns
`Case` objects and (per `qa/contracts/expand.md`'s no-fire list) persists
nothing — so a test that only checks the return value would have passed
happily throughout the entire period the product could not generate a case.
What these tests assert is that `projects/<slug>/cases.jsonl` gains rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, CaseClass, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _login_flow() -> Flow:
    return Flow(
        id="flow-login", name="Sign in", entry_screen="scr_signin",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
            Step(order=2, action=Action.FILL, target="Email", value="a@demo.test"),
            Step(order=3, action=Action.CLICK, target="Sign in"),
        ],
    )


def _seed(root: Path, *, status: ReviewStatus = ReviewStatus.APPROVED) -> ProjectStore:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.save_flowspec(FlowSpec(project="demo", review=Review(status=status),
                                 flows=[_login_flow()]))
    return store


def _seeded_mock(monkeypatch: pytest.MonkeyPatch, *, declines: bool = False) -> MockProvider:
    """One canned `ExpandedSteps` per model call, so the run is deterministic
    and offline. `declines=True` is the model saying "this class does not apply
    here" — an empty `steps` list (expand.md X4)."""
    answer = (
        ExpandedSteps(steps=[], rationale="does not apply to this flow") if declines
        else ExpandedSteps(
            steps=[Step(order=1, action=Action.CLICK, target="Sign in")],
            rationale="exercises the class",
        )
    )
    provider = MockProvider(responses={"agent": [answer] * 60})
    monkeypatch.setattr("autotester.cli.providers.get", lambda _id, **_kw: provider)
    return provider


def test_expand_writes_generated_cases_to_the_projects_cases_file(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point of the command: cases on disk, in the same file the UI
    lists and `trigger_run` runs."""
    store = _seed(root)
    _seeded_mock(monkeypatch)

    result = runner.invoke(app, ["expand", "demo"])

    assert result.exit_code == 0, result.output
    cases = store.list_cases()
    assert len(cases) > 1, [c.title for c in cases]
    assert store.paths.cases.exists()


def test_expand_produces_more_than_the_happy_path(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AT-250's actual complaint: a 94% happy-path suite. A command that only
    ever wrote the flow's own steps back would satisfy the test above and still
    leave the product exactly where it was."""
    store = _seed(root)
    _seeded_mock(monkeypatch)

    runner.invoke(app, ["expand", "demo"])

    classes = {c.case_class for c in store.list_cases()}
    assert CaseClass.HAPPY in classes
    assert len(classes - {CaseClass.HAPPY}) >= 3, classes


def test_expand_refuses_an_unreviewed_flowspec_and_writes_nothing(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """expand.md X1 + review-gate R1-R3 reaching the operator: the gate is what
    makes generated cases trustworthy, so the command must not be the back door
    around it."""
    store = _seed(root, status=ReviewStatus.DRAFT)
    _seeded_mock(monkeypatch)

    result = runner.invoke(app, ["expand", "demo"])

    assert result.exit_code == 1, result.output
    assert "not approved" in result.output
    assert store.list_cases() == []


def test_expand_on_a_project_that_does_not_exist_refuses_cleanly(root: Path) -> None:
    """AT-179's rule, applied to a new command: absence is exit 1, never a
    traceback and never a cheerful zero."""
    result = runner.invoke(app, ["expand", "nope"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "no project" in result.output


def test_expand_with_no_flowspec_says_so(root: Path) -> None:
    store = ProjectStore("demo", root)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))

    result = runner.invoke(app, ["expand", "demo"])

    assert result.exit_code == 1
    assert "no flowspec" in result.output


def test_expanding_twice_does_not_duplicate_the_suite(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`Case` is content-addressed and `add_case` is idempotent — the command
    must not defeat that by minting new ids (expand.md no-fire list)."""
    store = _seed(root)
    _seeded_mock(monkeypatch)

    runner.invoke(app, ["expand", "demo"])
    first = len(store.list_cases())
    _seeded_mock(monkeypatch)
    runner.invoke(app, ["expand", "demo"])

    assert len(ProjectStore("demo", root).list_cases()) == first


def test_a_declined_class_produces_no_case(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """expand.md X4 through the command: an empty `ExpandedSteps.steps` means
    "not applicable", so only the happy path survives."""
    store = _seed(root)
    _seeded_mock(monkeypatch, declines=True)

    result = runner.invoke(app, ["expand", "demo"])

    assert result.exit_code == 0, result.output
    assert [c.case_class for c in store.list_cases()] == [CaseClass.HAPPY]


def test_expand_refuses_when_the_named_provider_has_no_credentials(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refusal before the first model call, not a stack trace on the tenth."""
    _seed(root)

    class _Unavailable(MockProvider):
        def available(self) -> bool:
            return False

    monkeypatch.setattr("autotester.cli.providers.get", lambda _id, **_kw: _Unavailable())

    result = runner.invoke(app, ["expand", "demo"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "credentials" in result.output


def test_a_provider_failure_mid_expand_is_a_clean_refusal_not_a_traceback(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AT-260: a real run hit `ProviderError: the answer hit max_output_tokens
    and was truncated` as a raw Rich traceback panel, with no cases persisted
    and no clean signal why. This is the same refusal shape as the
    no-credentials case above, just for a failure that happens mid-call
    rather than before the first one."""
    from autotester.providers.base import ProviderError

    store = _seed(root)

    class _Exploding(MockProvider):
        def act(self, prompt: str, schema=None, *, prompt_file=None, fed_id=None):
            raise ProviderError("the answer hit max_output_tokens and was truncated (role=agent)")

    monkeypatch.setattr("autotester.cli.providers.get", lambda _id, **_kw: _Exploding())

    result = runner.invoke(app, ["expand", "demo"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "no cases persisted" in result.output
    assert store.list_cases() == []
