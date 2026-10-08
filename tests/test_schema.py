"""Schema contract tests: roundtrip, content-addressing, and strictness."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotester.schema import (
    Case,
    ExpectedState,
    Flow,
    FlowSpec,
    Project,
    Screen,
    SecretRef,
    Step,
    Verdict,
)
from autotester.schema.enums import Action, CaseClass, CaseKind, Result, WritePolicy
from autotester.schema.run import Run


def test_catalog_counts_roundtrip_zero_and_legacy_absence() -> None:
    counts = {"static": 0, "behavioural": 2, "adversarial": 1}
    run = Run(project="demo", catalog_runnable_counts=counts)
    assert Run.model_validate_json(run.model_dump_json()).catalog_runnable_counts == counts
    assert Run(project="demo").catalog_runnable_counts is None


@pytest.mark.parametrize("counts", [
    {}, {"static": 0, "behavioural": 0},
    {"static": 0, "behavioural": 0, "adversarial": -1},
    {"static": False, "behavioural": 0, "adversarial": 0},
    {"static": 0.0, "behavioural": 0, "adversarial": 0},
    {"static": 0, "behavioural": 0, "adversarial": 0, "extra": 0},
])
def test_catalog_counts_reject_malformed_measurements(counts) -> None:
    with pytest.raises(ValidationError):
        Run(project="demo", catalog_runnable_counts=counts)


def make_step(order: int = 1, value: str | None = None) -> Step:
    return Step(
        order=order,
        action=Action.FILL,
        target="textbox 'Email'",
        value=value,
        expected=ExpectedState(visible_text=["Dashboard"]),
    )


def test_flowspec_roundtrips_through_json() -> None:
    spec = FlowSpec(
        project="pathlynks",
        screens=[Screen(id="login", name="Login")],
        flows=[Flow(id="f_login", name="Log in", entry_screen="login", steps=[make_step()])],
    )
    restored = FlowSpec.model_validate_json(spec.model_dump_json())
    assert restored == spec
    assert restored.flow("f_login") is not None
    assert restored.screen("login") is not None


def test_flowspec_fingerprint_tracks_meaning_not_timestamps() -> None:
    a = FlowSpec(project="p", screens=[Screen(id="s", name="S")])
    b = FlowSpec(project="p", screens=[Screen(id="s", name="S")])
    assert a.fingerprint == b.fingerprint

    c = FlowSpec(project="p", screens=[Screen(id="s", name="Different")])
    assert c.fingerprint != a.fingerprint


def test_case_id_is_content_addressed() -> None:
    kwargs = dict(
        project="pathlynks",
        flow_id="f_login",
        kind=CaseKind.BEST,
        case_class=CaseClass.HAPPY,
        title="Log in with valid credentials",
        steps=[make_step()],
    )
    assert Case(**kwargs).id == Case(**kwargs).id
    other = Case(**{**kwargs, "case_class": CaseClass.AUTH_WRONG_CREDS})
    assert other.id != Case(**kwargs).id


def test_unknown_field_is_rejected_loudly() -> None:
    with pytest.raises(ValidationError):
        Screen(id="s", name="S", typo_field="oops")


def test_project_domain_allowlist_covers_subdomains_only_when_listed() -> None:
    project = Project(
        slug="pathlynks",
        name="Pathlynks",
        base_url="https://pathlynks.example.com",
        allowed_domains=["pathlynks.example.com"],
    )
    assert project.allows_domain("pathlynks.example.com")
    assert project.allows_domain("api.pathlynks.example.com")
    assert not project.allows_domain("evil.com")
    assert not project.allows_domain("notpathlynks.example.com")


def test_project_defaults_to_read_only_and_headed() -> None:
    project = Project(slug="p", name="P", base_url="https://p.test")
    assert project.write_policy is WritePolicy.READ_ONLY
    assert project.headed is True


def test_vision_ensemble_splits_the_config_and_deduplicates() -> None:
    """AT-542: one config string may name the whole ensemble."""
    from autotester.schema.project import ProviderConfig

    assert ProviderConfig(vision="gemini,anthropic").vision_ensemble() == [
        "gemini", "anthropic"]
    # whitespace tolerated, duplicates dropped, empty segments dropped
    assert ProviderConfig(vision=" gemini , anthropic , gemini , ").vision_ensemble() == [
        "gemini", "anthropic"]
    # single name = ensemble of one (honest, still works)
    assert ProviderConfig().vision_ensemble() == ["gemini"]


def test_vision_ensemble_empty_config_falls_back_to_gemini() -> None:
    from autotester.schema.project import ProviderConfig

    assert ProviderConfig(vision=",").vision_ensemble() == ["gemini"]


def test_vision_ensemble_defaulted_distinguishes_empty_from_explicit_gemini() -> None:
    """AT-550 (remainder): an empty config falling back to the default must
    be observable, not silent. Both an empty config and an explicit
    `vision="gemini"` produce the same `vision_ensemble() == ["gemini"]`, but
    only the empty one substituted a default an operator never chose —
    `vision_ensemble_defaulted()` is what lets a caller tell them apart."""
    from autotester.schema.project import ProviderConfig

    assert ProviderConfig(vision="").vision_ensemble_defaulted() is True
    assert ProviderConfig(vision=",").vision_ensemble_defaulted() is True
    assert ProviderConfig(vision=" , ").vision_ensemble_defaulted() is True
    assert ProviderConfig(vision="gemini").vision_ensemble_defaulted() is False
    assert ProviderConfig(vision="gemini,anthropic").vision_ensemble_defaulted() is False


def test_secret_ref_rejects_lowercase_keys() -> None:
    SecretRef(key="PATHLYNKS_PASSWORD", domains=["p.test"])
    with pytest.raises(ValidationError):
        SecretRef(key="pathlynks_password")


def test_verdict_actionable_failure_requires_cited_failures() -> None:
    bare = Verdict(run_id="r", case_id="c", result=Result.FAIL)
    assert not bare.is_actionable_failure


def test_team_project_metadata_roundtrips_and_source_identity_is_stable() -> None:
    from autotester.schema.enums import SourceKind
    from autotester.schema.project import Source

    old = Project(slug="demo", name="Demo", base_url="https://demo.test")
    assert old.schedule is None and old.tracker is None
    current = old.model_copy(update={}).model_dump()
    current.update(schedule={"mode": "manual", "timezone": "IST"},
                   tracker={"sheet_url": "https://sheets.example.test/demo"})
    project = Project.model_validate(current)
    assert Project.model_validate_json(project.model_dump_json()) == project
    source = Source(project="demo", kind=SourceKind.TEXT, text="fixed input")
    enriched = Source(project="demo", kind=SourceKind.TEXT, text="fixed input",
                      uploaded_by="fixture@example.test", origin="upload")
    assert enriched.id == source.id
    with pytest.raises(ValidationError):
        Project.model_validate({**current, "schedule": {"timezone": "America/New_York"}})
    with pytest.raises(ValidationError):
        Project.model_validate({**current, "tracker": {"unexpected": True}})


def test_old_run_defaults_team_metadata_to_none() -> None:
    from autotester.schema.run import Run

    run = Run.model_validate({"project": "demo", "id": "run-fixture"})
    assert run.requested_by is None and run.slot_key is None and run.via is None


def test_team_enum_concepts_have_one_home_and_legacy_trigger_is_unchanged() -> None:
    import ast
    from pathlib import Path

    from autotester.schema.enums import Trigger
    from autotester.schema.run_queue import QueueStatus as CompatibilityStatus
    from autotester.schema.team_enums import QueueStatus

    assert CompatibilityStatus is QueueStatus
    assert [(value.name, value.value) for value in Trigger] == [
        ("MANUAL", "manual"), ("CI", "ci"), ("SCHEDULE", "schedule")]
    schema = Path(__file__).resolve().parents[1] / "src/autotester/schema"
    concepts = {"SourceOrigin", "QueueStatus", "RunVia", "ScheduleMode", "SlotOutcome",
                "DeliveryStatus"}
    homes = {name: [] for name in concepts}
    for path in schema.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef) and node.name in concepts:
                homes[node.name].append(path.name)
    assert homes == {name: ["team_enums.py"] for name in concepts}
