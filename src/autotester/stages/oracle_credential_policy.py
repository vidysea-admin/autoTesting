"""The credential-policy oracle: weak passwords accepted, and credentials sent in plain mail (MP27).

One job: probe each declared create or reset form with one synthetic password per declared rule,
each breaking exactly that rule, and report every rule the product accepted a breach of; and read
the mailbox assertions the scenario already decided, reporting a mail that carried credential-shaped
tokens it was not declared to carry. Interface: `run(context)` (`schema/oracle_context.py`, "HOW TO
WRITE AN ORACLE"). The declaration is `context.declarations.credential_policy`, else
`<run_dir>/credential_policy.json` (`schema/credential_policy.py`); with neither the oracle raises
`PolicyNotDeclaredError`, so the registry shows `errored` rather than a clean `ran`.

Rules this module holds:
  * A finding names the RULE, never a value. The probe value lives only in the step handed to the
    port; the finding's repro says `[probe:<rule>]`. A reuse probe sends the `{{SECRET:KEY}}`
    placeholder of the previous password, so this module never holds that value either.
  * An accepted weak password on a reset form changed the account, so the declared `restore_steps`
    run right after it; a restore that failed is said in the finding's title.
  * Nothing that could not be looked at counts as clean (SA9): an unreachable form is tried once,
    and with no finding to return, a form left only partly probed (or nothing decided at all)
    raises `CredentialProbeError`, so the registry shows `errored`. Findings that were proven are
    never dropped for an unprobed sibling.
  * The mail half reads the mailbox oracle's own observation wording
    (`stages/oracle_mailbox.py::observation_from_read`, "N credential-shaped token(s) present"); a
    test pins that coupling. Tokens are counted over the whole read window, not one subject, so the
    check over-flags rather than under-flags.
"""

from __future__ import annotations

import re
from pathlib import Path

from autotester.schema.credential_policy import (
    POLICY_FILE,
    CredentialPolicy,
    MailRule,
    PasswordRule,
    PasswordRules,
    PolicyFlow,
)
from autotester.schema.cross_role_assertion import (
    AssertionOutcome,
    AssertVerdict,
    CrossRoleAssertion,
)
from autotester.schema.multi_role_enums import AssertChannel, Expectation, FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext, RoleSessionPort
from autotester.schema.platform import IMPLICIT_PLATFORM_ID
from autotester.schema.role_step import RoleStep

_FALLBACK_STEP = "goto /"
_TOKENS = re.compile(r"(\d+) credential-shaped token")
_CLASS_CHARS = {PasswordRule.REQUIRE_LOWER: "xkmq", PasswordRule.REQUIRE_UPPER: "XKMQ",
                PasswordRule.REQUIRE_DIGIT: "4719", PasswordRule.REQUIRE_SYMBOL: "#!%+"}
_BASE_LENGTH = 12


class PolicyNotDeclaredError(RuntimeError):
    """No usable `credential_policy.json`; the message is a closed phrase, never file text."""


class CredentialProbeError(RuntimeError):
    """Nothing was proven either way; the message is a closed phrase, never a page or value."""


def load_policy(run_dir: str) -> CredentialPolicy:
    """The declaration in `run_dir`, or `PolicyNotDeclaredError` (without the file's content)."""
    try:
        text = (Path(run_dir) / POLICY_FILE).read_text(encoding="utf-8")
    except OSError:
        raise PolicyNotDeclaredError("no credential policy declared") from None
    try:
        return CredentialPolicy.model_validate_json(text)
    except ValueError:
        raise PolicyNotDeclaredError("credential policy declaration is invalid") from None


