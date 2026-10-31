"""mongo-store U7 (M20, M53): a purge killed between a document move's put and delete.

On a document backend `rename_path` is put(dst) then delete(src), so a kill between the two
leaves both copies. Recovery has to finish that move; stranding the stage lets a later
recovery put a stale copy back over a file that a newer purge deleted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_coordination_u7 import _seed_purge
from test_coordination_u7 import root as _backend_root

import autotester.stages.schedule_store as schedule_store
import autotester.store.filestore as filestore
from autotester.stages.schedule_store import (
    list_claims,
    purge_project,
    read_records,
    recover_stale_purges,
)
from autotester.store.filestore import write_text
from autotester.store.filestore_paths import read_text_path

root = _backend_root  # the per-backend data-root fixture, shared with its sibling file


@pytest.mark.parametrize("dies_at", [0, 1, 2])
def test_a_kill_between_a_moves_put_and_delete_never_resurrects_a_purged_file(
        root: Path, monkeypatch: pytest.MonkeyPatch, dies_at: int) -> None:
    """On a document backend a move is put(dst) then delete(src): a kill between the two leaves
    both copies. Recovery must finish that move, not strand the stage for a later recovery to
    put the stale copy back over a file that a newer purge deleted."""
    claims, records = _seed_purge(root)
    real, calls = schedule_store.rename_path, []

    def put_then_die(src: Path, dst: Path) -> None:
        calls.append(src)
        if len(calls) - 1 != dies_at:
            real(src, dst)
            return
        write_text(dst, read_text_path(src) or "")  # the put landed; the delete never will
        raise KeyboardInterrupt

    with monkeypatch.context() as patched:
        patched.setattr(schedule_store, "rename_path", put_then_die)
        patched.setattr(schedule_store, "_restore_stage", lambda stage: False)  # a hard kill
        with pytest.raises(KeyboardInterrupt):
            purge_project(claims, records, "p")
    assert [n for n in filestore.list_children(claims.parent) if n.startswith(".purge")]
    purge_project(claims, records, "p")  # the retry adopts the stage, then purges for real
    assert list_claims(claims) == {} and read_records(records) == []
    assert [n for n in filestore.list_children(claims.parent) if n.startswith(".purge")] == []
    assert recover_stale_purges(claims, records, "p") == 0
    assert list_claims(claims) == {} and read_records(records) == []
