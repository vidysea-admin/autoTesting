"""The checks that stop an acting tool, in code (AL3). One job: decide, before any browser
exists, whether a model-requested action may start.

Nothing here is a prompt. Each function either returns/raises from an EXISTING guard
(`core.consent.require_approval`, `explore_safety.deny_reason`, `SecretStore.guard_prompt`) or,
for the one gap -- `execute.run_case` and the browser session have no write-policy check, and a
stored `Step` carries no DOM facts (no `is_form_submit`) -- decides from what the step says.

Under READ_ONLY that decision is fail-closed (table: the T-179a manifest): only step kinds that
cannot change state by construction run (reads, waits, assertions, hover, scroll, back, and a
GET navigation to an in-domain http(s) URL), plus the declared login case's credential entry.
`deny_reason` stays the one name deny-function. A model instruction cannot reach any of this.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from autotester.browser.secrets import SecretStore
from autotester.browser.session import NavigationRefused, check_destination
from autotester.core.consent import require_approval
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.agent_layer import RefusalClass
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef
from autotester.stages import explore_safety
from autotester.store.project_store import ProjectStore

_READS = frozenset({Action.WAIT, Action.ASSERT, Action.BACK, Action.HOVER, Action.SCROLL})
_WEB = ("http", "https")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
DESTINATION_REFUSED = "destination is not an http(s) URL inside the allowed domains"


@dataclass
class _Walk:
    """Where we are in one case: is it the declared login, and was a credential just typed."""

    login: bool
    credential_pending: bool = False


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


def _declared_credential(value: str | None, project: Project) -> bool:
    """Only `{{SECRET:KEY}}` placeholders of keys the project declares, and nothing else; at
    least one (a blank value is not a credential entry)."""
    keys = PLACEHOLDER_RE.findall(value or "")
    if not keys or PLACEHOLDER_RE.sub("", value or "").strip() != "":
        return False
    declared = {ref.key for ref in project.secrets}
    return all(key in declared for key in keys)


def _click_denied(name: str, project: Project) -> str | None:
    """The crawler's own name deny-function, asked about a name (the one deny concept)."""
    element = ElementRef(role="button", name=name, selector=name)
    return explore_safety.deny_reason(element, explore_safety.policy_for(project))


def _check_refuses(target: str, project: Project) -> bool:
    """The browser seam's own destination check (`check_destination`), asked of `target`."""
    try:
        check_destination(project, target)
    except NavigationRefused:
        return True
    return False


def _seam_refuses(target: str, project: Project) -> bool:
    """Would `BrowserSession.goto(target)` refuse it? A placeholder target is not judged: the
    seam resolves it first, and this guard resolves nothing earlier than the seam does."""
    return not PLACEHOLDER_RE.search(target) and _check_refuses(target, project)


def _destination(target: str, project: Project) -> tuple[str | None, str]:
    """READ_ONLY only: (why not, the cleaned target). Stricter than the seam on the raw target:
    control characters and non-http(s) schemes are refused, and an absolute or protocol-relative
    URL must pass the seam's own check (`check_destination`) as written, placeholders included."""
    if _CONTROL.search(target):
        return DESTINATION_REFUSED, target
    cleaned = target.strip()
    try:
        parts = urlsplit(cleaned)
    except ValueError:
        return DESTINATION_REFUSED, cleaned
    if parts.scheme and parts.scheme not in _WEB:
        return DESTINATION_REFUSED, cleaned
    if (parts.scheme or cleaned.startswith("//")) and _check_refuses(cleaned, project):
        return DESTINATION_REFUSED, cleaned
    return None, cleaned


def _navigate_refusal(step: Step, project: Project, walk: _Walk) -> tuple[str | None, bool]:
    """(reason, is_destination). Above READ_ONLY the guard is exactly the seam's check (never
    stricter: a placeholder target is left to the seam). READ_ONLY allows only a
    placeholder-free absolute http(s) GET with no query (the declared login may carry one)
    whose path and fragment pass `deny_reason`."""
    if project.write_policy is not WritePolicy.READ_ONLY:
        refused = _seam_refuses(step.target, project)
        return (DESTINATION_REFUSED, True) if refused else (None, False)
    why, url = _destination(step.target, project)
    if why is not None:
        return why, True
    parts = urlsplit(url)
    if not parts.scheme or PLACEHOLDER_RE.search(url):
        return "navigate needs an absolute http(s) URL without placeholders", False
    if parts.query and not walk.login:
        return "navigate with a query string can change state", False
    return _click_denied(unquote(f"{parts.path} {parts.fragment}"), project), False


def _read_only_refusal(step: Step, project: Project, walk: _Walk) -> str | None:
    """Fail closed: what is not listed as safe, or as the login's credential entry, is refused."""
    action = step.action
    if action in _READS:
        return None
    if action is Action.FILL and walk.login and _declared_credential(step.value, project):
        walk.credential_pending = True
        return None
    enter = action is Action.PRESS_KEY and step.value in (None, "Enter")
    if (action is Action.CLICK or enter) and walk.login and walk.credential_pending:
        walk.credential_pending = False  # one submit per credential entry
        return _click_denied(step.target, project) if action is Action.CLICK else None
    if action is Action.FILL:
        return "fill outside the declared login's credential entry"
    return f"{action.value} can change state"


def _step_refusal(step: Step, project: Project, walk: _Walk) -> tuple[str | None, RefusalClass]:
    if step.action is Action.NAVIGATE:
        why, is_destination = _navigate_refusal(step, project, walk)
        return why, RefusalClass.DESTINATION if is_destination else RefusalClass.WRITE_POLICY
    if project.write_policy is WritePolicy.READ_ONLY:
        return _read_only_refusal(step, project, walk), RefusalClass.WRITE_POLICY
    if step.action is Action.CLICK:
        return _click_denied(step.target, project), RefusalClass.WRITE_POLICY
    return None, RefusalClass.WRITE_POLICY


def write_policy_refusal(case: Case, project: Project) -> tuple[RefusalClass, str] | None:
    """(refusal class, why) if this case may not run under the project's `write_policy`, else
    None. A NAVIGATE outside the allowed http(s) domains is refused at every policy; above
    READ_ONLY nothing is added to the click deny-list the crawler already applies."""
    walk = _Walk(login=project.login_case_id is not None and case.id == project.login_case_id)
    for step in sorted(case.steps, key=lambda s: s.order):
        why, kind = _step_refusal(step, project, walk)
        if why is None:
            continue
        where = f"step {step.order} ({step.action.value})"
        if kind is RefusalClass.DESTINATION:
            return kind, f"refused: {where}: {why}"
        return kind, (f"refused under write_policy {project.write_policy.value}: "
                      f"{where} {step.target!r}: {why}")
    return None
