"""The hidden API error oracle (MP21): a first-party 4xx/5xx behind a screen that shows success.

One job: for every step whose UI showed success (`success_indicator` set), turn each distinct
first-party request that answered 4xx or 5xx into a `hidden_api_error` finding that cites the
request (method, status, redacted URL template) and the success screen (the indicator and the
screen template). Repeats of the same request count once with `count` set to how often. A step
whose UI showed no success is not this oracle's business; a third-party failure never reaches it
because the samples came through `network_capture`. Deterministic and offline: no browser, no
provider, nothing sent to a model (MPI1). Priority is not set here; it is
`finding_priority.priority_for(finding_class)`.
"""

from __future__ import annotations

from collections import Counter

from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext
from autotester.schema.request_budget import StepNetworkLog, network_log_from
from autotester.stages.oracle_request_budget import TITLE_MAX, safe_template

FIRST_ERROR_STATUS = 400
LAST_ERROR_STATUS = 599


def _title(method: str, status: int, request: str, indicator: str, screen: str) -> str:
    text = (f"Hidden API error: {method} {request} returned {status} while the screen showed "
            f"success ({indicator}) at {screen}")
    return text if len(text) <= TITLE_MAX else text[: TITLE_MAX - 1] + "~"


def _log_findings(log: StepNetworkLog, indicator: str, start: int) -> list[MultiRoleFinding]:
    failures = Counter((s.method, safe_template(s.url), s.status) for s in log.samples
                       if FIRST_ERROR_STATUS <= s.status <= LAST_ERROR_STATUS)
    screen = safe_template(log.screen_url)
    return [
        MultiRoleFinding(
            finding_id=f"hidden-api-error-{start + i}", finding_class=FindingClass.HIDDEN_API_ERROR,
            title=_title(method, status, request, indicator, screen),
            role=log.role_id, platform_id=log.platform_id, url_template=request,
            steps=list(log.repro_steps), count=count, oracle=OracleName.API_ERROR)
        for i, ((method, request, status), count) in enumerate(failures.items())]


def hidden_api_errors(logs: list[StepNetworkLog]) -> list[MultiRoleFinding]:
    """One finding per distinct failing request in a step whose UI showed success."""
    findings: list[MultiRoleFinding] = []
    for log in logs:
        if log.success_indicator is not None:
            findings.extend(_log_findings(log, log.success_indicator, len(findings)))
    return findings


def check_api_errors(context: OracleContext) -> list[MultiRoleFinding]:
    """MP21 on the port's network log; `NetworkLogUnavailable` when the port has none."""
    return hidden_api_errors(network_log_from(context)[0])


run = check_api_errors
"""The registry's entry point (`schema/oracle_context.py`). An alias, not a second definition:
`autotester doctor`'s duplicate-concept rule would flag a `def run` here against `doctor.run`."""
