"""T-209 (multi-role-platform.md MP10): a P0 finding's repro survives masking.

A local two-tenant fixture app (synthetic, test-only). The first run records a finding; a second
run replays ONLY the recorded steps read back from disk and must see the same number of foreign
rows. The same replay against a fixed app sees none, so the replay discriminates.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.schema.leak_evidence import LeakEvidence
from autotester.schema.multi_role_enums import FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding, ReproVerb, parse_repro_step
from autotester.stages.leak_evidence import write_finding

TENANTS = {"a": ["a1", "a2"], "b": ["b1", "b2", "b3"]}
ACCOUNTS = {"Parent": "a"}


class FixtureApp:
    """Lists the signed-in tenant's rows; the leaky build also honours 'Show all schools'."""

    def __init__(self, leaky: bool) -> None:
        self.leaky = leaky

    def visible(self, tenant: str, show_all: bool) -> list[tuple[str, str]]:
        scopes = list(TENANTS) if (self.leaky and show_all) else [tenant]
        return [(t, row) for t in scopes for row in TENANTS[t]]


def replay(app: FixtureApp, steps: list[str]) -> int:
    """Run recorded steps through the fixture; return the foreign rows on screen at the end."""
    tenant, show_all, page = "", False, "/"
    for step in steps:
        verb, target = parse_repro_step(step)
        if verb is ReproVerb.LOGIN:
            tenant = ACCOUNTS[target.removeprefix("as ").strip()]
        elif verb is ReproVerb.GOTO:
            page = target
        elif verb is ReproVerb.CLICK and target == "Show all schools":
            show_all = True
    assert page == "/students"
    return sum(1 for owner, _ in app.visible(tenant, show_all) if owner != tenant)


@pytest.fixture
def recorded(tmp_path: Path) -> MultiRoleFinding:
    steps = ["login as Parent", "goto /students", "click Show all schools"]
    seen = replay(FixtureApp(leaky=True), steps)
    ev = LeakEvidence(foreign_row_count=seen, field_names=["row"], url_template="/students")
    finding = MultiRoleFinding(
        finding_id="leak-replay", finding_class=FindingClass.DATA_LEAK,
        title="Parent sees tenant b", role="Parent", platform_id="parent",
        url_template="/students", steps=steps, count=seen, leak_evidence=ev)
    written = write_finding(tmp_path / "run", finding)
    return MultiRoleFinding.model_validate_json(written.read_text(encoding="utf-8"))


def test_replaying_the_recorded_repro_gives_the_same_count(recorded: MultiRoleFinding) -> None:
    assert recorded.count == 3
    assert replay(FixtureApp(leaky=True), recorded.steps) == recorded.count


def test_the_replay_discriminates_a_fixed_app(recorded: MultiRoleFinding) -> None:
    assert replay(FixtureApp(leaky=False), recorded.steps) == 0 != recorded.count


def test_every_p0_finding_carries_the_five_repro_fields(recorded: MultiRoleFinding) -> None:
    assert recorded.role and recorded.platform_id and recorded.url_template
    assert recorded.steps and recorded.count is not None
