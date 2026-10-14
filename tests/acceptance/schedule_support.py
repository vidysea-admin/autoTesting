"""Shared by the TA8 and TA11 tests: put a daily 09:00 UTC schedule on a project and the three
instants (before the slot, in it) the injected clock uses. The schedule is written to the project
file because the save route is not on master (see test_ta08)."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from rig import SLUG, World

from autotester.schema.schedule import ScheduleConfig

SAVED = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
BEFORE = datetime(2026, 10, 13, 8, 59, 0, tzinfo=UTC)
SLOT = datetime(2026, 10, 13, 9, 0, 10, tzinfo=UTC)


def schedule(world: World, slug: str = SLUG) -> None:
    store = world.store(slug)
    project = store.load_project()
    assert project is not None
    project.schedule = ScheduleConfig.model_validate(
        {"mode": "fixed", "fixed_at": "09:00", "timezone": "UTC", "owner": "subadmin@team.test"})
    store.save_project(project)
    os.utime(store.paths.config, (SAVED.timestamp(), SAVED.timestamp()))
