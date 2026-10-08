"""Persist team records atomically and claim slots exclusively beneath the team data root."""

import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from autotester.core.paths import team_component, team_path
from autotester.store.filestore import read_json, write_json

ModelT = TypeVar("ModelT", bound=BaseModel)


class TeamStore:
    """A portable sibling of ProjectStore for later schedule and delivery records."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root

    def save(self, namespace: str, project: str, record_id: str, model: BaseModel) -> None:
        write_json(team_path(namespace, project, record_id + ".json", root=self.root), model)

    def load(self, namespace: str, project: str, record_id: str,
             model_cls: type[ModelT]) -> ModelT | None:
        return read_json(team_path(namespace, project, record_id + ".json", root=self.root),
                         model_cls)

    def claim_slot(self, project: str, slot_key: str) -> bool:
        """Only one competing tick owns this slot; an existing claim is never overwritten."""
        encoded = team_component(slot_key, slot=True)
        path = team_path("slots", project, encoded, root=self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return False
        os.close(fd)
        return True
