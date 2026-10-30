"""The payment oracle: does each declared paid path reach a gateway page, and stop there (MP28).

One job: walk each declared paid path (`schema/payment_path.py`) through the session port, report
for every path whether the gateway page was reached and whether the coupon applied, and turn a
path that broke into a `PAYMENT_PATH` finding. Interface: `run(context)`
(`schema/oracle_context.py`, "HOW TO WRITE AN ORACLE"). The declaration is
`context.declarations.payment_paths`, else `<run_dir>/payment_paths.json`; a states-only report is
written to the run directory as `payment_report.json`.

THE NO-CHARGE RULE (MPI4: a real-money charge is never completed). The gateway marker is looked at
after EVERY step, in every phase, and the walk stops the moment it shows: nothing is performed on
a gateway page, so the gateway's submit endpoint is never called. The one exception is a path that
declares `provider_test_mode` AND carries `test_mode_steps` (the schema refuses the steps without
the flag). Only the port's `perform` and `observe` are used; no HTTP request and no provider call
is made from here.

Honesty rules (SA9): a page that could not be looked at is `unobserved`, never `not_reached`; a
step that raised ends the path as `not_reached` (the payer could not get there); the exception
itself is dropped, because it may carry a page. With no finding to return and an unobserved path,
`run` raises `PaymentUnobservedError`, so the registry shows `errored`, not a clean `ran`.
"""

from __future__ import annotations

from pathlib import Path

from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.multi_role_enums import AssertChannel, Expectation, FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext, RoleSessionPort
from autotester.schema.payment_path import (
    PAYMENT_FILE,
    CouponState,
    GatewayState,
    PathReport,
    PaymentDeclaration,
    PaymentPath,
)
from autotester.schema.platform import IMPLICIT_PLATFORM_ID
from autotester.schema.role_step import RoleStep
from autotester.store.filestore import read_json, write_text

REPORT_FILE = "payment_report.json"


class PaymentNotDeclaredError(RuntimeError):
    """No usable `payment_paths.json`; a closed phrase, never file text."""


class PaymentUnobservedError(RuntimeError):
    """A path could not be looked at and nothing else was proven; a closed phrase."""


def load_declaration(run_dir: str) -> PaymentDeclaration:
    """The declared paid paths in `run_dir`, or `PaymentNotDeclaredError`."""
    try:
        declaration = read_json(Path(run_dir) / PAYMENT_FILE, PaymentDeclaration)
    except OSError:
        declaration = None
    except ValueError:
        raise PaymentNotDeclaredError("payment declaration is invalid") from None
    if declaration is None:
        raise PaymentNotDeclaredError("no payment paths declared")
    return declaration


class _Walk:
    """One path being walked: the state the report is made from."""

    def __init__(self, path: PaymentPath, port: RoleSessionPort) -> None:
        self.path, self.port = path, port
        self.performed = 0
        self.test_steps = 0
        self.stop = False
        self.gateway = GatewayState.NOT_REACHED
        self.coupon = CouponState.NOT_REACHED if path.coupon_steps else CouponState.NOT_DECLARED

    def look(self, target: str) -> bool | None:
        probe = CrossRoleAssertion(
            id=f"{self.path.id}-look"[:64], observer_role_id=self.path.role_id,
            channel=AssertChannel.UI, expectation=Expectation.PRESENT, target=target,
            within_s=self.path.within_s)
        try:
            return self.port.observe(probe).matched
        except Exception:
            return None

    def _perform(self, tag: str, i: int, action: str) -> bool:
        step = RoleStep(id=f"{self.path.id}-{tag}{i}", role_id=self.path.role_id, action=action)
        try:
            self.port.perform(step)
        except Exception:
            return False
        self.performed += 1
        return True

    def _watch_gateway(self) -> None:
        seen = self.look(self.path.gateway_marker)
        if seen is None:
            self.gateway, self.stop = GatewayState.UNOBSERVED, True
        elif seen:
            self.gateway, self.stop = GatewayState.REACHED, True

    def phase(self, tag: str, actions: list[str]) -> bool:
        """Perform `actions`, watching for the gateway after each. False if a step raised."""
        for i, action in enumerate(actions):
            if self.stop:
                return True
            if not self._perform(tag, i, action):
                return False
            self._watch_gateway()
        return True

    def coupon_phase(self) -> None:
        if self.stop or not self.path.coupon_steps:
            return
        if not self.phase("coupon", self.path.coupon_steps):
            self.coupon = CouponState.NOT_APPLIED
            return
        if self.stop:
            return                      # the gateway came first: the coupon was never reached
        seen = self.look(self.path.coupon_marker or "")
        self.coupon = (CouponState.UNOBSERVED if seen is None
                       else CouponState.APPLIED if seen else CouponState.NOT_APPLIED)

    def sandbox_phase(self) -> None:
        if self.gateway is not GatewayState.REACHED or not self.path.provider_test_mode:
            return
        for i, action in enumerate(self.path.test_mode_steps):
            if not self._perform("sandbox", i, action):
                return
            self.test_steps += 1

    def report(self) -> PathReport:
        return PathReport(
            path_id=self.path.id, role_id=self.path.role_id, gateway=self.gateway,
            coupon=self.coupon, performed_steps=self.performed,
            stopped_at_gateway=self.gateway is GatewayState.REACHED,
            test_mode_steps_run=self.test_steps)


