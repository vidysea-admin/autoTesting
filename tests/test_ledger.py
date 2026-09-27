"""Living map + feature ledger. Contract: qa/contracts/living-ledger.md L1-L6."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from autotester.core.paths import RepoDocs
from autotester.ledger import render, store
from autotester.ledger.relitigation import gate_message, relitigate
from autotester.providers.mock import MockProvider
from autotester.schema.enums import FeatureEventKind, UserValue
from autotester.schema.ledger import FeatureEvent, RelitigationVerdict


def make_docs(tmp_path: Path) -> RepoDocs:
    # AT-137: prompts_dir named explicitly rather than inferred from `root`.
    docs = RepoDocs(tmp_path, prompts_dir=tmp_path / "src" / "autotester" / "prompts")
    docs.docs_dir.mkdir()
    docs.architecture.write_text(
        "# X\n\n**Purpose:** p\n**Open me when:** w\n\n## What it does\n\nIt tests things.\n",
        encoding="utf-8",
    )
    docs.map.write_text(
        "# map\n\n**Purpose:** p\n**Open me when:** w\n\n"
        "<!-- generated:map -->\n<!-- /generated:map -->\n"
        "<!-- generated:schema -->\n<!-- /generated:schema -->\n"
        "<!-- generated:scripts -->\n<!-- /generated:scripts -->\n",
        encoding="utf-8",
    )
    pkg = tmp_path / "src" / "autotester"
    (pkg / "schema").mkdir(parents=True)
    (pkg / "thing.py").write_text('"""Does one thing."""\n', encoding="utf-8")
    (pkg / "schema" / "m.py").write_text('class Widget:\n    """A widget."""\n', encoding="utf-8")
    docs.prompts_dir.mkdir(parents=True)
    prompt = docs.prompts_dir / "relitigation_v1.md"
    prompt.write_text("{{RETIRED_ROWS}}\n---\n{{UNIT}}", encoding="utf-8")
    return docs


# -- AT-137: prompts_dir named explicitly, not inferred from `root` alone ---

def test_an_explicit_prompts_dir_wins_over_root(tmp_path: Path) -> None:
    stub = tmp_path / "some" / "other" / "prompts"
    docs = RepoDocs(tmp_path, prompts_dir=stub)
    assert docs.prompts_dir == stub


def test_root_alone_still_behaves_exactly_as_before(tmp_path: Path) -> None:
    """No behaviour change (C2) for a caller that never adopts the explicit
    form — this is the AT-132 fallback the docstring already documents."""
    docs = RepoDocs(tmp_path)
    assert docs.prompts_dir == tmp_path / "src" / "autotester" / "prompts"


def row(events: list[FeatureEvent], **kw) -> FeatureEvent:
    base = dict(feature="login-otp", title="OTP via email link", event=FeatureEventKind.LIVE,
                description="user signs in with a one-time link sent by email",
                user_value=UserValue.HIGH, on=date(2026, 9, 1))
    base.update(kw)
    return store.new_event(events, **base)


# -- L2: rows, reasons, weights ------------------------------------------

def test_retired_row_refuses_the_auto_reason(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="real reason"):
        row([], event=FeatureEventKind.RETIRED)


def test_normal_value_auto_stamps_update_and_never_asks(tmp_path: Path) -> None:
    r = row([], user_value=UserValue.NORMAL)
    assert r.reason == "update" and r.ask_required is False


def test_high_value_with_auto_reason_asks(tmp_path: Path) -> None:
    r = row([], user_value=UserValue.HIGH)
    assert r.ask_required is True
    assert row([], reason="users asked for magic links").ask_required is False


def test_append_is_the_only_write_path_and_ids_are_sequential(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    first = store.append_event(docs.features, row([]))
    later = store.load_events(docs.features)
    second = store.append_event(docs.features, row(later, feature="dash"))
    assert (first.id, second.id) == ("F-001", "F-002")
    with pytest.raises(ValueError, match="already exists"):
        store.append_event(docs.features, first)
    assert len(docs.features.read_text(encoding="utf-8").splitlines()) == 2


def test_malformed_row_names_its_line(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    docs.features.write_text('{"id": "F-001", "nope": 1}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape("FEATURES.jsonl:1")):
        store.load_events(docs.features)


def test_raising_weight_to_high_asks_once(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    store.append_event(docs.features, row([], user_value=UserValue.NORMAL))
    r = store.raise_weight(docs.features, "login-otp", UserValue.HIGH)
    assert r.event is FeatureEventKind.UPDATED and r.ask_required is True
    with pytest.raises(ValueError, match="unknown feature"):
        store.raise_weight(docs.features, "ghost", UserValue.HIGH)


# -- L3: row on PASS ----------------------------------------------------------

def test_check_rows_on_pass_flags_closed_high_tasks_without_a_row() -> None:
    events = [row([], unit="T-011")]
    tasks = [
        {"id": "T-011", "status": "done", "user_value": "high"},
        {"id": "T-041", "status": "done", "user_value": "high"},
        {"id": "T-000", "status": "done", "user_value": "normal"},
    ]
    assert store.check_rows_on_pass(events, tasks) == ["T-041"]


# -- L1: derived, never typed ---------------------------------------------------

def test_map_is_derived_from_docstrings_and_doctor_sees_staleness(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    fresh = render.apply_map(docs)
    assert "| `thing.py` | Does one thing. |" in fresh
    assert "| `Widget` (`schema/m.py`) | A widget. |" in fresh
    assert fresh != docs.map.read_text(encoding="utf-8")  # not yet regenerated
    docs.map.write_text(fresh, encoding="utf-8")
    assert render.apply_map(docs) == docs.map.read_text(encoding="utf-8")


def test_replace_generated_requires_markers() -> None:
    with pytest.raises(ValueError, match="markers"):
        render.replace_generated("no markers here", "map", "x")


# -- AT-520: scripts/ is a routed doc section too, not a blind spot ---------

def test_scripts_section_covers_py_and_ps1_and_doctor_sees_staleness(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "do_thing.py").write_text('"""Does the other thing."""\n', encoding="utf-8")
    (scripts_dir / "do_other.ps1").write_text(
        "# do_other.ps1 -- explains itself in its header comment\n"
        "Write-Host 'hi'\n",
        encoding="utf-8",
    )
    fresh = render.apply_map(docs)
    assert "| `scripts/do_thing.py` | Does the other thing. |" in fresh
    assert (
        "| `scripts/do_other.ps1` | do_other.ps1 -- explains itself in its header comment |"
        in fresh
    )
    assert fresh != docs.map.read_text(encoding="utf-8")  # not yet regenerated
    docs.map.write_text(fresh, encoding="utf-8")
    assert render.apply_map(docs) == docs.map.read_text(encoding="utf-8")


def test_a_ps1_script_with_no_header_comment_gets_a_placeholder(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "bare.ps1").write_text("Write-Host 'no header here'\n", encoding="utf-8")
    fresh = render.apply_map(docs)
    assert "| `scripts/bare.ps1` | (no description) |" in fresh


# -- L5: lean snapshot -------------------------------------------------------

def test_snapshot_is_lean_and_shows_high_features_with_reason(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    why = "students lose passwords; OTP link cut support tickets"
    store.append_event(docs.features, row([], reason=why))
    (tmp_path / ".goal").mkdir()
    docs.goal.write_text(json.dumps({"tasks": [
        {"id": "T-010", "status": "pending", "user_value": "normal", "title": "browser session"}]}),
        encoding="utf-8")
    docs.decisions.write_text(
        "## D-001 | 2026-09-01 | type: decision | status: ACTIVE\n**What:** a\n"
        "## D-002 | 2026-09-02 | type: decision | status: ACTIVE\n"
        "**Supersedes:** D-001 -- b was better\n",
        encoding="utf-8")
    text = render.render_snapshot(docs)
    assert text.count("\n") <= render.SNAPSHOT_MAX_LINES
    assert "**Open me when:**" in text
    assert "F-001 **OTP via email link** [high]" in text and "cut support tickets" in text
    assert "- T-010 [normal] browser session" in text
    assert "D-001 2026-09-01 decision SUPERSEDED (by D-002)" in text


# -- L4: relitigation, confidence-gated -------------------------------------

def test_no_retired_rows_means_no_model_call(tmp_path: Path) -> None:
    judge = MockProvider()
    verdict = relitigate("2FA handling for login", [], judge, make_docs(tmp_path))
    assert verdict.gate is False and verdict.decided_by == "rule" and judge.prompts == []


def test_explicit_feature_id_is_a_certain_match_without_the_model(tmp_path: Path) -> None:
    retired = [row([], event=FeatureEventKind.RETIRED, reason="magic links were phished")]
    judge = MockProvider()
    verdict = relitigate("re-add F-001 magic links", retired, judge, make_docs(tmp_path))
    assert verdict.gate and verdict.decided_by == "rule" and judge.prompts == []


def test_paraphrased_unit_goes_to_the_judge_with_descriptions_and_gates(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    retired = [row([], event=FeatureEventKind.RETIRED, reason="magic links were phished")]
    judge = MockProvider(responses={"judge": [RelitigationVerdict(
        same_behaviour=True, matched_feature_id="F-001",
        justification="2FA over email link is the phished flow again", confidence=0.86)]})
    verdict = relitigate("2FA handling for login", retired, judge, docs)
    assert verdict.gate and verdict.decided_by == "llm"
    prompt = judge.prompts[0][1]
    assert "one-time link sent by email" in prompt and "magic links were phished" in prompt
    message = gate_message(verdict, retired)
    assert "retired on 2026-09-01" in message and "magic links were phished" in message
    assert "rebuild as-is" in message


def test_unrelated_unit_does_not_gate_when_judge_says_so(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    retired = [row([], event=FeatureEventKind.RETIRED, reason="magic links were phished")]
    judge = MockProvider(responses={"judge": [RelitigationVerdict(
        same_behaviour=False, justification="export shares nothing with login", confidence=0.9)]})
    assert relitigate("CSV export of reports", retired, judge, docs).gate is False


# -- L6: self-describing docs + router ----------------------------------------

def test_doc_header_and_router_detection(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    assert render.doc_header_missing(docs.architecture) is False
    bare = docs.docs_dir / "notes.md"
    bare.write_text("# just notes\n", encoding="utf-8")
    assert render.doc_header_missing(bare) is True
    docs.router.write_text("| `docs/ARCHITECTURE.md` | when |\n", encoding="utf-8")
    assert render.router_paths(docs.router) == {"docs/ARCHITECTURE.md"}


# -- cycle-2 findings (AT-019..022) pinned ---------------------------------

def test_duplicate_id_pasted_by_hand_is_rejected_at_load(tmp_path: Path) -> None:
    docs = make_docs(tmp_path)
    store.append_event(docs.features, row([]))
    line = docs.features.read_text(encoding="utf-8")
    docs.features.write_text(line + line, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate id F-001"):
        store.load_events(docs.features)


def test_doctor_reports_a_broken_ledger_instead_of_raising(tmp_path: Path) -> None:
    from autotester.ledger import checks

    docs = make_docs(tmp_path)
    docs.features.write_text("{not json\n", encoding="utf-8")
    found = checks.check_ledger(tmp_path)
    assert [v.rule for v in found] == ["ledger-invalid"]


def test_architecture_over_budget_is_a_doctor_violation(tmp_path: Path) -> None:
    from autotester import doctor

    docs = make_docs(tmp_path)
    assert doctor.check_architecture_budget(tmp_path) == []
    docs.architecture.write_text("x\n" * (render.ARCHITECTURE_MAX_LINES + 1), encoding="utf-8")
    assert [v.rule for v in doctor.check_architecture_budget(tmp_path)] == ["architecture-too-long"]


def test_snapshot_rolls_up_high_features_past_the_cap(tmp_path: Path) -> None:
    """AT-613: the newest feature (last appended) must be in the shown slice, not pushed out."""
    docs = make_docs(tmp_path)
    newest = None
    for i in range(render.HIGH_FEATURES_SHOWN + 2):
        newest = store.append_event(docs.features, row(store.load_events(docs.features),
                                              feature=f"feat-{i}", reason="why"))
    text = render.render_snapshot(docs)
    assert "+2 more high-value features" in text
    assert f"{newest.id} **{newest.title}**" in text
    assert text.count("\n") <= render.SNAPSHOT_MAX_LINES


def test_doctor_run_reports_a_broken_ledger_without_a_traceback(tmp_path: Path) -> None:
    """AT-021: the user-facing `doctor.run()` path, not check_ledger in isolation."""
    from autotester import doctor

    docs = make_docs(tmp_path)
    (tmp_path / "tests").mkdir()
    docs.features.write_text("{not json" + chr(10), encoding="utf-8")
    rules = {v.rule for v in doctor.run(tmp_path)}
    assert "ledger-invalid" in rules and "stale-generated" in rules
