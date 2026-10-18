"""Test doubles for the credential-policy and payment oracles (T-217): two scripted apps.

`PolicyApp` is a password form whose enforcement is chosen per rule; it checks each rule with its
OWN predicates (not the oracle's), so a wrong probe value shows up as a wrong verdict. `GatewayApp`
is a checkout -> hosted-gateway flow whose gateway submit endpoint counts its calls, so "stops at
the gateway" is a number, not a claim. Both implement the `RoleSessionPort` protocol; neither
touches a browser, a network or a provider (MPI2: all values are synthetic).
"""

from __future__ import annotations

import re

from autotester.schema.credential_policy import PasswordRule, PasswordRules
from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.multi_role_finding import ReproVerb, parse_repro_step
from autotester.schema.role_step import RoleStep

PREVIOUS_KEY = "QA_PREVIOUS_PASSWORD"
PREVIOUS_VALUE = "Old#Synthetic-Pass-0000"
_SECRET = re.compile(r"\{\{SECRET:([A-Z][A-Z0-9_]*)\}\}")


def meets(rule: PasswordRule, rules: PasswordRules, value: str, previous: str) -> bool:
    """The app's own check for one rule; independent of the oracle's value builder."""
    checks = {
        PasswordRule.MIN_LENGTH: lambda: len(value) >= (rules.min_length or 0),
        PasswordRule.REQUIRE_UPPER: lambda: any(c.isupper() for c in value),
        PasswordRule.REQUIRE_LOWER: lambda: any(c.islower() for c in value),
        PasswordRule.REQUIRE_DIGIT: lambda: any(c.isdigit() for c in value),
        PasswordRule.REQUIRE_SYMBOL: lambda: any(not c.isalnum() for c in value),
        PasswordRule.NO_REUSE: lambda: value != previous,
    }
    return checks[rule]()


class PolicyApp:
    """A create/reset form. `enforced` is the set of rules the product really checks."""

    def __init__(self, rules: PasswordRules, enforced: set[PasswordRule], *,
                 observe_error: bool = False, fail_on: str | None = None) -> None:
        self.rules, self.enforced = rules, enforced
        self.observe_error, self.fail_on = observe_error, fail_on
        self.typed: list[str] = []
        self.performed: list[str] = []
        self.accepted = False
        self._value = ""

    def perform(self, step: RoleStep) -> None:
        self.performed.append(step.action)
        if self.fail_on and self.fail_on in step.action:
            raise ConnectionError("form unreachable, and this message must not be copied")
        verb, target = parse_repro_step(step.action)
        if verb is ReproVerb.GOTO:
            self.accepted, self._value = False, ""
        elif verb is ReproVerb.FILL:
            raw = target.partition(" = ")[2]
            self._value = _SECRET.sub(PREVIOUS_VALUE, raw)
            self.typed.append(self._value)
        elif target == "#save":
            self.accepted = all(meets(r, self.rules, self._value, PREVIOUS_VALUE)
                                for r in self.enforced)
        elif target == "#restore":
            self.accepted = False

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        if self.observe_error:
            raise ConnectionError("page lost")
        return Observation(matched=self.accepted and assertion.target == "#done", detail="")


class GatewayApp:
    """pricing -> checkout -> hosted gateway; `submit_calls` counts the charge endpoint's calls."""

    def __init__(self, *, checkout_leads_to: str = "gateway", coupon_works: bool = True,
                 observe_error: bool = False, fail_on: str | None = None) -> None:
        self.page = "start"
        self.checkout_leads_to = checkout_leads_to
        self.coupon_works = coupon_works
        self.observe_error, self.fail_on = observe_error, fail_on
        self.discounted = False
        self.submit_calls = 0
        self.performed: list[str] = []

    def perform(self, step: RoleStep) -> None:
        self.performed.append(step.action)
        if self.fail_on and self.fail_on in step.action:
            raise TimeoutError("boom with detail that must not be copied")
        target = parse_repro_step(step.action)[1]
        if target.startswith("/pricing"):
            self.page = "pricing"
        elif target == "#choose-plan":
            self.page = "checkout"
        elif target == "#apply-coupon":
            self.discounted = self.coupon_works
        elif target == "#checkout":
            self.page = self.checkout_leads_to
        elif target == "#pay-now" and self.page == "gateway":
            self.submit_calls += 1          # the real charge would happen here

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        if self.observe_error:
            raise ConnectionError("page lost")
        if assertion.target == "#gateway-form":
            return Observation(matched=self.page == "gateway", detail="")
        if assertion.target == "#discount":
            return Observation(matched=self.discounted, detail="")
        return Observation(matched=False, detail="")