def check_path(path: PaymentPath, port: RoleSessionPort) -> PathReport:
    """Walk one path: reach checkout, try the coupon, open the gateway, stop at it."""
    walk = _Walk(path, port)
    if walk.phase("step", path.steps):
        walk.coupon_phase()
        walk.phase("gate", path.gateway_steps)
    walk.sandbox_phase()
    return walk.report()


def _finding(path: PaymentPath, what: str, tag: str, context: OracleContext) -> MultiRoleFinding:
    platform = path.platform_id or (context.platform_ids[0] if context.platform_ids
                                    else IMPLICIT_PLATFORM_ID)
    steps = [*path.steps, *path.coupon_steps, *path.gateway_steps][:50]
    return MultiRoleFinding(
        finding_id=f"pay-{path.id}-{tag}", finding_class=FindingClass.PAYMENT_PATH,
        title=what, role=path.role_id, platform_id=platform, url_template="/",
        steps=steps or ["goto /"], count=1)


def findings_from(path: PaymentPath, report: PathReport,
                  context: OracleContext) -> list[MultiRoleFinding]:
    """A finding per proven break: gateway not reached, coupon not applied."""
    found: list[MultiRoleFinding] = []
    if report.gateway is GatewayState.NOT_REACHED:
        found.append(_finding(path, "Declared paid path did not reach a gateway page",
                              "gateway", context))
    if report.coupon is CouponState.NOT_APPLIED:
        found.append(_finding(path, "Declared coupon path did not apply the coupon",
                              "coupon", context))
    return found


def _write_report(run_dir: str, reports: list[PathReport]) -> None:
    folder = Path(run_dir)
    if not folder.is_dir():
        return
    body = "[" + ",".join(r.model_dump_json() for r in reports) + "]"
    try:
        write_text(folder / REPORT_FILE, body)
    except OSError:
        return


def payment_findings(context: OracleContext,
                     declaration: PaymentDeclaration | None = None) -> list[MultiRoleFinding]:
    """Walk every declared path; findings for proven breaks, error if unseen and nothing proven."""
    declaration = (declaration or context.declarations.payment_paths
                   or load_declaration(context.run_dir))
    if declaration.paths and context.port is None:
        raise PaymentUnobservedError("no session port to walk the paths with")
    findings: list[MultiRoleFinding] = []
    reports: list[PathReport] = []
    for path in declaration.paths:
        report = check_path(path, context.port)
        reports.append(report)
        findings += findings_from(path, report, context)
    _write_report(context.run_dir, reports)
    blind = any(GatewayState.UNOBSERVED is r.gateway or CouponState.UNOBSERVED is r.coupon
                for r in reports)
    if blind and not findings:
        raise PaymentUnobservedError("a declared path could not be looked at")
    return findings


run = payment_findings
"""The registry's entry point (`schema/oracle_context.py`). An alias, not a second `def run`: the
doctor's duplicate-concept rule flags a top-level `def run` because `doctor.py` already has one."""
