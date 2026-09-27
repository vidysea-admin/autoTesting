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
