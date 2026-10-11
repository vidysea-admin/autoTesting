"""The checks that stop an acting tool, in code (AL3). One job: decide, before any browser
exists, whether a model-requested action may start.

Nothing here is a prompt. Each function either returns/raises from an EXISTING guard
(`core.consent.require_approval`, `explore_safety.deny_reason`, `SecretStore.guard_prompt`) or,
for the one gap -- `execute.run_case` has no write-policy check of its own -- applies
`deny_reason` to the case's steps. A model instruction cannot reach any of this.
"""

from __future__ import annotations

from autotester.browser.secrets import SecretStore
from autotester.core.consent import require_approval
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef
from autotester.stages import explore_safety
from autotester.store.project_store import ProjectStore

_DATA_ACTIONS = frozenset({Action.FILL, Action.SELECT, Action.UPLOAD})


def guard_model_bound(secrets: SecretStore, text: str) -> str:
    """Raise `ValueError` if `text` carries a raw credential (folded/encoded too)."""
    return secrets.guard_prompt(text)


def crawl_approval(store: ProjectStore, project: Project, bounds: CrawlBounds) -> RunApproval:
    """The signed, unexpired human approval covering exactly these bounds, or `ApprovalRequired`.
    Reads existing rows only: an agent can never mint one (D-018)."""
    return require_approval(
        store.list_approvals(), project=project.slug, kind=ApprovalKind.CRAWL,
        target=project.base_url, actions=bounds.max_actions, wall_clock_s=bounds.wall_clock_s)


def live_case_approval(store: ProjectStore, project: Project, case: Case) -> RunApproval:
    """The approval for running this case against the live target, or `ApprovalRequired`."""
    return require_approval(
        store.list_approvals(), project=project.slug, kind=ApprovalKind.LIVE_CASE,
        target=project.base_url, actions=len(case.steps))


def _is_login_value(value: str | None) -> bool:
    """A step that only types `{{SECRET:KEY}}` placeholders is a credential entry, not a write."""
    return value is None or PLACEHOLDER_RE.sub("", value).strip() == ""


def _step_refusal(step: Step, project: Project) -> str | None:
    if step.action in _DATA_ACTIONS:
        if project.write_policy is WritePolicy.READ_ONLY and not _is_login_value(step.value):
            return f"{step.action.value} with a literal value"
        return None
    if step.action is Action.CLICK:
        element = ElementRef(role="button", name=step.target, selector=step.target)
        return explore_safety.deny_reason(element, explore_safety.policy_for(project))
    return None


def write_policy_refusal(case: Case, project: Project) -> str | None:
    """Why this case may not run under the project's `write_policy`, or None. Clicks go through
    the crawler's own `deny_reason` (never-click and destructive names at every policy but
    ALLOW_WRITES); under READ_ONLY a step that types a literal value is refused too."""
    for step in sorted(case.steps, key=lambda s: s.order):
        why = _step_refusal(step, project)
        if why is not None:
            return (f"refused under write_policy {project.write_policy.value}: "
                    f"step {step.order} ({step.action.value} {step.target!r}): {why}")
    return None
