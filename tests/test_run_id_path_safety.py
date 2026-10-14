"""AT-900: a run id is a single safe path segment; nothing outside runs/ is ever created."""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester.core.paths import ProjectPaths
from autotester.core.safe_names import UnsafeName

BACKSLASH = chr(92)
BAD_IDS = ["../escaped", "..", "a/b", "a" + BACKSLASH + "b", "/abs",
           "C:" + BACKSLASH + "x", "", "x:y"]


@pytest.mark.parametrize("bad", BAD_IDS)
def test_run_dir_refuses_unsafe_ids(tmp_path: Path, bad: str) -> None:
    paths = ProjectPaths("demo", tmp_path)
    with pytest.raises(UnsafeName):
        paths.run_dir(bad)
    assert not (tmp_path / "escaped").exists()


def test_run_dir_accepts_minted_id(tmp_path: Path) -> None:
    paths = ProjectPaths("demo", tmp_path)
    assert paths.run_dir("rel_01ABC").parent == paths.runs_dir
