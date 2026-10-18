"""The request and polling budget oracle (MP22), plus the adapter from `network_capture` to samples.

One job: compare what a role's screens actually requested with the project's declared
`RequestBudget`. Two measurements, each a `request_budget` finding with the measured numbers in its
title: requests per screen (a role's visits to one screen template, summed across steps) over
`max_requests_per_screen`, and the fastest repeat gap of one endpoint on one screen -- an endpoint
requested `min_repeats_for_polling` times or more -- under `min_poll_interval_s`. No budget declared
means nothing to exceed, so no finding. Deterministic and offline: no browser, no provider, nothing
sent to a model (MPI1).

`capture_samples` is the one bridge from raw `(method, url, status, t_s)` responses to
`NetworkSample`s: it calls `stages/network_capture.first_party_evidence` (the one first-party filter
and redactor, NA6) and parses its evidence line back, so third-party noise is dropped and a secret
in a URL is `[REDACTED]` before any oracle sees it. `safe_template` turns a URL into the
placeholder template a finding may carry; both oracles use it.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from itertools import pairwise
from urllib.parse import urlsplit

from autotester.core.redact import Redactor
from autotester.schema.crawl import SafetyPolicy
from autotester.schema.leak_evidence import validate_url_template
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext
from autotester.schema.project import Project
from autotester.schema.request_budget import (
    MAX_URL,
    NetworkSample,
    RequestBudget,
    StepNetworkLog,
    network_log_from,
)
from autotester.stages.leak_evidence import templatise_url
from autotester.stages.network_capture import first_party_evidence

TITLE_MAX = 200
STEPS_MAX = 50
_EVIDENCE_LINE = re.compile(r"^(\S+) (.*) -> (\d{3})$")
Response = tuple[str, str, int, float]


def safe_template(url: str) -> str:
    """`url` with ids and query values as placeholders, valid for a finding; never the raw URL."""
    try:
        return validate_url_template(templatise_url(url))
    except ValueError:
        pass
    try:
        parts = urlsplit(url)
        candidates = [f"{parts.scheme}://{parts.hostname}/{{path}}"] if (
            parts.scheme and parts.hostname) else []
    except ValueError:
        candidates = []
    for candidate in (*candidates, "/{path}"):
        try:
            return validate_url_template(candidate)
        except ValueError:
            continue
    return "/{path}"


def capture_samples(responses: Iterable[Response], project: Project, policy: SafetyPolicy,
                    redactor: Redactor) -> list[NetworkSample]:
    """First-party, redacted `NetworkSample`s from raw responses, via `network_capture`."""
    samples: list[NetworkSample] = []
    for method, url, status, t_s in responses:
        for item in first_party_evidence([(method.upper(), url, status)], project, policy,
                                         redactor):
            line = _EVIDENCE_LINE.match(item.path)
            if line:
                samples.append(NetworkSample(method=line[1], url=line[2][:MAX_URL],
                                             status=int(line[3]), t_s=t_s))
    return samples


def _clip(text: str) -> str:
    return text if len(text) <= TITLE_MAX else text[: TITLE_MAX - 1] + "~"


def _steps(logs: list[StepNetworkLog]) -> list[str]:
    ordered = dict.fromkeys(step for log in logs for step in log.repro_steps)
    return list(ordered)[:STEPS_MAX]


def _finding(finding_id: str, title: str, logs: list[StepNetworkLog], url_template: str,
             count: int) -> MultiRoleFinding:
    return MultiRoleFinding(
        finding_id=finding_id, finding_class=FindingClass.REQUEST_BUDGET, title=_clip(title),
        role=logs[0].role_id, platform_id=logs[0].platform_id, url_template=url_template,
        steps=_steps(logs), count=count, oracle=OracleName.REQUEST_BUDGET)


def _screens(logs: list[StepNetworkLog]) -> dict[tuple[str, str, str], list[StepNetworkLog]]:
    groups: dict[tuple[str, str, str], list[StepNetworkLog]] = defaultdict(list)
    for log in logs:
        groups[(log.role_id, log.platform_id, safe_template(log.screen_url))].append(log)
    return groups


def _screen_findings(screens: dict[tuple[str, str, str], list[StepNetworkLog]],
                     budget: RequestBudget, start: int) -> list[MultiRoleFinding]:
    out: list[MultiRoleFinding] = []
    for (_, _, screen), logs in screens.items():
        total = sum(len(log.samples) for log in logs)
        if total > budget.max_requests_per_screen:
            title = (f"Request budget exceeded: {total} requests on {screen} "
                     f"(budget {budget.max_requests_per_screen} per screen)")
            out.append(_finding(f"req-screen-{start + len(out)}", title, logs, screen, total))
    return out


def _poll_findings(screens: dict[tuple[str, str, str], list[StepNetworkLog]],
                   budget: RequestBudget, start: int) -> list[MultiRoleFinding]:
    out: list[MultiRoleFinding] = []
    for (_, _, screen), logs in screens.items():
        endpoints: dict[tuple[str, str], list[float]] = defaultdict(list)
        for sample in (s for log in logs for s in log.samples):
            endpoints[(sample.method, safe_template(sample.url))].append(sample.t_s)
        for (method, endpoint), times in endpoints.items():
            if len(times) < budget.min_repeats_for_polling:
                continue
            times.sort()
            gap = round(min(b - a for a, b in pairwise(times)), 3)
            if gap < budget.min_poll_interval_s:
                title = (f"Polling too fast: {method} {endpoint} every {gap:.2f} s at the "
                         f"shortest over {len(times)} requests on {screen} "
                         f"(budget {budget.min_poll_interval_s:.2f} s minimum)")
                out.append(_finding(f"req-poll-{start + len(out)}", title, logs, endpoint,
                                    len(times)))
    return out


def budget_findings(logs: list[StepNetworkLog], budget: RequestBudget) -> list[MultiRoleFinding]:
    """Every screen over its request budget, then every endpoint polled faster than allowed."""
    screens = _screens(logs)
    per_screen = _screen_findings(screens, budget, 0)
    return per_screen + _poll_findings(screens, budget, len(per_screen))


def check_request_budget(context: OracleContext) -> list[MultiRoleFinding]:
    """MP22 on the port's network log; `NetworkLogUnavailable` when the port has none."""
    logs, budget = network_log_from(context)
    return [] if budget is None else budget_findings(logs, budget)


run = check_request_budget
"""The registry's entry point (`schema/oracle_context.py`). An alias, not a second definition:
`autotester doctor`'s duplicate-concept rule would flag a `def run` here against `doctor.run`."""
