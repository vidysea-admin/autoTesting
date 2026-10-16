"""The pre-run gates: refusal type, credential check and the D-018 live-case approval.

One job: the checks `prepare_run` applies before a run id, directory or browser exists
(split out of `run_launcher` to keep it under the file limit). `LaunchRefused` carries the HTTP
status a route shows; `run_launcher` re-exports every name here, so callers are unchanged.
"""

from __future__ import annotations

from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired
from autotester.core.redact import placeholder_keys
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind
from autotester.schema.project import Project
from autotester.stages.entry_precondition import requires_unauthenticated
from autotester.stages.execute import probe_request
from autotester.stages.explore_consent import covering_approval
from autotester.stages.run_budget import action_cost, wall_clock_request_s
from autotester.store.project_store import ProjectStore

__all__ = ["LaunchRefused", "is_entry_case", "require_declared_values",
           "require_live_case_approval"]


class LaunchRefused(Exception):
    """A gate said no. `status` is the HTTP code a route shows; `reason` the human sentence."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(reason)
        self.status, self.reason = status, reason


def is_entry_case(case: Case, project: Project) -> bool:
    """True when the case must start logged out: its first step navigates to the project's own
    `base_url` (a sign-in page, AT-044), or its precondition is a logged-out visitor
    (`deeplink_unauth`): the shared signed-in profile would hide it, so it gets a wiped one."""
    return (bool(case.steps) and case.steps[0].action is Action.NAVIGATE
            and case.steps[0].target == project.base_url) or requires_unauthenticated(case)


def require_declared_values(
    project: Project, secrets: SecretStore, slug: str, cases: list[Case] | None = None,
) -> set[str]:
    """Check referenced credentials before launch; unused roles never gate a run."""
    keys = ({ref.key for ref in project.secrets} if cases is None else {
        key for case in cases for step in case.steps
        for text in (step.target, step.value or "") for key in placeholder_keys(text)
    })
    missing = sorted(key for key in keys if not secrets.has_value(key))
    if missing:
        raise LaunchRefused(400, (
            f"{', '.join(missing)} has no value yet. Enter it on the project's "
            f"Credentials page (/projects/{slug}/env) before running."
            if len(missing) == 1 else
            f"these credentials have no value yet: {', '.join(missing)}. Enter them on the "
            f"project's Credentials page (/projects/{slug}/env) before running."
        ))
    return keys


def require_live_case_approval(
    project: Project, store: ProjectStore, cases: list[Case],
    secrets: SecretStore | None = None, account_keys: set[str] | None = None,
) -> RunApproval:
    """Pre-run D-018/CN11 gate (D-068): a covering human grant, else one derived from the
    project's provisioned credentials -- reused if an earlier row covers the run, else minted.

    Refuse before run-id/directory/browser creation, naming human-grant shortfalls.
    System-derived action/probe/time brakes bound, never expand, account consent.
    """
    bounds = CrawlBounds(max_actions=sum(action_cost(c) for c in cases),
                         wall_clock_s=wall_clock_request_s(cases))
    try:
        if any(case.project != project.slug for case in cases):
            raise ApprovalRequired("case project differs from the requested project")
        return covering_approval(
            project, store, bounds, kind=ApprovalKind.LIVE_CASE, secrets=secrets,
            account_keys=account_keys or None, probes=probe_request(cases))
    except ApprovalRequired as exc:
        raise LaunchRefused(403, str(exc)) from exc
