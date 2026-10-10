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
