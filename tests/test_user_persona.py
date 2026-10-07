"""T-190 advisory UX track. Contract: qa/contracts/persona-ux-advisory.md PU1-PU9."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths, RepoDocs
from autotester.providers.mock import MockProvider
from autotester.schema.case import AgentFix, Case
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    EvidenceKind,
    Outcome,
    Severity,
    TechComfort,
)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.run import Evidence, RawResult, Run
from autotester.schema.user_persona import UserPersona, UXPolicy
from autotester.schema.ux_report import UXCaseStatus, UXDraft, UXJudgment, UXReport
from autotester.schema.verdict import Judgment, Result, Verdict
from autotester.stages.run_case_pipeline import run_and_grade_case
from autotester.stages.ux_advisory import (
    judge_case_ux,
    run_ux_advisory,
)
from autotester.store.project_store import ProjectStore

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"
SECRET = "hunter2-very-secret-9x"
RUN = "run_1"


def _persona(device: str = "desktop", locale: str = "en-US", role: str = "counsellor",
             pid: str = "p1") -> UserPersona:
    return UserPersona(id=pid, project="demo", role=role, tech_comfort=TechComfort.LOW,
                       locale=locale, device=device)


def _draft(step: int | None = 1, path: str | None = None, text: str = "Label is unclear"):
    return UXDraft(severity=Severity.S2, finding=text, step_order=step, evidence_path=path)


def _mock(*judgments: UXJudgment) -> MockProvider:
    return MockProvider(responses={"judge": list(judgments)})


def _seed(tmp_path: Path, *, enabled: bool = True, max_calls: int = 20, n_cases: int = 1,
          persona: UserPersona | None = None, case_class: CaseClass = CaseClass.HAPPY,
          outcome: Outcome = Outcome.COMPLETED, ref: str | None = "p1") -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])], user_persona_ref=ref,
        ux_policy=UXPolicy(enabled=enabled, max_calls=max_calls)))
    (tmp_path / ".env").write_text(f"DEMO_PASSWORD={SECRET}\n", encoding="utf-8")
    store.save_user_persona(persona or _persona())
    run_dir, ids = store.paths.run_dir(RUN), []
    for i in range(n_cases):
        case = Case(project="demo", flow_id=f"f{i}", kind=CaseKind.BEST, case_class=case_class,
                    title=f"Case {i}", steps=[Step(order=1, action=Action.NAVIGATE,
                                                   target=f"https://demo.test/{i}")])
        store.add_case(case)
        ids.append(case.id)
        (run_dir).mkdir(parents=True, exist_ok=True)
        (run_dir / f"{i}.png").write_bytes(b"png")
        store.save_result(RUN, RawResult(case_id=case.id, outcome=outcome, evidence=[
            Evidence(kind=EvidenceKind.SCREENSHOT, path=f"{i}.png", step_order=1)]))
    store.save_run(Run(id=RUN, project="demo", case_ids=ids))
    return store


def _status(report: UXReport | None, index: int = 0) -> UXCaseStatus:
    assert report is not None
    return report.cases[index].status


# -- PU1 ----------------------------------------------------------------------
def test_persona_schema_forbids_extras_and_closes_tech_comfort() -> None:
    with pytest.raises(ValidationError):
        UserPersona(id="p", project="demo", role="r", tech_comfort=TechComfort.LOW,
                    locale="en", device="desktop", extra_field=1)
    with pytest.raises(ValidationError):
        UserPersona(id="p", project="demo", role="r", tech_comfort="expert",
                    locale="en", device="desktop")
    with pytest.raises(ValidationError):
        _persona(pid="../escape")


def test_persona_ref_round_trips_on_project_and_case_and_survives_a_fixed_step(
    tmp_path: Path,
) -> None:
    store = _seed(tmp_path)
    assert store.load_project().user_persona_ref == "p1"
    case = store.list_cases()[0].model_copy(update={"user_persona_ref": "p1"})
    store.update_case(case)
    reloaded = store.get_case(case.id)
    assert reloaded is not None and reloaded.user_persona_ref == "p1"
    assert reloaded.compute_id() == case.id  # the ref is not part of the content id
    fixed = reloaded.with_fixed_step(1, AgentFix(action=Action.NAVIGATE, target="/x",
                                                   reasoning="r"))
    assert fixed.user_persona_ref == "p1"
    stored = store.get_user_persona("p1")
    assert stored is not None
    omit = {"created_at"}
    assert stored.model_dump(exclude=omit) == _persona().model_dump(exclude=omit)


# -- PU2 / PU4: separate artifact, nothing persona-shaped in grading ----------------------
def test_verdict_and_grading_modules_know_nothing_about_personas_or_ux() -> None:
    for rel in ("schema/verdict.py", "stages/grade.py", "stages/run_case_pipeline.py"):
        text = (SRC / rel).read_text(encoding="utf-8")
        assert not re.search(r"persona|ux_|UXFinding|UXReport", text, re.IGNORECASE), rel
    assert not {"persona", "ux"} & {f.lower() for f in Verdict.model_fields}
    assert not {"persona", "ux"} & {f.lower() for f in Judgment.model_fields}


def test_ux_report_is_its_own_file_and_load_results_still_skips_it(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    report = run_ux_advisory(store, RUN, _mock(UXJudgment(findings=[_draft()])))
    assert report is not None and report.cases[0].findings
    assert store.paths.run_ux_report(RUN).name == "ux_report.json"
    assert store.paths.run_ux_report(RUN).parent == store.paths.run_dir(RUN)
    assert [r.case_id for r in store.load_results(RUN)] == [report.cases[0].case_id]
    assert store.load_ux_report(RUN) == report


# -- PU3: the functional verdict is byte-identical with or without the UX pass -----------
class _Page:
    url = "https://demo.test/"

    def add_style_tag(self, content: str) -> None:
        pass

    def screenshot(self, path: str, full_page: bool = False) -> None:
        Path(path).write_bytes(b"png")

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url


def _graded_arm(root: Path, with_ux: bool) -> tuple[str, str, str]:
    store = _seed(root)
    case = store.list_cases()[0]
    paths = ProjectPaths("demo", root)
    secrets = SecretStore.load(store.load_project(), paths.env_file, strict=False)
    session = BrowserSession(store.load_project(), secrets, store.paths.run_dir(RUN), paths)
    session._page = _Page()
    judge = MockProvider(responses={"judge": [Judgment(
        result=Result.PASS, criteria_met=1, criteria_total=1, scoreboard="1/1 met")]})
    result, verdict = run_and_grade_case(case, session, judge, RUN, store)
    # created_at / duration_s are wall-clock mint values, not functional output
    result = result.model_copy(update={"created_at": result.created_at.min, "duration_s": 0.0})
    store.save_result(RUN, result)
    store.save_verdict(RUN, verdict)
    if with_ux:
        assert run_ux_advisory(store, RUN, _mock(UXJudgment(findings=[_draft()]))) is not None
    frozen = verdict.model_copy(update={"created_at": verdict.created_at.min})
    on_disk = (store.paths.run_dir(RUN) / f"{case.id}.verdict.json").read_text(encoding="utf-8")
    return (frozen.model_dump_json(),
            re.sub(r'"created_at": "[^"]*"', "", on_disk),
            (store.paths.run_dir(RUN) / f"{case.id}.json").read_text(encoding="utf-8"))


def test_persona_ux_pass_leaves_functional_verdict_and_result_byte_identical(
    tmp_path: Path,
) -> None:
    plain = _graded_arm(tmp_path / "a", with_ux=False)
    advised = _graded_arm(tmp_path / "b", with_ux=True)
    assert plain[0] == advised[0]  # every Verdict field
    assert plain[1] == advised[1]  # the stored verdict file
    assert plain[2] == advised[2]  # the stored RawResult file


def test_persona_judge_case_ux_never_mutates_the_result_it_reads(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    case, result = store.list_cases()[0], store.load_results(RUN)[0]
    before = result.model_dump_json()
    secrets = SecretStore.load(store.load_project(), store.paths.env_file, strict=False)
    judge_case_ux(case, result, _persona(), _mock(UXJudgment(findings=[_draft()])),
                  secrets=secrets, run_dir=store.paths.run_dir(RUN))
    assert result.model_dump_json() == before


# -- PU5: Provider + prompt file -------------------------------------------------------
def test_persona_ux_call_goes_through_provider_with_the_skill_prompt(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    provider = _mock(UXJudgment(findings=[]))
    run_ux_advisory(store, RUN, provider)
    (role, prompt), = provider.prompts
    assert role == "judge" and "counsellor" in prompt and "advisory" in prompt
    assert len(provider.judge_images[0]) == 1
    text = (SRC / "stages" / "ux_advisory.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(requests|httpx|anthropic|google)", text, re.M)


def test_persona_missing_skill_file_raises_not_an_inline_fallback(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    empty = RepoDocs(root=tmp_path / "nowhere", skills_dir=tmp_path / "no-skills")
    provider = _mock(UXJudgment())
    with pytest.raises(FileNotFoundError):
        run_ux_advisory(store, RUN, provider, docs=empty)
    assert provider.prompts == []


# -- PU6: redaction gate before the call --------------------------------------------------
def test_persona_prompt_with_a_raw_secret_raises_before_any_provider_call(tmp_path: Path) -> None:
    store = _seed(tmp_path, persona=_persona(role=f"reads {SECRET}"))
    case, result = store.list_cases()[0], store.load_results(RUN)[0]
    secrets = SecretStore.load(store.load_project(), store.paths.env_file, strict=False)
    provider = _mock(UXJudgment())
    with pytest.raises(ValueError):
        judge_case_ux(case, result, store.get_user_persona("p1"), provider, secrets=secrets,
                      run_dir=store.paths.run_dir(RUN))
    assert provider.prompts == []
    report = run_ux_advisory(store, RUN, provider)
    assert _status(report) is UXCaseStatus.WITHHELD and provider.prompts == []
    assert SECRET not in store.paths.run_ux_report(RUN).read_text(encoding="utf-8")


def test_persona_save_refuses_a_persona_carrying_a_credential(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    secrets = SecretStore.load(store.load_project(), store.paths.env_file, strict=False)
    with pytest.raises(ValueError):
        store.save_user_persona(_persona(role=SECRET, pid="p2"), secrets)
    assert store.get_user_persona("p2") is None
