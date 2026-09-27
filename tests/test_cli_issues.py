"""`autotester issues pin` — the CLI half of AT-597's issue -> pinned Case path.

Sibling to the UI action in `ui/routes_issues.py`: same `pin_issue_as_case`
constructor (T-184, AT-585), a different human-facing entry point for anyone
scripting the tester workflow instead of clicking through the browser.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli_issues import _parse_step, app
from autotester.schema.enums import IssueCategory
from autotester.schema.issue import Issue
from autotester.schema.project import Project, SecretRef
from autotester.store.project_store import ProjectStore

runner = CliRunner()


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    result = ProjectStore("demo", tmp_path)
    result.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                                allowed_domains=["demo.test"]))
    return result


def _an_issue(**kw) -> Issue:
    return Issue(
        project="demo", source_id="src_one", recording_label="Demo clip", at_s=4,
        screen="Signup", title=kw.pop("title", "Google sign-in drops the data filled at signup"),
        what_is_wrong="fields filled before the Google redirect are gone on return",
        category=IssueCategory.LOGIC_ERROR, **kw,
    )


def test_pin_creates_a_protected_case_from_confirmed_steps(store: ProjectStore) -> None:
    issue = _an_issue()
    store.add_issue(issue)

    result = runner.invoke(app, [
        "pin", "demo", issue.id,
        "--step", "navigate:https://demo.test/signup",
        "--step", "click:#google-sign-in::signup form still has my email",
    ])

    assert result.exit_code == 0, result.output
    cases = store.list_cases()
    assert len(cases) == 1
    assert cases[0].pinned is True
    assert cases[0].pinned_issue_id == issue.id
    assert cases[0].steps[0].order == 1
    assert cases[0].steps[1].value is None
    assert cases[0].steps[1].expected.visible_text == ["signup form still has my email"]


def test_pin_an_unknown_issue_fails_clearly(store: ProjectStore) -> None:
    result = runner.invoke(app, ["pin", "demo", "iss_nope", "--step", "navigate:/x"])

    assert result.exit_code != 0
    assert "no issue" in result.output.lower()
    assert store.list_cases() == []


def test_pin_requires_at_least_one_step(store: ProjectStore) -> None:
    issue = _an_issue()
    store.add_issue(issue)

    result = runner.invoke(app, ["pin", "demo", issue.id])

    assert result.exit_code != 0
    assert "at least one confirmed --step" in result.output
    assert store.list_cases() == []


def test_pin_rejects_an_unparseable_step(store: ProjectStore) -> None:
    issue = _an_issue()
    store.add_issue(issue)

    result = runner.invoke(app, ["pin", "demo", issue.id, "--step", "not-a-valid-step"])

    assert result.exit_code != 0
    assert "must look like" in result.output
    assert store.list_cases() == []


def test_pin_rejects_an_unknown_action(store: ProjectStore) -> None:
    issue = _an_issue()
    store.add_issue(issue)

    result = runner.invoke(app, ["pin", "demo", issue.id, "--step", "flibber:/x"])

    assert result.exit_code != 0
    assert "is not one of" in result.output
    assert store.list_cases() == []


def test_pinning_the_same_issue_and_steps_twice_is_idempotent(store: ProjectStore) -> None:
    issue = _an_issue()
    store.add_issue(issue)
    step = ["--step", "navigate:https://demo.test/signup"]

    first = runner.invoke(app, ["pin", "demo", issue.id, *step])
    second = runner.invoke(app, ["pin", "demo", issue.id, *step])

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert len(store.list_cases()) == 1


# -- AT-597 cycle 2: the CLI gets the same guards the UI route already has ---

def test_pin_preserves_a_url_scheme_in_the_navigate_target(store: ProjectStore) -> None:
    """A plain `split(":", 3)` used to cut the URL's own scheme colon as a
    field separator, turning 'https://demo.test/login' into target='https'."""
    issue = _an_issue()
    store.add_issue(issue)

    result = runner.invoke(app, [
        "pin", "demo", issue.id, "--step", "navigate:https://demo.test/login",
    ])

    assert result.exit_code == 0, result.output
    assert store.list_cases()[0].steps[0].target == "https://demo.test/login"


def test_pin_refuses_an_out_of_scope_navigate_step(store: ProjectStore) -> None:
    """Same AT-058/AT-432 guard the UI pin route runs (`_require_reachable_
    navigate_steps`): a step that could never run at execution time is
    refused at pin time too, on the CLI as well as the UI."""
    issue = _an_issue()
    store.add_issue(issue)

    result = runner.invoke(app, [
        "pin", "demo", issue.id, "--step", "navigate:https://not-allowed.test/x",
    ])

    assert result.exit_code != 0
    assert "could never run" in result.output
    assert store.list_cases() == []


def test_pin_refuses_a_raw_secret_value(store: ProjectStore) -> None:
    """C5: `cases.jsonl` is git-tracked in a public repo -- a raw declared
    credential typed into a step must be refused exactly like the UI's pin
    route refuses it (400 there, non-zero exit here), and nothing pinned."""
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test",
        allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])],
    ))
    (store.paths.root / ".env").write_text("DEMO_PASSWORD=SuperSecretRaw123\n", encoding="utf-8")
    issue = _an_issue()
    store.add_issue(issue)

    result = runner.invoke(app, [
        "pin", "demo", issue.id,
        "--step", "navigate:https://demo.test/signup",
        "--step", "fill:#password:SuperSecretRaw123",
    ])

    assert result.exit_code != 0
    assert "looks like it contains a real credential" in result.output
    assert store.list_cases() == []
    cases_file = store.paths.cases
    assert not cases_file.exists() or "SuperSecretRaw123" not in cases_file.read_text(
        encoding="utf-8")


def test_pin_refuses_a_second_pin_of_the_same_issue_with_different_steps(
    store: ProjectStore,
) -> None:
    """AT-604: `Case.id` is content-addressed on its steps, so re-pinning the
    same issue with different steps would otherwise create a second pinned
    case for the same finding instead of colliding with the first."""
    issue = _an_issue()
    store.add_issue(issue)
    runner.invoke(app, ["pin", "demo", issue.id, "--step", "navigate:https://demo.test/signup"])

    result = runner.invoke(app, [
        "pin", "demo", issue.id, "--step", "navigate:https://demo.test/other",
    ])

    assert result.exit_code != 0
    assert "already pinned as case" in result.output
    assert len(store.list_cases()) == 1


# -- AT-597 cycle 3: cycle 2's fix protected the SCHEME colon, not the PORT --

def test_parse_step_preserves_a_navigate_targets_port() -> None:
    """`navigate:http://localhost:8069/signup` used to become
    target='http://localhost', value='8069/signup' -- the port's own ':'
    looked exactly like the scheme colon cycle 2 already protected."""
    step = _parse_step(1, "navigate:http://localhost:8069/signup")

    assert step.target == "http://localhost:8069/signup"
    assert step.value is None


def test_parse_step_preserves_an_https_hosts_port() -> None:
    step = _parse_step(1, "navigate:https://app.example.com:8443/login")

    assert step.target == "https://app.example.com:8443/login"
    assert step.value is None


def test_parse_step_keeps_a_ported_url_whole_as_a_fill_value() -> None:
    """A URL need not be the navigate target -- it can just as well be a
    fill value, and its port must survive there too."""
    step = _parse_step(1, "fill:#url:https://x.com:8080/a")

    assert step.target == "#url"
    assert step.value == "https://x.com:8080/a"
    assert step.expected.visible_text == []


def test_parse_step_keeps_a_ported_url_value_and_its_own_expect() -> None:
    """The field AFTER a ported URL value must still parse -- the URL's own
    colons must not swallow the expect field that follows it."""
    step = _parse_step(1, "fill:#url:https://x.com:8080/a:expected")

    assert step.value == "https://x.com:8080/a"
    assert step.expected.visible_text == ["expected"]


def test_parse_step_still_parses_a_plain_url_with_no_port() -> None:
    """Regression check: a URL with no port (cycles 1 and 2's own fix) must
    still parse correctly now that the tokenizer is scheme-aware."""
    step = _parse_step(1, "navigate:https://example.com/login")

    assert step.target == "https://example.com/login"
    assert step.value is None


def test_pin_a_local_dev_server_navigate_target_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mis-parsed target with its port stripped would make the reachable-
    navigate guard check the WRONG host -- `http://localhost` (no port) still
    happens to resolve to the same allowed host here, so only a full
    end-to-end run, asserting the STORED target, catches a silent truncation
    that a guard's pass/fail alone would miss."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    local_store = ProjectStore("local", tmp_path)
    local_store.save_project(Project(
        slug="local", name="Local", base_url="http://localhost:8069",
        allowed_domains=["localhost"],
    ))
    issue = _an_issue()
    local_store.add_issue(issue)

    result = runner.invoke(app, [
        "pin", "local", issue.id,
        "--step", "navigate:http://localhost:8069/signup",
        "--step", "click:#go",
    ])

    assert result.exit_code == 0, result.output
    case = local_store.list_cases()[0]
    assert case.steps[0].target == "http://localhost:8069/signup"


# -- AT-597 cycle 4 (narrow, gate qa/gates/at597-cycle4.md, answer A): cycle
# 3's NAVIGATE bypass took the whole remainder as the target, which silently
# swallowed a trailing `::expect` into the URL instead of keeping it as the
# step's expected text. -----------------------------------------------------

def test_parse_step_keeps_a_navigate_ports_target_and_its_expect() -> None:
    """`navigate:<ported url>::Welcome` must keep BOTH the port (cycle 3's
    own fix) and the expect (cycle 2 had this; cycle 3 lost it, 1133e8b)."""
    step = _parse_step(1, "navigate:http://localhost:8069/signup::Welcome")

    assert step.target == "http://localhost:8069/signup"
    assert step.value is None
    assert step.expected.visible_text == ["Welcome"]


def test_parse_step_keeps_a_navigates_expect_with_no_port_too() -> None:
    """Same capability as the ported case above, without a port -- the
    fix must not be a port-only special case."""
    step = _parse_step(1, "navigate:https://x.com/signup::Welcome")

    assert step.target == "https://x.com/signup"
    assert step.value is None
    assert step.expected.visible_text == ["Welcome"]


def test_parse_step_refuses_a_navigate_with_a_value_field() -> None:
    """Navigate has nowhere to put a value -- a single-colon tail after the
    target (`:junk:Welcome`) must be refused with a clear error rather than
    silently folded into the target or dropped, the way cycle 3 did."""
    with pytest.raises(ValueError, match="navigate has no value field"):
        _parse_step(1, "navigate:https://x.com/a:junk:Welcome")
