"""Test double for the state-after oracle (T-220): a scripted multi-role app with named faults.

Each counter has a `mode` (how the action changes it) and, per role, a server value and a page
view. `goto` reloads a role's views from the server; an action edits server and/or view according
to the mode. Observation detail is the view's text. Synthetic shapes only (MPI2): no product code.
"""

from __future__ import annotations

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.role_step import RoleStep

ROLES = ("teacher", "parent")


class StatePort:
    """`counters` maps a reader target to its mode: correct, not_incremented, actor_only,
    reverted, double. Start value is `start`. `texts` overrides a view's text (status readers)."""

    def __init__(self, counters: dict[str, str], *, actor: str = "teacher", start: int = 3,
                 texts: dict[str, str] | None = None, unreadable: set[str] | None = None) -> None:
        self.modes = counters
        self.actor = actor
        self.server = {t: {r: start for r in ROLES} for t in counters}
        self.view = {t: {r: start for r in ROLES} for t in counters}
        self.texts = texts or {}
        self.unreadable = unreadable or set()
        self.performed: list[str] = []

    def perform(self, step: RoleStep) -> None:
        self.performed.append(f"{step.role_id}:{step.action}")
        if step.action.startswith("goto"):
            for target in self.modes:
                self.view[target][step.role_id] = self.server[target][step.role_id]
            return
        for target, mode in self.modes.items():
            self._apply(target, mode)

    def _apply(self, target: str, mode: str) -> None:
        srv, view, actor = self.server[target], self.view[target], self.actor
        if mode == "correct":
            for role in ROLES:
                srv[role] += 1
            view[actor] = srv[actor]
        elif mode == "double":
            for role in ROLES:
                srv[role] += 2
            view[actor] = srv[actor]
        elif mode == "actor_only":
            srv[actor] += 1
            view[actor] = srv[actor]
        elif mode == "reverted":
            view[actor] += 1

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        target = assertion.target
        if target in self.unreadable:
            return Observation(matched=False, detail="")
        if target in self.texts:
            return Observation(matched=True, detail=self.texts[target])
        return Observation(matched=True, detail=str(self.view[target][assertion.observer_role_id]))
