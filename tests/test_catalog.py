"""CATALOG stage. Contract: qa/contracts/catalog.md CT1-CT8 (D-039)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.schema.catalog import BlockedReason, Catalog, CatalogEntry, StandardPack, Tier
from autotester.schema.enums import Action, CaseClass, ReviewStatus, WritePolicy
from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
from autotester.schema.project import Project, SecretRef
from autotester.stages.catalog import catalog, tiers_to_run
from autotester.store.project_store import ProjectStore


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _project(**overrides: object) -> Project:
    base = {
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test/signin",
        "allowed_domains": ["demo.test"],
    }
    base.update(overrides)
    return Project(**base)


def _auth_flow() -> Flow:
    return Flow(
        id="flow_login", name="Login", entry_screen="scr_login",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
            Step(order=2, action=Action.FILL, target="Email", value="demo@test.test"),
            Step(order=3, action=Action.FILL, target="Password", value="{{SECRET:DEMO_PASSWORD}}"),
            Step(order=4, action=Action.CLICK, target="Sign in"),
        ],
    )


def _approved_spec(*flows: Flow) -> FlowSpec:
    return FlowSpec(
        project="demo", flows=list(flows) or [_auth_flow()],
        review=Review(status=ReviewStatus.APPROVED, by="umesh"),
    )


@pytest.mark.parametrize("state", ["approved", "draft", "absent"])
def test_catalog_is_pure_same_inputs_same_output(root: Path, monkeypatch, state) -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace

    import autotester.schema.base as artifact_base
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    spec = _approved_spec()
    if state == "draft":
        spec = spec.model_copy(update={"review": Review(status=ReviewStatus.DRAFT)})
    if state == "absent":
        spec = None
    (root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    clock = [datetime(2026, 10, 1, tzinfo=UTC)]
    monkeypatch.setattr(artifact_base, "datetime", SimpleNamespace(now=lambda tz: clock[0]))
    first = catalog(project, spec, ProjectStore("demo", root))
    clock[0] = datetime(2026, 10, 2, tzinfo=UTC)
    second = catalog(project, spec, ProjectStore("demo", root))
    assert first.model_dump_json() == second.model_dump_json()



def test_every_case_class_gets_exactly_one_entry_no_flowspec(root: Path) -> None:
    cat = catalog(_project(), None, ProjectStore("demo", root))
    assert len(cat.entries) == len(CaseClass)
    assert len({e.case_class for e in cat.entries}) == len(CaseClass)


def test_every_case_class_gets_exactly_one_entry_approved(root: Path) -> None:
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    (root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))
    assert len(cat.entries) == len(CaseClass)
    assert len({e.case_class for e in cat.entries}) == len(CaseClass)



def test_blocked_entries_always_carry_a_closed_reason(root: Path) -> None:
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))  # no .env at all
    for entry in cat.entries:
        if entry.runnable:
            assert entry.blocked_reason is None
        else:
            assert entry.blocked_reason is not None
            assert entry.blocked_reason in set(BlockedReason)


def test_runnable_entries_never_carry_a_reason(root: Path) -> None:
    project = _project()
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))
    happy = cat.entry(CaseClass.HAPPY)
    assert happy is not None
    assert happy.runnable is True
    assert happy.blocked_reason is None
    assert happy.unblock_action is None



def test_no_flowspec_blocks_every_class_no_flowspec(root: Path) -> None:
    cat = catalog(_project(), None, ProjectStore("demo", root))
    assert all(e.blocked_reason is BlockedReason.NO_FLOWSPEC for e in cat.entries)
    assert all(e.applicable is False and e.runnable is False for e in cat.entries)


def test_empty_flowspec_flows_also_blocks_no_flowspec(root: Path) -> None:
    spec = FlowSpec(project="demo", flows=[], review=Review(status=ReviewStatus.APPROVED))
    cat = catalog(_project(), spec, ProjectStore("demo", root))
    assert all(e.blocked_reason is BlockedReason.NO_FLOWSPEC for e in cat.entries)


def test_unapproved_flowspec_blocks_every_class_flowspec_not_approved(root: Path) -> None:
    spec = FlowSpec(project="demo", flows=[_auth_flow()], review=Review(status=ReviewStatus.DRAFT))
    cat = catalog(_project(), spec, ProjectStore("demo", root))
    assert all(e.blocked_reason is BlockedReason.FLOWSPEC_NOT_APPROVED for e in cat.entries)
    assert all(e.applicable is True for e in cat.entries)



def test_missing_credential_names_the_key_never_a_value(root: Path) -> None:
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))  # no .env value set

    wrong_creds = cat.entry(CaseClass.AUTH_WRONG_CREDS)
    expired = cat.entry(CaseClass.AUTH_EXPIRED_SESSION)
    assert wrong_creds is not None and expired is not None
    for entry in (wrong_creds, expired):
        assert entry.blocked_reason is BlockedReason.MISSING_CREDENTIAL
        assert entry.unblock_action is not None
        assert "DEMO_PASSWORD" in entry.unblock_action
        assert entry.unblock_action != BlockedReason.MISSING_CREDENTIAL.value


def test_credential_present_makes_auth_classes_runnable(root: Path) -> None:
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    (root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))

    for case_class in (CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION):
        entry = cat.entry(case_class)
        assert entry is not None
        assert entry.runnable is True
        assert entry.blocked_reason is None


def test_a_flow_with_no_auth_field_never_blocks_on_credential(root: Path) -> None:
    flow = Flow(
        id="flow_browse", name="Browse", entry_screen="scr_home",
        steps=[Step(order=1, action=Action.NAVIGATE, target="Sign in with Google")],
    )
    cat = catalog(_project(secrets=[SecretRef(key="GOOGLE_LOGIN_TOKEN")]),
                  _approved_spec(flow), ProjectStore("demo", root))
    for case_class in (CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION):
        entry = cat.entry(case_class)
        assert entry is not None
        assert entry.runnable is True


def test_read_only_blocks_double_submit_needs_write_policy(root: Path) -> None:
    project = _project(write_policy=WritePolicy.READ_ONLY)
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))
    entry = cat.entry(CaseClass.DOUBLE_SUBMIT)
    assert entry is not None
    assert entry.blocked_reason is BlockedReason.NEEDS_WRITE_POLICY
    assert entry.unblock_action is not None
    assert entry.unblock_action != BlockedReason.NEEDS_WRITE_POLICY.value


def test_test_account_write_policy_makes_double_submit_runnable(root: Path) -> None:
    project = _project(write_policy=WritePolicy.TEST_ACCOUNT)
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))
    entry = cat.entry(CaseClass.DOUBLE_SUBMIT)
    assert entry is not None
    assert entry.runnable is True
    assert entry.blocked_reason is None


# -- CT6 cheap -> expensive ordering never filters an empty tier ------------

def test_every_case_class_has_exactly_one_tier() -> None:
    from autotester.schema.catalog import TIER_BY_CLASS

    assert set(TIER_BY_CLASS) == set(CaseClass)


def _static_blocked_adversarial_runnable() -> Catalog:
    """STATIC blocked while ADVERSARIAL is runnable — the only state that tells
    a stopping `tiers_to_run` from a non-stopping one. Hand-built because
    `catalog()` never blocks a STATIC class: the no-flowspec fixture these two
    tests shared blocked EVERY tier, so both passed with `break` OR `continue`."""
    return Catalog(project="demo", entries=[
        CatalogEntry(case_class=CaseClass.HAPPY, tier=Tier.STATIC, applicable=True,
                     runnable=False, blocked_reason=BlockedReason.NO_GROUND_TRUTH),
        CatalogEntry(case_class=CaseClass.AUTH_WRONG_CREDS, tier=Tier.ADVERSARIAL,
                     applicable=True, runnable=True)])


def test_tiers_to_run_keeps_all_tiers_when_static_is_blocked() -> None:
    cat = _static_blocked_adversarial_runnable()
    assert cat.runnable_in_tier(Tier.ADVERSARIAL)  # the expensive tier IS reachable
    assert tiers_to_run(cat) == [Tier.STATIC, Tier.BEHAVIOURAL, Tier.ADVERSARIAL]


def test_tiers_to_run_runs_static_then_behavioural_in_order(root: Path) -> None:
    project = _project(write_policy=WritePolicy.TEST_ACCOUNT)
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))
    order = tiers_to_run(cat)
    assert order[:2] == [Tier.STATIC, Tier.BEHAVIOURAL]
    assert order.index(Tier.STATIC) < order.index(Tier.BEHAVIOURAL)


def test_tiers_to_run_observed_via_call_order_not_just_final_state() -> None:
    """CT6's helper is an ordering input; the real trigger is tested separately."""
    dispatched: list[Tier] = []
    for tier in tiers_to_run(_static_blocked_adversarial_runnable()):
        dispatched.append(tier)
    assert dispatched == [Tier.STATIC, Tier.BEHAVIOURAL, Tier.ADVERSARIAL]



