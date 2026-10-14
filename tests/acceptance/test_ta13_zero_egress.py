"""TA13 (CRITICAL): zero egress, and the spend is exactly what the scenario implies. Over a press, a
tick, an intake (zip and Drive) and a review: no non-loopback connect, no smtplib connection, the
mail transport is the outbox adapter, the Drive client is the fake class, and the provider is
called only by the review."""

from __future__ import annotations

import urllib.request

import pytest
from drive_fakes import FakeDrive
from review_support import grant_review, make_zip, review, upload, upload_video
from rig import World, press
from schedule_support import SLOT, schedule
from video_review_fakes import RecordingProvider

from autotester.delivery.email import OutboxAdapter, select_transport
from autotester.stages.schedule_wiring import tick_all
from autotester.ui import routes_intake
from autotester.ui.run_queue import get_queue


def test_nothing_leaves_loopback_and_only_the_review_spends(world: World) -> None:
    schedule(world)
    press(world, "dev")
    assert world.counters.graded == 1 and world.provider.calls == 0     # a run: grader only
    tick_all(SLOT, root=world.root, queue=get_queue())
    assert world.counters.graded == 2 and world.provider.calls == 0
    upload(world, "dev", "clips.zip", make_zip())
    assert world.provider.calls == 0                                    # intake spends nothing
    source = upload_video(world, "dev", "walk")
    grant_review(world)
    result = review(world, source, "1:00 | total")
    assert world.provider.calls == result.calls > 0                     # exactly what it reports
    assert world.egress.blocked == []
    assert set(world.egress.attempts) <= {"127.0.0.1", "::1", "localhost"}
    assert world.smtp_attempts == []


def test_the_seams_are_the_fake_classes(world: World) -> None:
    assert isinstance(world.provider, RecordingProvider)
    assert isinstance(world.drive, FakeDrive)
    assert routes_intake.drive_factory(world.store()) is world.drive
    assert isinstance(select_transport({}, world.outbox), OutboxAdapter)    # no SES values set


def test_a_non_loopback_attempt_on_the_delivery_path_would_be_caught(world: World) -> None:
    """Sabotage: the same guard that stays empty above records the attempt and the host."""
    with pytest.raises(OSError):
        urllib.request.urlopen("http://203.0.113.9/", timeout=3)
    assert world.egress.blocked == ["203.0.113.9"]
