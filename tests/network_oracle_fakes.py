"""Test doubles for the network oracles (T-214): scripted responses through the real capture path.

`log_for` turns `(method, url, status, t_s)` tuples into a `StepNetworkLog` by calling the shipped
`capture_samples` (so first-party filtering and redaction are the real ones). `FakeNetworkPort`
plays the role-session port plus the optional network-log seam. No browser, no network, no product
code (MPI2: every shape is synthetic).
"""

from __future__ import annotations

from autotester.core.redact import Redactor
from autotester.schema.crawl import SafetyPolicy
from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.project import Project
from autotester.schema.request_budget import RequestBudget, StepNetworkLog
from autotester.schema.role_step import RoleStep
from autotester.stages.oracle_request_budget import capture_samples

SECRET = "tok-s3cret-value"
PROJECT = Project(slug="demo", name="Demo", base_url="https://app.test/",
                  allowed_domains=["app.test"])
POLICY = SafetyPolicy()
REDACTOR = Redactor({"DEMO_TOKEN": SECRET})
Response = tuple[str, str, int, float]


def log_for(responses: list[Response], *, step_id: str = "submit", role_id: str = "teacher",
            platform_id: str = "parent", screen_url: str = "https://app.test/orders",
            success: str | None = None, steps: list[str] | None = None) -> StepNetworkLog:
    return StepNetworkLog(
        step_id=step_id, role_id=role_id, platform_id=platform_id, screen_url=screen_url,
        repro_steps=steps or ["login portal", "click #submit"], success_indicator=success,
        samples=capture_samples(responses, PROJECT, POLICY, REDACTOR))


class FakeNetworkPort:
    """A role-session port that also exposes what the browser's network capture saw."""

    def __init__(self, logs: list[StepNetworkLog], budget: RequestBudget | None = None) -> None:
        self._logs = logs
        self._budget = budget

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        return Observation(matched=False)

    def network_log(self) -> list[StepNetworkLog]:
        return self._logs

    def request_budget(self) -> RequestBudget | None:
        return self._budget


class PlainPort:
    """A port without the network seam: the oracles must say so, not return an empty list."""

    def perform(self, step: RoleStep) -> None:
        return None

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        return Observation(matched=False)
