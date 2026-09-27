"""The record rules: does the ledger still hold what the handshake recorded?

Split from `test_doctor.py` alongside the module it tests (AT-506). That file is
the rules over SOURCE -- line caps, function length, duplicated concepts, root
clutter. These are the rules over the project's own ACCOUNT of itself, and the
three units that wrote them (AT-496, AT-500, AT-504) are what pushed both files
toward their caps.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotester.ledger import checks

# -- AT-496: a handshake artifact naming an issue that has no ledger row -------


def _qa(root: Path, ledger: str, manifests: dict | None = None,
        verdicts: dict | None = None) -> None:
    (root / "qa").mkdir(parents=True, exist_ok=True)
    (root / "qa" / "issues.jsonl").write_text(ledger, encoding="utf-8")
    for kind, files in (("manifests", manifests or {}), ("verdicts", verdicts or {})):
        (root / "qa" / kind).mkdir(exist_ok=True)
        for name, body in files.items():
            (root / "qa" / kind / name).write_text(body, encoding="utf-8")


ROW = '{"id": "AT-900", "severity": "low", "title": "t", "status": "%s"}'


def test_an_issue_a_manifest_names_must_still_have_a_ledger_row(tmp_path: Path) -> None:
    """AT-496: two loops share this tree, and a commit built from a stale copy of
    qa/issues.jsonl drops rows another loop appended. AT-494's row vanished that way
    while its verdict stayed in git — so the verdict is what makes the loss visible."""
    _qa(tmp_path, ledger="", manifests={"u.md": "**Issues addressed:** AT-900 (low, open)"})

    codes = [(v.rule, v.location) for v in checks.check_qa_issue_rows(tmp_path)]

    assert ("ledger-row-lost", "qa/manifests/u.md") in codes


def test_an_issue_a_verdict_wrote_must_still_have_a_ledger_row(tmp_path: Path) -> None:
    _qa(tmp_path, ledger=ROW % "open",
        verdicts={"u.md": "ISSUES-WRITTEN: AT-900 (low), AT-901 (medium)"})

    lost = [(v.rule, v.detail) for v in checks.check_qa_issue_rows(tmp_path)]

    assert [r for r, d in lost if "AT-901" in d] == ["ledger-row-lost"], lost
    assert not any("AT-900" in d for _, d in lost), "AT-900 has a row; only AT-901 is missing"


def test_a_passed_unit_whose_issue_is_still_open_is_a_stale_row(tmp_path: Path) -> None:
    """AT-401's row was flipped to `fixed` by its PASS and then reverted to `open` by a
    later stale write. Nothing noticed, because the verdict file was still right."""
    _qa(tmp_path, ledger=ROW % "open",
        manifests={"u.md": "**Issues addressed:** AT-900 (low, open -> fixed)"},
        verdicts={"u.md": "VERDICT: PASS"})

    codes = [v.rule for v in checks.check_qa_issue_rows(tmp_path)]

    assert "ledger-row-stale" in codes


def test_a_passed_unit_whose_issue_is_fixed_is_not_flagged(tmp_path: Path) -> None:
    _qa(tmp_path, ledger=ROW % "fixed",
        manifests={"u.md": "**Issues addressed:** AT-900 (low, open -> fixed)"},
        verdicts={"u.md": "VERDICT: PASS"})

    assert checks.check_qa_issue_rows(tmp_path) == []


def test_a_failed_or_unchecked_unit_leaves_its_issue_open(tmp_path: Path) -> None:
    """Only a PASS is evidence the issue was closed; an open row is correct otherwise."""
    _qa(tmp_path, ledger=ROW % "open",
        manifests={"u.md": "**Issues addressed:** AT-900 (low, open -> fixed)"},
        verdicts={"u.md": "VERDICT: FAIL"})

    assert checks.check_qa_issue_rows(tmp_path) == []


def test_a_project_with_no_qa_directory_is_not_a_violation(tmp_path: Path) -> None:
    assert checks.check_qa_issue_rows(tmp_path) == []


@pytest.mark.parametrize("issue", ["AT-900", "AT-900b"])
def test_a_letter_suffixed_id_is_an_id_too(issue: str, tmp_path: Path) -> None:
    r"""AT-500: when two checkers file the same defect, the second row takes a letter
    suffix — AT-297b, AT-298b and AT-299b are live rows filed under that convention.
    Both regexes ended at a word boundary straight after the digits, and `\bAT-\d+\b`
    matches nothing at all inside `AT-297b`, so a manifest naming one was invisible."""
    _qa(tmp_path, ledger="", manifests={"u.md": f"**Issues addressed:** {issue} (low, open)"})

    lost = [(v.rule, v.detail) for v in checks.check_qa_issue_rows(tmp_path)]

    assert [r for r, d in lost if issue in d] == ["ledger-row-lost"], lost


@pytest.mark.parametrize("issue", ["AT-900", "AT-900b"])
def test_a_letter_suffixed_id_is_read_on_both_sides_of_the_comparison(
    issue: str, tmp_path: Path
) -> None:
    """Widening only the handshake side would turn every suffixed row into a phantom
    loss: the id is read a second time out of the LEDGER, and the two must agree or
    the check reports a row it is looking at as missing."""
    _qa(tmp_path, ledger=ROW.replace("AT-900", issue) % "open",
        manifests={"u.md": f"**Issues addressed:** {issue} (low, open -> fixed)"},
        verdicts={"u.md": "VERDICT: PASS"})

    codes = [v.rule for v in checks.check_qa_issue_rows(tmp_path)]

    assert codes == ["ledger-row-stale"], "the row EXISTS (never lost), it is only stale"


def test_an_issue_a_manifest_says_it_did_NOT_fix_stays_open(tmp_path: Path) -> None:
    """A manifest may name issues it filed and deliberately left open —
    `at227-first-paint-modal` names AT-335 that way. Reading "NOT fixed" as a fix
    claim made that unit's PASS look like a stale row."""
    _qa(tmp_path, ledger=ROW % "open",
        manifests={"u.md": "**Issues addressed:** AT-900 (filed, NOT fixed - reasons below)"},
        verdicts={"u.md": "VERDICT: PASS"})

    assert checks.check_qa_issue_rows(tmp_path) == []


