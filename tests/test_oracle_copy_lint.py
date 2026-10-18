"""T-216 (multi-role-platform.md MP25): the copy, branding and timezone lint.

Synthetic rule matrix (MPI2): each declared brand term misspelt once, each forbidden string
present once, and a timestamp in each of two arbitrary zones other than the declared display zone;
a control page with none is clean. Page text is held in memory only: no finding and no file under
the run directory may carry it (MPI1), including a planted canary email and phone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from surface_fakes import PlainPort, SurfacePort, context, text

from autotester.schema.lint_rule import LintKind, LintRule, SurfaceChecks, TextOrigin
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.oracle_context import OracleState
from autotester.stages import oracle_copy_lint as lint
from autotester.stages.finding_priority import priority_for
from autotester.stages.oracle_registry import run_oracles

BRANDS = ["PathLynks", "Vidysea"]
FORBIDDEN = ["lorem ipsum", "TODO"]
DISPLAY = "IST"
CANARY_MAIL, CANARY_PHONE = "zorblax.quimby@canary.invalid", "+1 (555) 013-7788"


def rules() -> list[LintRule]:
    out = [LintRule(id=f"brand-{b.lower()}", kind=LintKind.BRAND_TERM, value=b) for b in BRANDS]
    out += [LintRule(id=f"forbid-{i}", kind=LintKind.FORBIDDEN_STRING, value=s)
            for i, s in enumerate(FORBIDDEN)]
    out.append(LintRule(id="tz-display", kind=LintKind.DISPLAY_TIMEZONE, value=DISPLAY))
    return out


def declare(run_dir: Path, rule_list: list[LintRule] | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    checks = SurfaceChecks(rules=rule_list if rule_list is not None else rules())
    (run_dir / "surface_checks.json").write_text(checks.model_dump_json(), encoding="utf-8")


def run_lint(run_dir: Path, texts: list) -> list:
    declare(run_dir)
    return lint.run(context(run_dir, SurfacePort(texts)))


def cells(found: list) -> set[tuple[str, str]]:
    """(rule id, screen) pairs: the title cites both."""
    return {(f.title.split(":")[0], f.title.split(" on ")[1].split(" ")[0]) for f in found}


MATRIX = [
    text("misspelt-a", "Welcome to Pathlynks, your portal"),
    text("misspelt-b", "Powered by Vidysae"),
    text("forbidden-a", "Heading is lorem ipsum dolor"),
    text("forbidden-b", "Fix this TODO before launch"),
    text("zone-pst", "Posted 2026-10-19 09:30 PST"),
    text("zone-offset", "Posted 2026-10-19T09:30:00+02:00"),
]
EXPECTED = {("brand-pathlynks", "misspelt-a"), ("brand-vidysea", "misspelt-b"),
            ("forbid-0", "forbidden-a"), ("forbid-1", "forbidden-b"),
            ("tz-display", "zone-pst"), ("tz-display", "zone-offset")}


def test_every_cell_of_the_rule_matrix_is_reported(tmp_path: Path) -> None:
    found = run_lint(tmp_path, MATRIX)
    assert cells(found) == EXPECTED
    assert len(found) == len(EXPECTED)
    for f in found:
        assert f.finding_class is FindingClass.COPY_OR_BRANDING
        assert f.oracle is OracleName.COPY_LINT
        assert priority_for(f.finding_class).value == "P2"


def test_control_page_is_clean(tmp_path: Path) -> None:
    clean = [text("home", "Welcome to PathLynks by Vidysea. Posted 2026-10-19 15:00 IST."),
             text("iso", "Updated 2026-10-19T09:30:00+05:30 and 10:30 AM, open 09:00-12:00"),
             text("mail", "Hello from PathLynks", kind=TextOrigin.MAIL)]
    assert run_lint(tmp_path, clean) == []


@pytest.mark.parametrize(("display", "stamp", "hit"), [
    ("UTC", "Due 2026-10-19T09:00:00+05:30", True),
    ("+05:30", "Due 09:00 UTC", True),
    ("EST", "Due 09:00 EST", False),
    ("UTC+5:30", "Due 14:30 IST", False),
    ("Z", "Due 2026-10-19T09:00:00Z", False),
    ("PST", "Due 11:00 PM JST", True),
    ("JST", "Due 11:00 PM JST", False),
])
def test_timezone_rule_compares_zones_not_names(tmp_path: Path, display: str, stamp: str,
                                                hit: bool) -> None:
    declare(tmp_path, [LintRule(id="tz", kind=LintKind.DISPLAY_TIMEZONE, value=display)])
    found = lint.run(context(tmp_path, SurfacePort([text("s", stamp)])))
    assert bool(found) is hit


def test_mail_bodies_are_linted_and_cited_as_a_message(tmp_path: Path) -> None:
    mail = text("welcome-mail", "Dear parent, TODO insert name", kind=TextOrigin.MAIL, url=None)
    found = run_lint(tmp_path, [mail])
    assert len(found) == 1
    assert found[0].url_template == "/mail/{id}"
    assert "mail" in found[0].title and "welcome-mail" in found[0].title


def test_no_page_text_reaches_a_finding_or_a_file(tmp_path: Path) -> None:
    body = f"Pathlynks contact {CANARY_MAIL} or {CANARY_PHONE}; Zorblax Quimby TODO"
    found = run_lint(tmp_path, [text("contacts", body)])
    assert found
    blob = json.dumps([f.model_dump(mode="json") for f in found])
    for canary in (CANARY_MAIL, CANARY_PHONE, "Zorblax", "013-7788"):
        assert canary not in blob
    written = [p.name for p in tmp_path.rglob("*") if p.is_file()]
    assert written == ["surface_checks.json"]


def test_occurrences_are_counted_per_cell(tmp_path: Path) -> None:
    found = run_lint(tmp_path, [text("s", "TODO one. TODO two. TODO three.")])
    assert [f.count for f in found] == [3]


def test_an_undeclared_rule_set_is_an_error_not_a_clean_pass(tmp_path: Path) -> None:
    with pytest.raises(lint.SurfaceDeclarationMissing):
        lint.run(context(tmp_path, SurfacePort([text("s", "TODO")])))
    declare(tmp_path, [])
    with pytest.raises(lint.SurfaceDeclarationMissing):
        lint.run(context(tmp_path, SurfacePort([])))


def test_a_port_without_text_access_is_reported_errored(tmp_path: Path) -> None:
    declare(tmp_path)
    summary, found = run_oracles(context(tmp_path, PlainPort()), [OracleName.COPY_LINT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.COPY_LINT)
    assert (status.state, status.reason) == (OracleState.ERRORED, "SurfaceUnavailable")
    assert found == []


def test_the_registry_runs_the_oracle_end_to_end(tmp_path: Path) -> None:
    declare(tmp_path)
    summary, found = run_oracles(context(tmp_path, SurfacePort(MATRIX)), [OracleName.COPY_LINT])
    status = next(s for s in summary.statuses if s.oracle is OracleName.COPY_LINT)
    assert (status.state, status.finding_count) == (OracleState.RAN, len(EXPECTED))
    assert len(found) == len(EXPECTED)


@pytest.mark.parametrize("bad", [
    {"id": "r", "kind": "brand_term", "value": "mail me at a@b.example"},
    {"id": "r", "kind": "display_timezone", "value": "Mars/Olympus"},
    {"id": "R!", "kind": "forbidden_string", "value": "x"},
    {"id": "r", "kind": "forbidden_string", "value": "x", "extra": 1},
])
def test_rule_shapes_are_closed(bad: dict) -> None:
    with pytest.raises(ValidationError):
        LintRule(**bad)
