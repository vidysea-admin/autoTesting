"""AT-588: the three standard packs on top of the CaseClass catalog.

Contract: qa/contracts/catalog.md (CT2/CT3/CT7 extended to `PackEntry`).
Split from test_catalog.py by responsibility (autotester doctor's C2 file cap).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.schema.catalog import BlockedReason, StandardPack
from autotester.schema.enums import Action, ReviewStatus
from autotester.schema.flowspec import Flow, FlowSpec, InputField, Review, Screen, Step
from autotester.schema.project import Project, SecretRef
from autotester.stages.catalog import catalog
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
            Step(order=3, action=Action.CLICK, target="Sign in"),
        ],
    )


def _approved_spec(*flows: Flow) -> FlowSpec:
    return FlowSpec(
        project="demo", flows=list(flows) or [_auth_flow()],
        review=Review(status=ReviewStatus.APPROVED, by="umesh"),
    )


def _oauth_signup_flow() -> Flow:
    return Flow(
        id="flow_signup", name="Sign up", entry_screen="scr_signup",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signup"),
            Step(order=2, action=Action.CLICK, target="Sign up with Google"),
        ],
    )


def _date_picker_screen() -> Screen:
    return Screen(
        id="scr_profile", name="Profile",
        fields=[InputField(name="dob_month", label="Birth month", type="month")],
    )


def _excel_upload_flow() -> Flow:
    return Flow(
        id="flow_import", name="Import", entry_screen="scr_import",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/import"),
            Step(order=2, action=Action.UPLOAD, target="Upload file", value="roster.xlsx"),
        ],
    )


def test_every_pack_gets_exactly_one_entry(root: Path) -> None:
    cat = catalog(_project(), _approved_spec(), ProjectStore("demo", root))
    assert len(cat.packs) == len(StandardPack)
    assert len({p.pack for p in cat.packs}) == len(StandardPack)


def test_no_flowspec_blocks_every_pack_no_flowspec(root: Path) -> None:
    cat = catalog(_project(), None, ProjectStore("demo", root))
    assert all(p.blocked_reason is BlockedReason.NO_FLOWSPEC for p in cat.packs)
    assert all(p.applicable is False and p.runnable is False for p in cat.packs)


def test_unapproved_flowspec_blocks_every_pack_not_approved(root: Path) -> None:
    spec = FlowSpec(
        project="demo", flows=[_oauth_signup_flow()], review=Review(status=ReviewStatus.DRAFT),
    )
    cat = catalog(_project(), spec, ProjectStore("demo", root))
    assert all(p.blocked_reason is BlockedReason.FLOWSPEC_NOT_APPROVED for p in cat.packs)
    oauth = cat.pack(StandardPack.OAUTH_SIGNUP_CARRYOVER)
    assert oauth is not None and oauth.applicable is True  # signal present even though unapproved
    excel = cat.pack(StandardPack.EXCEL_COLUMN_MAPPING)
    assert excel is not None and excel.applicable is False  # signal genuinely absent


def test_pack_with_no_matching_signal_is_not_applicable_no_reason(root: Path) -> None:
    cat = catalog(_project(), _approved_spec(), ProjectStore("demo", root))  # plain login flow
    for pack in StandardPack:
        entry = cat.pack(pack)
        assert entry is not None
        assert entry.applicable is False
        assert entry.runnable is False
        assert entry.blocked_reason is None
        assert entry.unblock_action is None


def test_oauth_signup_pack_detected_and_runnable(root: Path) -> None:
    spec = _approved_spec(_oauth_signup_flow())
    cat = catalog(_project(), spec, ProjectStore("demo", root))
    entry = cat.pack(StandardPack.OAUTH_SIGNUP_CARRYOVER)
    assert entry is not None
    assert entry.applicable is True
    assert entry.runnable is True
    assert entry.blocked_reason is None


def test_oauth_signup_pack_blocked_missing_credential_names_the_key(root: Path) -> None:
    flow = Flow(
        id="flow_signup", name="Sign up", entry_screen="scr_signup",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signup"),
            Step(order=2, action=Action.CLICK, target="Sign up with Google"),
            Step(order=3, action=Action.FILL, target="Password", value="{{SECRET:DEMO_PASSWORD}}"),
        ],
    )
    project = _project(secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    cat = catalog(project, _approved_spec(flow), ProjectStore("demo", root))  # no .env value set
    entry = cat.pack(StandardPack.OAUTH_SIGNUP_CARRYOVER)
    assert entry is not None
    assert entry.applicable is True
    assert entry.runnable is False
    assert entry.blocked_reason is BlockedReason.MISSING_CREDENTIAL
    assert entry.unblock_action is not None
    assert "DEMO_PASSWORD" in entry.unblock_action


def test_date_picker_pack_detected_from_field_type(root: Path) -> None:
    spec = FlowSpec(
        project="demo", screens=[_date_picker_screen()], flows=[_auth_flow()],
        review=Review(status=ReviewStatus.APPROVED, by="umesh"),
    )
    cat = catalog(_project(), spec, ProjectStore("demo", root))
    entry = cat.pack(StandardPack.DATE_PICKER_MONTH_YEAR)
    assert entry is not None
    assert entry.applicable is True
    assert entry.runnable is True


def test_excel_column_mapping_pack_detected_from_upload_step(root: Path) -> None:
    spec = _approved_spec(_excel_upload_flow())
    cat = catalog(_project(), spec, ProjectStore("demo", root))
    entry = cat.pack(StandardPack.EXCEL_COLUMN_MAPPING)
    assert entry is not None
    assert entry.applicable is True
    assert entry.runnable is True


def test_packs_never_add_a_second_catalog_or_blocked_reason_definition() -> None:
    """CT7 still holds after AT-588: the pack model reuses `BlockedReason`
    rather than inventing a pack-specific one."""
    import re

    from autotester.core.paths import repo_root

    src = repo_root() / "src" / "autotester"
    reason_defs = 0
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        reason_defs += len(re.findall(r"^class BlockedReason\b", text, re.M))
    assert reason_defs == 1


# -- ISS-t125-2: a blocked row names ITS OWN flow's key, not every unset key --


def _two_flows_each_needing_a_different_secret() -> FlowSpec:
    """The fixture no existing test built: one credential-consuming flow was
    always tested alone, so a union could never be told from a scoped answer."""
    login = Flow(
        id="flow_login", name="Login", entry_screen="scr_login",
        steps=[
            Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
            Step(order=2, action=Action.FILL, target="Password",
                 value="{{SECRET:DEMO_PASSWORD}}"),
            Step(order=3, action=Action.CLICK, target="Sign in"),
        ],
    )
    signup = Flow(
        id="flow_signup", name="Sign up", entry_screen="scr_signup",
        steps=[
            Step(order=1, action=Action.CLICK, target="Sign up with Google"),
            Step(order=2, action=Action.FILL, target="Token",
                 value="{{SECRET:GOOGLE_SIGNUP_TOKEN}}"),
        ],
    )
    return _approved_spec(login, signup)


def _both_secrets_declared() -> Project:
    return _project(secrets=[
        SecretRef(key="DEMO_PASSWORD", domains=["demo.test"]),
        SecretRef(key="GOOGLE_SIGNUP_TOKEN", domains=["demo.test"]),
    ])


def test_auth_rows_union_keys_from_both_secret_fill_flows(root: Path) -> None:
    """CT9: both secret FILL flows feed auth; same-class key union is required."""
    from autotester.schema.enums import CaseClass

    cat = catalog(_both_secrets_declared(), _two_flows_each_needing_a_different_secret(),
                  ProjectStore("demo", root))
    for case_class in (CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION):
        entry = cat.entry(case_class)
        assert entry is not None and entry.unblock_action is not None
        assert entry.blocked_reason is BlockedReason.MISSING_CREDENTIAL
        assert entry.unblock_action == (
            "set DEMO_PASSWORD, GOOGLE_SIGNUP_TOKEN in the repo-root .env")


def test_the_oauth_pack_does_not_advertise_a_login_only_key(root: Path) -> None:
    """The same defect pointing the other way: the pack named DEMO_PASSWORD,
    which the Google sign-up flow never reads."""
    cat = catalog(_both_secrets_declared(), _two_flows_each_needing_a_different_secret(),
                  ProjectStore("demo", root))
    entry = cat.pack(StandardPack.OAUTH_SIGNUP_CARRYOVER)
    assert entry is not None and entry.unblock_action is not None
    assert entry.blocked_reason is BlockedReason.MISSING_CREDENTIAL
    assert "GOOGLE_SIGNUP_TOKEN" in entry.unblock_action
    assert "DEMO_PASSWORD" not in entry.unblock_action, (
        f"the OAuth pack names a login-only key: {entry.unblock_action!r}"
    )


def test_an_oauth_only_spec_still_names_its_keys_rather_than_nothing(root: Path) -> None:
    """The fallback branch, stated so it is not mistaken for an accident: when
    every flow carries the OAuth signal there is no 'other' flow to scope the
    generic auth classes to, and an empty action would read as 'nothing
    unblocks this row'. It falls back to the spec's own keys."""
    signup = Flow(
        id="flow_signup", name="Sign up", entry_screen="scr_signup",
        steps=[
            Step(order=1, action=Action.CLICK, target="Sign up with Google"),
            Step(order=2, action=Action.FILL, target="Token",
                 value="{{SECRET:GOOGLE_SIGNUP_TOKEN}}"),
        ],
    )
    from autotester.schema.enums import CaseClass

    project = _project(secrets=[SecretRef(key="GOOGLE_SIGNUP_TOKEN", domains=["demo.test"])])
    cat = catalog(project, _approved_spec(signup), ProjectStore("demo", root))
    entry = cat.entry(CaseClass.AUTH_WRONG_CREDS)
    assert entry is not None and entry.unblock_action is not None
    assert "GOOGLE_SIGNUP_TOKEN" in entry.unblock_action


def test_a_hybrid_oauth_and_password_flow_still_blocks_the_auth_rows(root: Path) -> None:
    """ISS-t125-3 — one flow is BOTH an OAuth flow and the credential source.

    The checker's cycle-2 fixture, which cycle 2 got wrong: one flow both
    clicks "Sign up with Google" and fills the product's own password. Cycle 2
    read that whole flow as OAuth, so the auth rows showed a green `runnable`
    pill while the only declared secret was unset — an invisible omission that
    fails for real at run time, strictly worse than ISS-t125-2's over-naming."""
    from autotester.schema.enums import CaseClass

    hybrid = Flow(
        id="flow_hybrid", name="Sign up", entry_screen="scr_signup",
        steps=[Step(order=1, action=Action.CLICK, target="Sign up with Google"),
               Step(order=2, action=Action.FILL, target="Password",
                    value="{{SECRET:HYBRID_PASSWORD}}")],
    )
    browse = Flow(id="flow_browse", name="Browse", entry_screen="scr_login",
                  steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/")])
    project = _project(secrets=[SecretRef(key="HYBRID_PASSWORD", domains=["demo.test"])])
    cat = catalog(project, _approved_spec(hybrid, browse), ProjectStore("demo", root))
    for case_class in (CaseClass.AUTH_WRONG_CREDS, CaseClass.AUTH_EXPIRED_SESSION):
        entry = cat.entry(case_class)
        assert entry is not None
        assert entry.runnable is False, (
            f"{case_class.value} claims runnable while HYBRID_PASSWORD is unset"
        )
        assert entry.blocked_reason is BlockedReason.MISSING_CREDENTIAL
        assert entry.unblock_action and "HYBRID_PASSWORD" in entry.unblock_action
    pack = cat.pack(StandardPack.OAUTH_SIGNUP_CARRYOVER)
    assert pack is not None and pack.runnable is False
    assert pack.unblock_action and "HYBRID_PASSWORD" in pack.unblock_action