@pytest.mark.parametrize("note", [
    "low, unfixed - tracked separately",
    "low, not-fixed, deferred",
    "low, not yet fixed",
    "low, prefixed by an earlier note",
])
def test_a_word_that_merely_contains_fixed_is_not_a_fix_claim(note: str,
                                                              tmp_path: Path) -> None:
    """AT-508: the claim test was a bare substring, excluding only the exact phrase
    "not fixed", so "unfixed" read as a fix claim. It then accused a manifest that had
    CORRECTLY declared an issue unfixed of leaving a stale row — the very case the
    filter exists to protect, and a false accusation is worse than a miss. Live since
    AT-496; found by a fresh engineering review, not by the four units built on it."""
    _qa(tmp_path, ledger=ROW % "open",
        manifests={"u.md": f"**Issues addressed:** AT-900 ({note})"},
        verdicts={"u.md": "VERDICT: PASS"})

    assert checks.check_qa_issue_rows(tmp_path) == []


@pytest.mark.parametrize("note", [
    "low, open -> fixed",
    "medium, open → fixed",
    "fixed",
    "not a duplicate, open -> fixed",
])
def test_a_real_fix_claim_still_counts(note: str, tmp_path: Path) -> None:
    """Over-tightening is the dangerous direction. Both `->` and the unicode arrow are
    live in this repo's manifests, a bare `(fixed)` is too, and the negation must not
    swallow a `not` belonging to a different clause — hence a character class that
    cannot cross a comma. Measured over all 54 distinct live notes: none changes."""
    _qa(tmp_path, ledger=ROW % "open",
        manifests={"u.md": f"**Issues addressed:** AT-900 ({note})"},
        verdicts={"u.md": "VERDICT: PASS"})

    assert [v.rule for v in checks.check_qa_issue_rows(tmp_path)] == ["ledger-row-stale"]


# -- AT-523/AT-524: a CLI -q must never stack on pyproject.toml's own addopts -q --


def _pyproject(root: Path, addopts: str = "-q") -> None:
    (root / "pyproject.toml").write_text(
        f'[tool.pytest.ini_options]\naddopts = "{addopts}"\n', encoding="utf-8")


def _adapter(root: Path, cmd: str) -> None:
    (root / "qa").mkdir(parents=True, exist_ok=True)
    (root / "qa" / "adapter.json").write_text(
        json.dumps({"verify": {"commands": [{"cmd": cmd, "expect": "exit 0"}]}}),
        encoding="utf-8")


def _goal(root: Path, tasks: list[dict]) -> None:
    (root / ".goal").mkdir(parents=True, exist_ok=True)
    (root / ".goal" / "goal.json").write_text(json.dumps({"tasks": tasks}), encoding="utf-8")


