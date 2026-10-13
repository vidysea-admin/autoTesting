"""Fixtures for the T-206 acceptance tests: a cold world and a warm one on fresh temp roots."""

from __future__ import annotations

import pytest
from rig import World, add_team, build_world


@pytest.fixture
def cold(tmp_path, monkeypatch, serve_dir) -> World:
    return build_world(tmp_path, monkeypatch, serve_dir)


@pytest.fixture
def world(cold) -> World:
    return add_team(cold)
