"""The checks that stop an acting tool, in code (AL3). One job: decide, before any browser
exists, whether a model-requested action may start.

Nothing here is a prompt. Each function either returns/raises from an EXISTING guard
(`core.consent.require_project_approval`, `explore_safety.deny_reason`,
`SecretStore.guard_prompt`) or,
for the one gap -- `execute.run_case` and the browser session have no write-policy check, and a
stored `Step` carries no DOM facts (no `is_form_submit`) -- decides from what the step says.

Under READ_ONLY that decision is fail-closed (table: the T-179a manifest): only step kinds that
cannot change state by construction run (reads, waits, assertions, hover, scroll, back, a
click whose name passes the deny-list (D-086), and a GET navigation to an in-domain
http(s) URL), plus the declared login case's credential entry.
`deny_reason` stays the one name deny-function. A model instruction cannot reach any of this.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from autotester.browser.secrets import SecretStore
from autotester.browser.session import NavigationRefused, check_destination
from autotester.core.consent import require_project_approval
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
# D-086 (HG-1): READ_ONLY may click, but a step carries no DOM facts, so a control whose own name
# says it commits something (the crawler's `is_form_submit` is unknowable here) stays refused.
_COMMIT_NAME = re.compile(
    r"\b(save|place order|confirm|register|sign ?up|sign ?in|log ?in|add to cart|buy|purchase|"
    r"update|create|apply|book|upload|import)\b", re.IGNORECASE)
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
    return require_project_approval(
        store.list_approvals(), project=project, kind=ApprovalKind.CRAWL,
        target=project.base_url, actions=bounds.max_actions, wall_clock_s=bounds.wall_clock_s)


def live_case_approval(store: ProjectStore, project: Project, case: Case) -> RunApproval:
    """The approval for running this case against the live target, or `ApprovalRequired`."""
    return require_project_approval(
        store.list_approvals(), project=project, kind=ApprovalKind.LIVE_CASE,
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
    return explore_safety.deny_reason(element, explore_safety.policy_for(project))  # incl. destroy


# Cyrillic/Greek lookalikes of Latin letters, folded after NFKC (small, cheap; not a full table).
_CONFUSABLES = {  # code point -> Latin letter (Cyrillic a e o p c x y i s j d h, Greek o v i)
    cp: ch for cp, ch in zip(
        (0x430, 0x435, 0x43E, 0x440, 0x441, 0x445, 0x443, 0x456, 0x455, 0x458, 0x501, 0x4BB,
         0x3BF, 0x3BD, 0x3B9), "aeopcxyisjdhovi", strict=True)}
_CONFUSABLE_TABLE = str.maketrans(_CONFUSABLES)
_UNNAMED = "unnamed control"


def _click_names(name: str) -> tuple[str, ...]:
    """A click target as the person sees it, in two readings: NFKC, lookalikes folded, case folded,
    separators and whitespace collapsed (`normalise_label`), with invisible/format characters
    dropped (`De<ZWSP>lete`) and with them read as a space (`Save<ZWSP>draft`)."""
    text = unicodedata.normalize("NFKC", name)
    out = []
    for hidden in ("", " "):
        seen = "".join(hidden if unicodedata.category(ch) == "Cf" else (" " if ch.isspace() else ch)
                       for ch in text)
        out.append(explore_safety.normalise_label(seen.translate(_CONFUSABLE_TABLE).casefold()))
    return tuple(dict.fromkeys(out))


def _click_refusal(name: str, project: Project) -> str | None:
    """Deny-list, never-click and unnamed (blank after cleaning) checks for a click target."""
    names = _click_names(name)
    if not any(names):
        return _UNNAMED
    return next((why for n in names if (why := _click_denied(n, project))), None)


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
        return _click_refusal(step.target, project) if action is Action.CLICK else None
    if action is Action.CLICK:  # D-086 HG-1: benign clicks run; deny-list/never-click still hold
        return _click_refusal(step.target, project) or (
            "click on a control named like a commit can change state"
            if any(_COMMIT_NAME.search(n) for n in _click_names(step.target)) else None)
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
        return _click_refusal(step.target, project), RefusalClass.WRITE_POLICY
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