def test_adapter_command_matching_addopts_is_not_flagged(tmp_path: Path) -> None:
    _pyproject(tmp_path, "-q")
    _adapter(tmp_path, "uv run pytest")

    assert checks.check_adapter_pytest_q(tmp_path) == []


def test_adapter_command_stacking_cli_q_on_addopts_is_flagged(tmp_path: Path) -> None:
    """AT-503's own defect: pyproject's addopts already sets one -q; a second one on
    the CLI reaches -qq, which prints no summary line at all."""
    _pyproject(tmp_path, "-q")
    _adapter(tmp_path, "uv run pytest -q")

    codes = [v.rule for v in checks.check_adapter_pytest_q(tmp_path)]

    assert codes == ["pytest-q-doubled"]


def test_an_explicit_addopts_override_is_not_a_doubling(tmp_path: Path) -> None:
    """`-o addopts=` REPLACES pyproject's addopts for that one invocation (pytest's
    own rule) — AT-506's own subset runs rely on exactly this to add a bare -q
    safely. A guard that only grepped for the literal string '-q' would misfire
    here; this one must actually reason about what addopts is FOR this command."""
    _pyproject(tmp_path, "-q")
    _adapter(tmp_path, "uv run pytest -q -o addopts= tests/test_x.py")

    assert checks.check_adapter_pytest_q(tmp_path) == []


def test_the_guard_reads_addopts_live_rather_than_assuming_it(tmp_path: Path) -> None:
    """A guard that hardcoded "-q is always one too many" would misfire the moment
    addopts stops setting one. This proves the count is derived from the live
    pyproject.toml, not a copy of today's value baked into the rule."""
    _pyproject(tmp_path, "")
    _adapter(tmp_path, "uv run pytest -q")

    assert checks.check_adapter_pytest_q(tmp_path) == []


def test_a_missing_adapter_or_pyproject_is_not_a_violation(tmp_path: Path) -> None:
    assert checks.check_adapter_pytest_q(tmp_path) == []


def test_goal_json_cmd_row_stacking_cli_q_is_flagged_with_its_task_id(tmp_path: Path) -> None:
    """AT-524: the same defect, extended to .goal/goal.json's ~50 done_check rows —
    43 of them carried it until AT-521/AT-522 swept the live file by hand."""
    _pyproject(tmp_path, "-q")
    _goal(tmp_path, [{"id": "T-160",
                      "done_check": {"type": "cmd", "cmd": "uv run pytest tests/x.py -q"}}])

    violations = checks.check_goal_pytest_q(tmp_path)

    assert [(v.rule, v.location) for v in violations] == \
        [("pytest-q-doubled", ".goal/goal.json:T-160")]


def test_a_non_cmd_done_check_is_not_inspected(tmp_path: Path) -> None:
    _pyproject(tmp_path, "-q")
    _goal(tmp_path, [{"id": "T-004", "done_check": {"type": "file", "path": "docs/x.md"}}])

    assert checks.check_goal_pytest_q(tmp_path) == []


def test_only_the_pytest_sub_command_of_a_chained_cmd_is_checked(tmp_path: Path) -> None:
    """A trailing -q after && belongs to a DIFFERENT program; only the pytest
    invocation's own flags may stack on top of addopts."""
    _pyproject(tmp_path, "-q")
    _goal(tmp_path, [{"id": "T-005",
                      "done_check": {"type": "cmd",
                                     "cmd": "uv run pytest tests/x.py && "
                                            "uv run autotester doctor -q"}}])

    assert checks.check_goal_pytest_q(tmp_path) == []


def test_a_missing_goal_json_is_not_a_violation(tmp_path: Path) -> None:
    _pyproject(tmp_path, "-q")

    assert checks.check_goal_pytest_q(tmp_path) == []


def test_a_row_is_found_whatever_order_its_keys_are_in(tmp_path: Path) -> None:
    """AT-571: the row reader matched `"id" ... "status"` with a regex, so a row
    serialized status-first (AT-568/569/570 on 2026-09-25) was invisible and doctor
    reported it lost. A JSON row's key order carries no meaning; neither may ours."""
    row = json.dumps({"status": "open", "id": "AT-900", "severity": "low", "title": "t"})
    _qa(tmp_path, ledger=row + "\n", manifests={"u.md": "**Issues addressed:** AT-900 (low, open)"})
    assert checks.check_qa_issue_rows(tmp_path) == []
