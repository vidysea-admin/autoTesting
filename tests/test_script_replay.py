"""T-176 / D-041: persist the generated script, replay it, locate by meaning.

Contract: qa/contracts/script-replay.md SR1-SR5. Every test runs a real Chromium against a local
fixture page (a fake page cannot tell `get_by_role` from a CSS path) and counts provider calls.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from autotester.browser.locators import format_label, format_role, format_testid, parse_target
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.providers.mock import MockProvider
from autotester.schema.case import AgentFix, Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import ExpectedState, FlowSpec, Step
from autotester.schema.project import Project
from autotester.schema.verdict import Judgment
from autotester.stages.run_case_pipeline import run_and_grade_case
from autotester.stages.script_replay import load_script, run_scripted
from autotester.store.project_store import ProjectStore

PAGE = """<!doctype html><html><body><h1>Account</h1>
<label for="em">Email address</label><input id="em" class="{inp}" type="text">
<button class="{btn}" data-testid="t-save" data-qa="q-save">{name}</button>
<div class="{plain}" onclick="document.getElementById('out').textContent='saved'">tap</div>
<p id="out"></p>
<script>document.querySelector('button').addEventListener('click',
  () => {{ document.getElementById('out').textContent = 'saved' }})</script>
</body></html>"""


def write_page(site: Path, *, inp="email-field", btn="save-btn", name="Save", plain="x") -> None:
    site.joinpath("index.html").write_text(
        PAGE.format(inp=inp, btn=btn, name=name, plain=plain), encoding="utf-8")


def judge() -> MockProvider:
    verdict = Judgment(result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1")
    return MockProvider(responses={"judge": [verdict, verdict, verdict]})


def make_case(base: str, *, click: str = "button.save-btn") -> Case:
    return Case(
        project="demo", flow_id="f1", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="Save works", rationale="saving shows 'saved'", steps=[
            Step(order=1, action=Action.NAVIGATE, target=f"{base}/index.html"),
            Step(order=2, action=Action.FILL, target="input.email-field", value="a@b.co"),
            Step(order=3, action=Action.CLICK, target=click,
                 expected=ExpectedState(visible_text=["saved"]))])


class Env:
    def __init__(self, tmp: Path, base: str, site: Path) -> None:
        self.tmp, self.base, self.site = tmp, base, site
        self.project = Project(slug="demo", name="Demo", base_url=base + "/",
                               allowed_domains=["127.0.0.1"], headed=False)
        self.store = ProjectStore("demo", tmp)
        self.store.save_project(self.project)
        self._live: BrowserSession | None = None

    def close(self) -> None:
        if self._live is not None:
            self._live.close()
            self._live = None

    @contextmanager
    def session(self, project: Project | None = None) -> Iterator[BrowserSession]:
        """One Chromium per test (they are slow to start), reused until the project differs."""
        project = project or self.project
        if self._live is not None and self._live.project != project:
            self.close()
        if self._live is None:
            paths = ProjectPaths("demo", self.tmp)
            paths.ensure()
            self.tmp.joinpath(".env").write_text("", encoding="utf-8")
            secrets = SecretStore.load(project, self.tmp / ".env", strict=False)
            live = BrowserSession(project, secrets, self.tmp / "run", paths)
            try:
                live.start()
            except Exception as exc:  # browser binary missing on this machine
                pytest.skip(f"chromium unavailable: {type(exc).__name__}")
            live.locate_timeout_ms = 400
            self._live = live
        yield self._live

    def run(self, case: Case, project: Project | None = None):
        with self.session(project) as session:
            return run_scripted(case, session, self.store)

    def stored(self, case: Case) -> Case:
        stored = self.store.get_case(case.id)
        assert stored is not None
        return stored

    def script(self, case: Case):
        script, _why = load_script(self.stored(case), self.store, self.project)
        return script

    def script_bytes(self, case: Case) -> bytes:
        script = self.script(case)
        return (self.tmp / script.path).read_bytes()


@pytest.fixture
def env(tmp_path: Path, serve_dir: Callable[[Path], str]) -> Iterator[Env]:
    pytest.importorskip("playwright")
    site = tmp_path / "site"
    site.mkdir()
    write_page(site)
    made = Env(tmp_path, serve_dir(site), site)
    yield made
    made.close()


@pytest.fixture
def case(env: Env) -> Case:
    made = make_case(env.base)
    env.store.add_case(made)
    return made


# -- SR1: a stored script is replayed with zero provider calls -----------------------------

def test_sr1_second_run_replays_the_stored_script_with_zero_provider_calls(
    env: Env, case: Case
) -> None:
    provider = judge()
    with env.session() as session:
        first, _ = run_and_grade_case(case, session, provider, "run1", env.store)
        calls_after_first = len(provider.prompts)
        stored = env.stored(case)
        second, verdict = run_and_grade_case(
            stored, session, provider, "run2", env.store, judge_replays=False)
    assert calls_after_first == 1 and not first.used_script
    assert stored.script_ref and env.script(case).version == 1
    assert len(provider.prompts) == calls_after_first, "the replay made a provider call"
    assert second.used_script and second.outcome is first.outcome is Outcome.COMPLETED
    assert any(e.path.startswith("replay: script") for e in second.evidence)
    assert verdict.grader_provider == "rule"  # replay never grades (C7)


def test_sr1_a_replayed_run_is_still_graded_by_default(env: Env, case: Case) -> None:
    provider = judge()
    with env.session() as session:
        run_and_grade_case(case, session, provider, "run1", env.store)
        run_and_grade_case(env.stored(case), session, provider, "run2", env.store)
    assert len(provider.prompts) == 2  # grading stays the judge's job; only execution is free


# -- SR2: a stale script is invalidated, never trusted ----------------------------------------

def test_sr2_a_changed_step_refuses_the_old_script_and_says_why(env: Env, case: Case) -> None:
    env.run(case)
    old_bytes = env.script_bytes(case)
    fixed = env.stored(case).with_fixed_step(
        2, AgentFix(action=Action.FILL, target="input.email-field", value="z@y.co",
                    reasoning="changed value"))
    assert fixed.script_ref and fixed.id != case.id
    run = env.run(fixed)
    assert run.mode == "record" and not run.result.used_script
    assert run.reason and "case steps changed" in run.reason
    assert any("script stale: case steps changed" in e.path for e in run.result.evidence)
    assert (env.tmp / env.script(case).path).read_bytes() == old_bytes  # old version kept


def test_sr2_a_changed_flowspec_version_or_locator_priority_is_stale(
    env: Env, case: Case
) -> None:
    env.run(case)
    stored = env.stored(case)
    env.store.save_flowspec(FlowSpec(project="demo", version=2))
    _, why = load_script(stored, env.store, env.project)
    assert why and "flowspec version" in why
    env.store.save_flowspec(FlowSpec(project="demo", version=1))
    changed = env.project.model_copy(update={"test_id_attributes": ["data-qa"]})
    _, why = load_script(stored, env.store, changed)
    assert why and "locator priority" in why


# -- SR3: semantic first, brittle named, wrong element never healed -----------------------------

def test_sr3_replay_survives_a_css_class_rename(env: Env, case: Case) -> None:
    env.run(case)
    write_page(env.site, inp="renamed-input", btn="renamed-btn")
    run = env.run(env.stored(case))
    assert run.mode == "replay" and run.result.outcome is Outcome.COMPLETED
    steps = {s.order: s for s in env.script(case).steps}
    assert steps[2].strategy == "role"
    assert steps[2].locator == format_role("textbox", "Email address")
    assert steps[3].locator == format_role("button", "Save")


def test_sr3_a_changed_accessible_name_fails_honestly_and_names_the_step(
    env: Env, case: Case
) -> None:
    env.run(case)
    write_page(env.site, name="Save draft")  # a substring match would 'heal' onto the wrong button
    run = env.run(env.stored(case))
    assert run.mode == "replay"
    assert run.result.outcome is Outcome.ERRORED
    assert run.result.error and "step 3" in run.result.error


def test_sr3_a_css_only_step_is_flagged_not_silent(env: Env) -> None:
    case = make_case(env.base, click="div.x")
    env.store.add_case(case)
    run = env.run(case)
    script = env.script(case)
    assert script.brittle_steps == [3]
    assert any(e.path.startswith("brittle locator step 3") and e.step_order == 3
               for e in run.result.evidence)


def test_sr3_target_grammar_round_trips_and_leaves_css_alone() -> None:
    nasty = 'He said "hi" \\ ok'
    for target in (format_role("button", nasty), format_role("link", None),
                   format_label(nasty), format_testid("data-qa", nasty)):
        assert parse_target(target) is not None
    assert parse_target(format_role("button", nasty)).name == nasty
    assert parse_target("button.save-btn") is None and parse_target("#id > a") is None


# -- SR4: declared test-id priority, in order, nothing else -------------------------------------

@pytest.mark.parametrize(("declared", "expected"), [
    (["data-qa", "data-testid"], format_testid("data-qa", "q-save")),
    (["data-testid", "data-qa"], format_testid("data-testid", "t-save")),
    ([], format_role("button", "Save")),
    (["data-nonexistent"], format_role("button", "Save")),
])
def test_sr4_the_first_declared_attribute_present_wins(
    env: Env, case: Case, declared: list[str], expected: str
) -> None:
    project = env.project.model_copy(update={"test_id_attributes": declared})
    env.run(case, project)
    script, _ = load_script(env.stored(case), env.store, project)
    assert {s.order: s.locator for s in script.steps}[3] == expected


def test_sr4_an_attribute_not_on_the_list_is_never_used(env: Env, case: Case) -> None:
    """The element carries data-testid and data-qa; only data-other is declared (absent)."""
    project = env.project.model_copy(update={"test_id_attributes": ["data-other"]})
    env.run(case, project)
    script, _ = load_script(env.stored(case), env.store, project)
    assert all("data-" not in s.locator for s in script.steps)


def test_sr4_a_project_written_before_this_unit_still_loads() -> None:
    old = {"slug": "demo", "name": "Demo", "base_url": "https://demo.test"}
    assert Project.model_validate(old).test_id_attributes == []
    with pytest.raises(ValueError, match="test_id_attributes"):
        Project.model_validate({**old, "test_id_attributes": ['x"] , body {']})


# -- SR5: a failed replay reports; it never regenerates or overwrites ---------------------------

def test_sr5_a_failed_replay_is_errored_with_the_script_byte_identical(
    env: Env, case: Case
) -> None:
    provider = judge()
    env.run(case)
    before = env.script_bytes(case)
    write_page(env.site, name="Gone")  # the Save button no longer exists
    with env.session() as session:
        result, verdict = run_and_grade_case(
            env.stored(case), session, provider, "run2", env.store)
    assert result.outcome is Outcome.ERRORED and result.used_script
    assert "step 3" in (result.error or "")
    assert env.script_bytes(case) == before and env.script(case).version == 1
    assert hashlib.sha256(env.script_bytes(case)).hexdigest() == hashlib.sha256(before).hexdigest()
    assert not provider.prompts, "a failed replay called a provider"
    assert verdict.result is Result.INCONCLUSIVE and verdict.grader_provider == "rule"
