"""The network-log capability of the live role port: `NetworkLogPort` (MP21, MP22).

One job: turn the responses each role's page made into `StepNetworkLog`s and hand them, with the
declared `RequestBudget`, to the network oracles. Responses reach the log only through
`stages/oracle_request_budget.py::capture_samples`, which calls
`network_capture.first_party_evidence` (the one first-party filter and URL redactor), so a
third-party host is dropped and a secret in a URL is `[REDACTED]` before an oracle sees it.
Requests that arrive between steps are added to the role's previous step (that screen is where
they came from); requests before its first step are sign-in traffic and dropped. Nothing is
written to disk.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from autotester.browser.role_probe import PageSnapshot
from autotester.schema.crawl import SafetyPolicy
from autotester.schema.request_budget import (
    NetworkLogUnavailable,
    RequestBudget,
    StepNetworkLog,
)
from autotester.schema.role_step import RoleStep
from autotester.stages.oracle_request_budget import capture_samples
from autotester.stages.role_port_state import PortBase

BUDGET_FILE = "request_budget.json"


class NetworkMixin(PortBase):
    """`network_log()` and `request_budget()`; needs `_logs`, `_policy` and `_budget` set."""

    _logs: list[StepNetworkLog]
    _policy: SafetyPolicy
    _budget: RequestBudget | None

    def _record_step(self, step: RoleStep, snap: PageSnapshot) -> None:
        """One log entry for a step that just ran, with the responses it caused."""
        state, account = self._states[step.role_id], self.roles.account(step.role_id)
        samples = capture_samples(snap.responses, self.roles.project, self._policy, self._redactor)
        fields = {"step_id": step.id, "role_id": step.role_id, "platform_id": account.platform_id,
                  "screen_url": self._redactor.scrub(snap.url), "success_indicator": snap.success,
                  "samples": samples}
        try:
            log = StepNetworkLog(**fields, repro_steps=list(state.repro))
        except ValidationError:  # a repro step that looks personal: keep the step's own action
            try:
                log = StepNetworkLog(**fields, repro_steps=[step.action])
            except ValidationError:  # the action itself looks personal: replay nothing
                log = StepNetworkLog(**fields, repro_steps=[])
        self._logs.append(log)
        state.last_log = len(self._logs) - 1

    def _absorb(self, role_id: str) -> None:
        """Move responses seen since the role's last step onto that step's log."""
        state = self._states[role_id]
        rows = self.roles.run_as(role_id, lambda _s: state.log.take())
        if not rows or state.last_log is None:
            return
        old = self._logs[state.last_log]
        extra = capture_samples(rows, self.roles.project, self._policy, self._redactor)
        self._logs[state.last_log] = old.model_copy(update={"samples": [*old.samples, *extra]})

    def network_log(self) -> list[StepNetworkLog]:
        """Every step's first-party requests in the order the steps ran."""
        self._require_every_role()
        for role_id in self._states:
            self._absorb(role_id)
        if not self._logs:
            raise NetworkLogUnavailable("no step has run, so no request was captured")
        return list(self._logs)

    def request_budget(self) -> RequestBudget | None:
        return self._budget


def load_budget(run_dir: Path | str) -> RequestBudget | None:
    """The run's declared budget from `<run_dir>/request_budget.json`; None when absent."""
    path = Path(run_dir) / BUDGET_FILE
    if not path.is_file():
        return None
    return RequestBudget.model_validate_json(path.read_text(encoding="utf-8"))
