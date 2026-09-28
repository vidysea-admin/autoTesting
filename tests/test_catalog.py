"""CATALOG stage. Contract: qa/contracts/catalog.md CT1-CT8 (D-039)."""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.schema.catalog import BlockedReason, StandardPack, Tier
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


# -- CT1 pure, deterministic, no side effects --------------------------------

def test_catalog_is_pure_same_inputs_same_output(root: Path) -> None:
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    spec = _approved_spec()
    (root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")

    first = catalog(project, spec, ProjectStore("demo", root))
    second = catalog(project, spec, ProjectStore("demo", root))

    assert [e.model_dump() for e in first.entries] == [e.model_dump() for e in second.entries]


# -- CT2 every CaseClass gets exactly one entry ------------------------------

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


# -- CT3 blocked_reason is exactly the closed vocabulary, present iff blocked -

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


# -- CT4 no FlowSpec -> every entry blocked no_flowspec ----------------------

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


# -- CT5 missing credential names the KEY, never a value ---------------------

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
        steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/home")],
    )
    cat = catalog(_project(), _approved_spec(flow), ProjectStore("demo", root))
    for case_class in (CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION):
        entry = cat.entry(case_class)
        assert entry is not None
        assert entry.runnable is True


# -- needs_write_policy (D-039's remaining vocabulary member T-125 fires) ----

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


# -- CT6 cheap -> expensive tier ordering is real, total, and stops early ----

def test_every_case_class_has_exactly_one_tier() -> None:
    from autotester.schema.catalog import TIER_BY_CLASS

    assert set(TIER_BY_CLASS) == set(CaseClass)


def test_tiers_to_run_stops_before_an_unreachable_expensive_tier(root: Path) -> None:
    """A blocked STATIC tier stops dispatch even though ADVERSARIAL has a
    runnable entry (a real project: read-only, unapproved-adjacent secret
    missing does not apply here -- use no-flowspec, whose STATIC entries are
    all blocked, to construct the fixture without hand-building a Catalog)."""
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    cat = catalog(project, None, ProjectStore("demo", root))  # every entry no_flowspec
    assert tiers_to_run(cat) == []


def test_tiers_to_run_runs_static_then_behavioural_in_order(root: Path) -> None:
    project = _project(write_policy=WritePolicy.TEST_ACCOUNT)
    cat = catalog(project, _approved_spec(), ProjectStore("demo", root))
    order = tiers_to_run(cat)
    assert order[:2] == [Tier.STATIC, Tier.BEHAVIOURAL]
    assert order.index(Tier.STATIC) < order.index(Tier.BEHAVIOURAL)


def test_tiers_to_run_observed_via_call_order_not_just_final_state(root: Path) -> None:
    """CT6: 'observed via call order not just final state' -- a caller that
    iterates `tiers_to_run`'s result and records each tier as it dispatches
    it never records a tier the stop-rule should have skipped."""
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    cat = catalog(project, None, ProjectStore("demo", root))
    dispatched: list[Tier] = []
    for tier in tiers_to_run(cat):
        dispatched.append(tier)
    assert dispatched == []
    assert Tier.ADVERSARIAL not in dispatched


# -- CT7 one Catalog, reused, not duplicated ---------------------------------

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


# -- purity across independent SecretStore reads (no leaked value) ----------

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


# -- ISS-t125-5: the gate must not block on a credential the row never reads --

def test_an_unrelated_flows_unset_secret_does_not_block_the_auth_rows(root: Path) -> None:
    """ISS-t125-5 repro (b). DEMO_PASSWORD is SET; an admin-import flow's
    SFTP_KEY is not. Cycle 3 gated the auth rows on every key declared anywhere
    in the spec, so signing in reported blocked on a key login never reads."""
    project = _project(secrets=[
        SecretRef(key="DEMO_PASSWORD", domains=["demo.test"]),
        SecretRef(key="SFTP_KEY", domains=["demo.test"]),
    ])
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
        assert entry.runnable is True, (
            f"{case_class.value} blocked on a key login never reads: {entry.unblock_action!r}")


def test_an_oauth_only_unset_secret_blocks_the_pack_not_the_login_rows(root: Path) -> None:
    """ISS-t125-5 repro (a). The login password is SET; only the Google sign-up
    token is missing -- the OAuth pack is the one row that token blocks."""
    project = _project(secrets=[
        SecretRef(key="DEMO_PASSWORD", domains=["demo.test"]),
        SecretRef(key="GOOGLE_SIGNUP_TOKEN", domains=["demo.test"]),
    ])
    (root / ".env").write_text("DEMO_PASSWORD=hunter2\n", encoding="utf-8")
    signup = Flow(
        id="flow_signup", name="Sign up", entry_screen="scr_signup",
        steps=[Step(order=1, action=Action.CLICK, target="Sign up with Google"),
               Step(order=2, action=Action.FILL, target="Token",
                    value="{{SECRET:GOOGLE_SIGNUP_TOKEN}}")],
    )
    cat = catalog(project, _approved_spec(_auth_flow(), signup), ProjectStore("demo", root))
    entry = cat.entry(CaseClass.AUTH_WRONG_CREDS)
    assert entry is not None
    assert entry.runnable is True, f"login blocked on a signup token: {entry.unblock_action!r}"
    pack = cat.pack(StandardPack.OAUTH_SIGNUP_CARRYOVER)
    assert pack is not None and pack.runnable is False
    assert pack.unblock_action and "GOOGLE_SIGNUP_TOKEN" in pack.unblock_action
