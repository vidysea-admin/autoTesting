"""The report message and the outbox adapter (hosting.md HO26, HO28; team-test-button.md TT8).

Covers what is pure: composition of the message from a stored summary, the dry-run outbox, the
opt-in rule. The route-level rows (recipient follows the session, forged `to` in a POST) belong
to the phase that has sessions and are not claimed here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from delivery_fakes import CANARY_PAGE, CANARY_SECRET, NOW, recipient, summary
from pydantic import ValidationError

from autotester.core.redact import Redactor
from autotester.delivery.email import OutboxAdapter, TransportError, may_email, select_transport
from autotester.delivery.message import TEMPLATE_PATH, render_message
from autotester.schema.delivery import (
    DeliveryStatus,
    NotificationPref,
    ReportLabel,
    ReportSummary,
    RunCounts,
)


def test_body_carries_exactly_the_ho28_fields() -> None:
    msg = render_message(summary())
    for needle in ("Demo Shop", "run-0001", "2026-10-11 12:00 UTC", "Passed: 7", "Failed: 2",
                   "Blocked: 1", "Inconclusive: 3", "Coverage: 12 of 15 screens visited (80%)",
                   "failed", "https://tester.example.test/runs/run-0001", "sign in"):
        assert needle.lower() in msg.body.lower(), needle
    assert msg.subject == "AutoTester report: Demo Shop - failed"
    assert "\n" not in msg.subject and "attach" not in msg.body.lower()


def test_template_is_a_file_and_the_renderer_holds_no_inline_body() -> None:
    assert TEMPLATE_PATH.is_file() and TEMPLATE_PATH.suffix == ".txt"
    source = (Path(__file__).resolve().parents[1] / "src/autotester/delivery/message.py"
              ).read_text("utf-8")
    assert "Passed:" not in source and "Coverage" not in source


def test_message_passes_the_redactor_so_a_planted_secret_is_masked() -> None:
    red = Redactor({"PLANTED": CANARY_SECRET})
    msg = render_message(summary(coverage_line=f"Coverage: 80% ({CANARY_SECRET})"),
                         scrub=red.scrub)
    assert CANARY_SECRET not in msg.body and CANARY_SECRET not in msg.subject
    assert "[REDACTED" in msg.body


def test_summary_has_no_slot_for_page_content_or_attachments() -> None:
    for extra in ({"page_content": CANARY_PAGE}, {"attachment": "x.png"}, {"screenshot": "a"}):
        with pytest.raises(ValidationError):
            ReportSummary(**{**summary().model_dump(), **extra})
    assert CANARY_PAGE not in render_message(summary()).body


@pytest.mark.parametrize("field,value", [
    ("project_name", "Shop\r\nBcc: evil@x.test"), ("project_name", "C:\\Users\\umesh\\secret"),
    ("coverage_line", "see /home/umesh/.env"), ("coverage_line", "line\nbreak"),
    ("report_url", "https://x.test/runs/1?token=abc"), ("report_url", "https://x.test/r#frag"),
    ("report_url", "https://user:pw@x.test/r"), ("report_url", "javascript:alert(1)"),
    ("report_url", "ftp://x.test/r"), ("report_url", "https://x.test/r\r\nBcc: e@x.test"),
    ("run_id", "../../etc"), ("run_id", "a/b")])
def test_summary_fields_refuse_injection_paths_tokens_and_odd_links(field: str,
                                                                    value: str) -> None:
    with pytest.raises(ValidationError):
        summary(**{field: value})


def test_report_url_may_be_a_signed_in_site_relative_path() -> None:
    assert render_message(summary(report_url="/runs/run-0001")).body.count("/runs/run-0001") == 1


def test_naive_timestamps_are_refused() -> None:
    with pytest.raises(ValidationError):
        summary(finished_at=NOW.replace(tzinfo=None))


def test_label_is_a_closed_stored_vocabulary_the_message_only_reads() -> None:
    assert {m.value for m in ReportLabel} == {"green", "failed", "blocked", "inconclusive",
                                              "low coverage"}
    with pytest.raises(ValidationError):
        summary(label="great")
    all_blocked = summary(counts=RunCounts(passed=0, failed=0, blocked=9, inconclusive=0),
                          label=ReportLabel.BLOCKED)
    assert "green" not in render_message(all_blocked).subject


def test_outbox_writes_one_dry_run_file_and_sends_nothing(tmp_path: Path) -> None:
    box = OutboxAdapter(tmp_path / "outbox")
    assert box.outcome is DeliveryStatus.OUTBOXED
    box.send(recipient(), render_message(summary()), key="run-0001__email__user-a")
    files = list((tmp_path / "outbox").iterdir())
    assert [f.name for f in files] == ["run-0001__email__user-a.eml"]
    text = files[0].read_text("utf-8")
    assert "To: dev.a@example.test" in text and "run-0001" in text


def test_outbox_is_idempotent_per_key_and_never_overwrites(tmp_path: Path) -> None:
    box = OutboxAdapter(tmp_path)
    box.send(recipient(), render_message(summary()), key="k1")
    first = (tmp_path / "k1.eml").read_bytes()
    box.send(recipient(address="other@example.test"), render_message(summary()), key="k1")
    assert (tmp_path / "k1.eml").read_bytes() == first and len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("key", ["../escape", "a/b", "a\\b", "", "..", "k\r\nx", "x" * 300])
def test_outbox_refuses_a_key_that_could_leave_its_directory(tmp_path: Path, key: str) -> None:
    with pytest.raises(TransportError):
        OutboxAdapter(tmp_path / "box").send(recipient(), render_message(summary()), key=key)
    assert not list(tmp_path.rglob("*.eml"))


def test_default_selection_without_credentials_is_the_outbox_and_sends_nothing(
        tmp_path: Path) -> None:
    assert isinstance(select_transport({}, tmp_path), OutboxAdapter)


def test_notification_preference_defaults_off_and_is_a_strict_model() -> None:
    assert NotificationPref(user_id="user-a").email_run_reports is False
    with pytest.raises(ValidationError):
        NotificationPref(user_id="user-a", email="attacker@x.test")  # type: ignore[call-arg]


def test_a_report_is_mailed_only_when_ticked_and_still_allowed_to_view_it() -> None:
    on, off = NotificationPref(user_id="u", email_run_reports=True), NotificationPref(user_id="u")
    assert may_email(on, can_view_report=True) is True
    assert may_email(off, can_view_report=True) is False       # box off (the default)
    assert may_email(on, can_view_report=False) is False       # report.view revoked before send
    assert may_email(None, can_view_report=True) is False      # never set a preference
