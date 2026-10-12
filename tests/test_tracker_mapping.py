"""T-199c: the tracker mapping is proposed from the header, inert until confirmed (TB8, TB14)."""

from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path

import pytest
from bug_loop_fixture import T0
from sheet_fake import FakeSheet
from tracker_fakes import ALLOWED, LAYOUT_A, LAYOUT_B, RecordingProvider, binding

from autotester.schema.tracker_binding import MappingStatus
from autotester.stages import tracker_mapping as mapping_mod
from autotester.stages.tracker_mapping import (
    MappingNotConfirmed,
    NotAllowed,
    check_header,
    confirm_mapping,
    mapping_columns,
    propose_mapping,
    rebind,
)
from autotester.store.tracker_store import WrongProject, load_binding, save_binding

NOW = T0 + timedelta(days=1)


def _proposed(header: list[str], **kw):
    return binding().model_copy(update={"mapping": propose_mapping(header, **kw)})


def test_tb8_deterministic_proposal_from_the_header_alone() -> None:
    m = propose_mapping(LAYOUT_A)
    assert m.status is MappingStatus.PROPOSED and m.confirmed_by is None
    assert m.columns["bug_key"] == "Bug ID" and m.columns["title"] == "Bug Title"
    assert m.columns["date"] == "Date Reported" and m.columns["screenshot_link"] == "Screenshot"
    assert m.unmapped == {}


def test_tb8_none_or_two_candidates_is_unmapped_with_the_candidates_listed() -> None:
    m = propose_mapping(["Bug ID", "Title", "Summary", "Severity"])
    assert "title" not in m.columns and m.unmapped["title"] == ["Title", "Summary"]
    assert m.unmapped["status"] == []
    assert m.columns["bug_key"] == "Bug ID"


def test_tb8_the_header_read_is_the_only_read_and_the_client_is_never_written() -> None:
    sheet = FakeSheet(LAYOUT_A, [["1", "k1", "secret-row-value"]])
    propose_mapping(sheet.read_header("s", "Bugs"))
    assert [c[0] for c in sheet.calls] == ["read_header"]


def test_tb8_the_provider_payload_is_header_cells_only_and_scrubbed() -> None:
    sheet = FakeSheet([*LAYOUT_B, "token-hunter2"], [["R1", "A SECRET ROW VALUE"]])
    provider = RecordingProvider({"title": "What broke"})
    m = propose_mapping(sheet.read_header("s", "Bugs"), provider=provider,
                        scrub=lambda t: t.replace("hunter2", "[REDACTED]"))
    assert len(provider.prompts) == 1
    sent = provider.prompts[0]
    assert "A SECRET ROW VALUE" not in sent and "hunter2" not in sent
    assert all(cell in sent for cell in LAYOUT_B[:3])
    assert m.columns["title"] == "What broke" and m.status is MappingStatus.PROPOSED


def test_tb8_a_fallback_answer_that_is_not_a_shown_header_is_ignored() -> None:
    provider = RecordingProvider({"title": "Invented", "bug_key": "Ref"})
    m = propose_mapping(LAYOUT_B, provider=provider)
    assert "title" not in m.columns and m.columns["bug_key"] == "Ref"


def test_tb8_a_proposed_mapping_cannot_feed_a_write_path() -> None:
    with pytest.raises(MappingNotConfirmed):
        mapping_columns(_proposed(LAYOUT_A))


def test_tb8_only_a_holder_of_project_edit_confirms_and_who_and_when_are_recorded() -> None:
    proposed = _proposed(LAYOUT_A)
    with pytest.raises(NotAllowed):
        confirm_mapping(proposed, "mallory", ALLOWED, NOW)
    assert proposed.mapping.status is MappingStatus.PROPOSED  # unchanged
    done = confirm_mapping(proposed, "umesh.s", ALLOWED, NOW)
    assert (done.mapping.status, done.mapping.confirmed_by, done.mapping.confirmed_at) == (
        MappingStatus.CONFIRMED, "umesh.s", NOW)
    cols = mapping_columns(done)
    assert cols.columns["first_seen"] == "Date Reported" and "screenshot_link" not in cols.columns


def test_tb8_the_machine_actor_cannot_confirm_even_if_allowed() -> None:
    with pytest.raises(ValueError):
        confirm_mapping(_proposed(LAYOUT_A), "system:bug-loop", lambda u, p: True, NOW)


def test_tb8_no_bug_key_column_cannot_be_confirmed() -> None:
    with pytest.raises(MappingNotConfirmed):
        confirm_mapping(_proposed(["Title", "Status"]), "umesh.s", ALLOWED, NOW)


def test_tb8_a_renamed_or_moved_header_makes_the_mapping_stale_and_refuses_writes() -> None:
    done = confirm_mapping(_proposed(LAYOUT_A), "umesh.s", ALLOWED, NOW)
    assert check_header(done, LAYOUT_A).mapping.status is MappingStatus.CONFIRMED
    renamed = [h if h != "Severity" else "Sev." for h in LAYOUT_A]
    moved = [LAYOUT_A[1], LAYOUT_A[0], *LAYOUT_A[2:]]
    for header in (renamed, moved):
        stale = check_header(done, header)
        assert stale.mapping.status is MappingStatus.STALE
        with pytest.raises(MappingNotConfirmed):
            mapping_columns(stale)
        with pytest.raises(MappingNotConfirmed):
            confirm_mapping(stale, "umesh.s", ALLOWED, NOW)


def test_tb13_changing_the_sheet_id_leaves_the_binding_unconfirmed() -> None:
    done = confirm_mapping(_proposed(LAYOUT_A), "umesh.s", ALLOWED, NOW)
    other = rebind(done, sheet_id="another_sheet")
    assert other.sheet_id == "another_sheet" and other.first_write is None
    assert other.mapping.status is MappingStatus.PROPOSED
    with pytest.raises(MappingNotConfirmed):
        mapping_columns(other)
    assert rebind(done, sheet_id="sheet_demo") is done


def test_tb14_two_layouts_one_code_path() -> None:
    a = confirm_mapping(_proposed(LAYOUT_A), "umesh.s", ALLOWED, NOW)
    b = confirm_mapping(_proposed(LAYOUT_B), "umesh.s", ALLOWED, NOW)
    assert mapping_columns(a).columns["bug_key"] == "Bug ID"
    assert mapping_columns(b).columns["bug_key"] == "Ref"
    assert b.mapping.unmapped["title"] == []


def test_tb14_bindings_are_per_project_and_never_read_across(tmp_path: Path) -> None:
    save_binding(binding("alpha", "sheet_a"), tmp_path)
    save_binding(binding("beta", "sheet_b"), tmp_path)
    assert load_binding("alpha", tmp_path).sheet_id == "sheet_a"
    assert load_binding("beta", tmp_path).sheet_id == "sheet_b"
    assert load_binding("gamma", tmp_path) is None
    (tmp_path / "projects" / "beta" / "tracker.json").write_text(
        (tmp_path / "projects" / "alpha" / "tracker.json").read_text(encoding="utf-8"),
        encoding="utf-8")
    with pytest.raises(WrongProject):
        load_binding("beta", tmp_path)


def test_tb14_no_tracker_stage_names_a_product() -> None:
    src = Path(mapping_mod.__file__).parent
    text = "".join(p.read_text(encoding="utf-8") for p in src.glob("tracker_*.py"))
    assert not re.search(r"pathlynks", text, re.I)