def probe_value(rules: PasswordRules, rule: PasswordRule) -> str:
    """A synthetic password that meets every declared rule except `rule`.

    A reuse probe is the placeholder of the previous password's key, not a value."""
    if rule is PasswordRule.NO_REUSE:
        return "{{SECRET:" + str(rules.previous_password_key) + "}}"
    alphabets = [chars for r, chars in _CLASS_CHARS.items() if r is not rule]
    if rule is PasswordRule.MIN_LENGTH:
        length = (rules.min_length or 1) - 1
    else:
        length = max(rules.min_length or 0, _BASE_LENGTH)
    n = len(alphabets)
    return "".join(alphabets[i % n][(i // n) % len(alphabets[i % n])] for i in range(length))


def _role_steps(flow: PolicyFlow, actions: list[str], tag: str) -> list[RoleStep]:
    return [RoleStep(id=f"{flow.id}-{tag}{i}", role_id=flow.role_id, action=a)
            for i, a in enumerate(actions)]


def _restore(flow: PolicyFlow, port: RoleSessionPort) -> bool:
    try:
        for step in _role_steps(flow, flow.restore_steps, "restore"):
            port.perform(step)
    except Exception:
        return False
    return True


def _probe(flow: PolicyFlow, rules: PasswordRules, rule: PasswordRule,
           port: RoleSessionPort) -> tuple[bool | None, bool]:
    """(accepted, restored): accepted is None when the form could not be probed or looked at."""
    actions = [*flow.open_steps, f"fill {flow.password_field} = {probe_value(rules, rule)}",
               flow.submit_step]
    look = CrossRoleAssertion(
        id=f"{flow.id}-look"[:64], observer_role_id=flow.role_id, channel=AssertChannel.UI,
        expectation=Expectation.PRESENT, target=flow.accepted_marker, within_s=flow.within_s)
    try:
        for step in _role_steps(flow, actions, "probe"):
            port.perform(step)
        accepted = port.observe(look).matched
    except Exception:
        return None, True            # exception text is dropped: it may echo the typed value
    return accepted, (_restore(flow, port) if accepted else True)


def _platform(flow_platform: str | None, context: OracleContext) -> str:
    return flow_platform or (context.platform_ids[0] if context.platform_ids
                             else IMPLICIT_PLATFORM_ID)


def _flow_finding(flow: PolicyFlow, rule: PasswordRule, restored: bool,
                  context: OracleContext) -> MultiRoleFinding:
    title = f"Weak password accepted on the {flow.kind.value} form: rule {rule.value} not enforced"
    return MultiRoleFinding(
        finding_id=f"cred-{flow.id}-{rule.value}",
        finding_class=FindingClass.WEAK_CREDENTIAL_POLICY,
        title=title + ("" if restored else " (account not restored)"), role=flow.role_id,
        platform_id=_platform(flow.platform_id, context), url_template=flow.page,
        steps=[*flow.open_steps, f"fill {flow.password_field} = [probe:{rule.value}]",
               flow.submit_step], count=1)


def _probe_flow(flow: PolicyFlow, policy: CredentialPolicy, context: OracleContext,
                ) -> tuple[list[MultiRoleFinding], int]:
    """Findings for one form and how many probes were actually decided."""
    if context.port is None:
        raise CredentialProbeError("no session port to probe through")
    findings: list[MultiRoleFinding] = []
    decided = 0
    for rule in policy.rules.declared():
        accepted, restored = _probe(flow, policy.rules, rule, context.port)
        if accepted is None:
            break                       # the form is unreachable or unreadable: stop poking it
        decided += 1
        if accepted:
            findings.append(_flow_finding(flow, rule, restored, context))
    return findings, decided


def _token_count(outcome: AssertionOutcome) -> int | None:
    """Tokens the mailbox oracle saw, or None when this outcome proves nothing about the mail."""
    if not (outcome.channel is AssertChannel.MAILBOX and outcome.expectation is Expectation.PRESENT
            and outcome.verdict is AssertVerdict.PASSED and outcome.last_observation):
        return None
    found = _TOKENS.search(outcome.last_observation)
    return int(found.group(1)) if found else 0


def _mail_finding(outcome: AssertionOutcome, tokens: int,
                  context: OracleContext) -> MultiRoleFinding:
    return MultiRoleFinding(
        finding_id=f"cred-mail-{outcome.assertion_id}"[:64],
        finding_class=FindingClass.WEAK_CREDENTIAL_POLICY,
        title=f"A mail carries credential-shaped tokens in plain text: "
              f"rule {MailRule.CREDENTIAL_IN_PLAIN_MAIL.value}",
        role=outcome.observer_role_id, platform_id=_platform(None, context), url_template="/",
        steps=[s.action for s in context.steps][:50] or [_FALLBACK_STEP], count=tokens)


def _mail_findings(policy: CredentialPolicy, context: OracleContext,
                   ) -> tuple[list[MultiRoleFinding], int]:
    findings: list[MultiRoleFinding] = []
    decided = 0
    for outcome in context.assertion_outcomes:
        tokens = _token_count(outcome)
        if tokens is None:
            continue
        decided += 1
        if tokens and outcome.assertion_id not in policy.token_allowed_assertions:
            findings.append(_mail_finding(outcome, tokens, context))
    return findings, decided


def credential_findings(context: OracleContext,
                        policy: CredentialPolicy | None = None) -> list[MultiRoleFinding]:
    """All weak-credential findings; raises `CredentialProbeError` when nothing was decided."""
    policy = policy or context.declarations.credential_policy or load_policy(context.run_dir)
    findings: list[MultiRoleFinding] = []
    decided, incomplete = 0, False
    for flow in policy.flows:
        found, n = _probe_flow(flow, policy, context)
        findings += found
        decided += n
        incomplete = incomplete or n < len(policy.rules.declared())
    mail, n = _mail_findings(policy, context)
    if not findings + mail and (incomplete or decided + n == 0):
        raise CredentialProbeError("a declared probe or mail could not be decided")
    return findings + mail


run = credential_findings
"""The registry's entry point (`schema/oracle_context.py`). An alias, not a second `def run`: the
doctor's duplicate-concept rule flags a top-level `def run` because `doctor.py` already has one."""