def test_exactly_one_catalog_model_and_blocked_reason_enum_in_src() -> None:
    import re

    from autotester.core.paths import repo_root

    src = repo_root() / "src" / "autotester"
    catalog_defs = 0
    reason_defs = 0
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        catalog_defs += len(re.findall(r"^class Catalog\b", text, re.M))
        reason_defs += len(re.findall(r"^class BlockedReason\b", text, re.M))
    assert catalog_defs == 1
    assert reason_defs == 1



def test_missing_credential_action_never_contains_the_real_env_value(root: Path) -> None:
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    # a DIFFERENT undeclared key is present too -- catalog must never echo it either
    (root / ".env").write_text(
        "DEMO_PASSWORD=hunter2\nOTHER_PROJECT_SECRET=zebra_quilt\n", encoding="utf-8"
    )
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))
    dumped = cat.model_dump_json()
    assert "hunter2" not in dumped
    assert "zebra_quilt" not in dumped



def test_same_class_union_includes_secret_fills_with_arbitrary_field_names(root: Path) -> None:
    """CT9: secret FILL feeds auth structurally even with an arbitrary target."""
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"]),
                                SecretRef(key="SFTP_KEY", domains=["demo.test"])])
    (root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    admin = Flow(
        id="flow_import", name="Admin import", entry_screen="scr_admin",
        steps=[Step(order=1, action=Action.FILL, target="SFTP key",
                    value="{{SECRET:SFTP_KEY}}")],
    )
    cat = catalog(project, _approved_spec(_auth_flow(), admin), ProjectStore("demo", root))
    for case_class in (CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION):
        entry = cat.entry(case_class)
        assert entry is not None
        assert entry.blocked_reason is BlockedReason.MISSING_CREDENTIAL
        assert entry.unblock_action == "set SFTP_KEY in the repo-root .env"


def test_an_oauth_only_unset_secret_blocks_the_pack_not_the_login_rows(root: Path) -> None:
    """CT9: CLICK placeholder feeds universal classes, never the auth class."""
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"]),
                                SecretRef(key="GOOGLE_SIGNUP_TOKEN", domains=["demo.test"])])
    (root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    signup = Flow(
        id="flow_signup", name="Sign up", entry_screen="scr_signup",
        steps=[Step(order=1, action=Action.CLICK, target="Sign up with Google"),
               Step(order=2, action=Action.CLICK, target="Token",
                    value="{{SECRET:GOOGLE_SIGNUP_TOKEN}}")],
    )
    cat = catalog(project, _approved_spec(_auth_flow(), signup), ProjectStore("demo", root))
    entry = cat.entry(CaseClass.AUTH_WRONG_CREDS)
    assert entry is not None
    assert entry.runnable is True, f"login blocked on a signup token: {entry.unblock_action!r}"
    assert entry.unblock_action is None
    happy = cat.entry(CaseClass.HAPPY)
    assert happy and happy.blocked_reason is BlockedReason.MISSING_CREDENTIAL
    assert happy.unblock_action and "GOOGLE_SIGNUP_TOKEN" in happy.unblock_action
    pack = cat.pack(StandardPack.OAUTH_SIGNUP_CARRYOVER)
    assert pack is not None and pack.runnable is False
    assert pack.unblock_action and "GOOGLE_SIGNUP_TOKEN" in pack.unblock_action
