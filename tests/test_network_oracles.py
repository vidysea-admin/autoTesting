"""T-214 (multi-role-platform.md MP21, MP22): the hidden-API-error and request-budget oracles.

MP21: a first-party 4xx/5xx during a step whose UI shows success is a finding citing the redacted
URL, the status and the success screen. MP22: requests per screen and the minimum polling interval
are measured from `network_capture` and compared with the declared budget. Fixtures are synthetic
and cover each rule as a matrix (MPI2); no browser, no network, no provider.
"""

from __future__ import annotations

import inspect

import pytest
from network_oracle_fakes import SECRET, FakeNetworkPort, PlainPort, log_for
from pydantic import ValidationError

from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.oracle_context import OracleContext, OracleState
from autotester.schema.request_budget import (
    NetworkLogUnavailable,
    NetworkSample,
    RequestBudget,
    StepNetworkLog,
)
from autotester.stages import oracle_api_error, oracle_request_budget
from autotester.stages.oracle_api_error import hidden_api_errors
from autotester.stages.oracle_registry import oracle_statuses, run_oracles
from autotester.stages.oracle_request_budget import budget_findings

ORDERS = "https://app.test/api/orders"
BUDGET = RequestBudget(max_requests_per_screen=50, min_poll_interval_s=1.0)


def _context(port: object) -> OracleContext:
    return OracleContext(project_slug="demo", run_dir=".", scenario_id="s1", port=port)


def _polls(url: str, count: int, gap: float, start: float = 0.0) -> list:
    return [("GET", url, 200, round(start + i * gap, 3)) for i in range(count)]


def _distinct(count: int, offset: int = 0) -> list:
    return [("GET", f"https://app.test/api/r{i + offset}", 200, float(i + offset))
            for i in range(count)]


# ---- MP21 hidden API error ------------------------------------------------------------------

def test_mp21_a_500_behind_a_success_toast_is_one_finding_citing_url_status_and_screen() -> None:
    log = log_for([("GET", "https://app.test/api/me", 200, 0.1),
                   ("POST", f"{ORDERS}/12345?ref=abc", 500, 0.2)], success="#toast-success")
    [finding] = hidden_api_errors([log])
    assert finding.finding_class is FindingClass.HIDDEN_API_ERROR
    assert finding.oracle is OracleName.API_ERROR
    assert finding.count == 1 and finding.role == "teacher" and finding.platform_id == "parent"
    assert finding.url_template == "https://app.test/api/orders/{id}?ref={value}"
    assert "500" in finding.title and "#toast-success" in finding.title
    assert "POST" in finding.title and "/orders" in finding.title
    assert finding.steps == ["login portal", "click #submit"]
    assert "12345" not in finding.model_dump_json() and "abc" not in finding.model_dump_json()


@pytest.mark.parametrize("status", [400, 401, 404, 422, 499, 500, 502, 503, 599])
def test_mp21_every_4xx_and_5xx_is_flagged(status: int) -> None:
    log = log_for([("POST", ORDERS, status, 0.0)], success="#toast-success")
    assert [f.count for f in hidden_api_errors([log])] == [1]


@pytest.mark.parametrize("status", [200, 201, 204, 301, 302, 304, 399])
def test_mp21_a_non_error_status_is_not_flagged(status: int) -> None:
    log = log_for([("POST", ORDERS, status, 0.0)], success="#toast-success")
    assert hidden_api_errors([log]) == []


def test_mp21_no_finding_when_the_ui_did_not_show_success() -> None:
    log = log_for([("POST", ORDERS, 500, 0.0)], success=None)
    assert hidden_api_errors([log]) == []


def test_mp21_third_party_failures_are_not_product_errors() -> None:
    log = log_for([("GET", "https://analytics.example.net/collect", 500, 0.0),
                   ("GET", "https://cdn.other.test/lib.js", 404, 0.1)], success="#toast-success")
    assert log.samples == [] and hidden_api_errors([log]) == []


def test_mp21_repeats_group_and_distinct_requests_are_distinct_findings() -> None:
    log = log_for([("POST", ORDERS, 500, 0.0), ("POST", ORDERS, 500, 0.5),
                   ("POST", ORDERS, 500, 0.9), ("PUT", "https://app.test/api/cart", 503, 1.0)],
                  success="#ok")
    findings = hidden_api_errors([log])
    assert sorted(f.count for f in findings) == [1, 3]
    assert len({f.finding_id for f in findings}) == 2


def test_mp21_the_secret_in_a_url_never_reaches_the_finding() -> None:
    log = log_for([("POST", f"{ORDERS}?token={SECRET}", 500, 0.0)], success="#toast-success")
    assert SECRET not in log.samples[0].url
    assert SECRET not in hidden_api_errors([log])[0].model_dump_json()


def test_mp21_run_reads_the_port_and_names_the_oracle() -> None:
    port = FakeNetworkPort([log_for([("POST", ORDERS, 500, 0.0)], success="#toast-success")])
    findings = oracle_api_error.run(_context(port))
    assert [f.finding_class for f in findings] == [FindingClass.HIDDEN_API_ERROR]


def test_a_port_without_a_network_log_is_reported_not_silently_clean() -> None:
    with pytest.raises(NetworkLogUnavailable):
        oracle_api_error.run(_context(PlainPort()))
    with pytest.raises(NetworkLogUnavailable):
        oracle_request_budget.run(_context(PlainPort()))
    summary, found = run_oracles(_context(PlainPort()), [OracleName.API_ERROR])
    status = next(s for s in summary.statuses if s.oracle is OracleName.API_ERROR)
    assert status.state is OracleState.ERRORED and status.reason == "NetworkLogUnavailable"
    assert found == []


def test_the_registry_sees_both_oracles_as_built() -> None:
    states = {s.oracle: s.state for s in oracle_statuses().statuses}
    assert states[OracleName.API_ERROR] is OracleState.NOT_RUN
    assert states[OracleName.REQUEST_BUDGET] is OracleState.NOT_RUN
    port = FakeNetworkPort([log_for([("POST", ORDERS, 500, 0.0)], success="#x")], BUDGET)
    summary, found = run_oracles(_context(port), [OracleName.API_ERROR, OracleName.REQUEST_BUDGET])
    ran = {s.oracle: (s.state, s.finding_count) for s in summary.statuses}
    assert ran[OracleName.API_ERROR] == (OracleState.RAN, 1)
    assert ran[OracleName.REQUEST_BUDGET] == (OracleState.RAN, 0) and len(found) == 1


# ---- MP22 request and polling budget --------------------------------------------------------

def test_mp22_polling_every_200ms_against_a_1s_budget_is_a_finding_with_the_numbers() -> None:
    log = log_for(_polls("https://app.test/api/status", 6, 0.2))
    [finding] = budget_findings([log], BUDGET)
    assert finding.finding_class is FindingClass.REQUEST_BUDGET
    assert finding.oracle is OracleName.REQUEST_BUDGET
    assert finding.count == 6
    assert "0.20 s" in finding.title and "1.00 s" in finding.title and "GET" in finding.title
    assert finding.url_template == "https://app.test/api/status"


@pytest.mark.parametrize(("gap", "flagged"), [(0.2, True), (0.999, True), (1.0, False),
                                              (1.5, False)])
def test_mp22_the_polling_boundary_is_the_declared_interval(gap: float, flagged: bool) -> None:
    findings = budget_findings([log_for(_polls("https://app.test/api/s", 4, gap))], BUDGET)
    assert bool(findings) is flagged


def test_mp22_two_requests_are_not_polling_until_the_declared_repeat_count() -> None:
    log = log_for(_polls("https://app.test/api/s", 2, 0.1))
    assert budget_findings([log], BUDGET) == []
    tight = RequestBudget(max_requests_per_screen=50, min_poll_interval_s=1.0,
                          min_repeats_for_polling=2)
    assert len(budget_findings([log], tight)) == 1


def test_mp22_only_the_fast_endpoint_is_flagged_when_polls_interleave() -> None:
    fast = _polls("https://app.test/api/fast", 6, 0.2)
    slow = _polls("https://app.test/api/slow", 3, 2.0)
    findings = budget_findings([log_for(fast + slow)], BUDGET)
    assert [f.url_template for f in findings] == ["https://app.test/api/fast"]


def test_mp22_the_same_endpoint_with_different_ids_is_one_polled_endpoint() -> None:
    rows = [("GET", f"https://app.test/api/items/{1000 + i}", 200, i * 0.2) for i in range(4)]
    [finding] = budget_findings([log_for(rows)], BUDGET)
    assert finding.url_template == "https://app.test/api/items/{id}" and finding.count == 4


def test_mp22_unsorted_timestamps_are_measured_in_time_order() -> None:
    rows = list(reversed(_polls("https://app.test/api/s", 4, 0.2)))
    assert len(budget_findings([log_for(rows)], BUDGET)) == 1


@pytest.mark.parametrize(("count", "flagged"), [(49, False), (50, False), (51, True)])
def test_mp22_requests_per_screen_over_the_budget_is_a_finding(count: int, flagged: bool) -> None:
    findings = budget_findings([log_for(_distinct(count))], BUDGET)
    assert bool(findings) is flagged
    if flagged:
        assert findings[0].count == 51 and "51" in findings[0].title and "50" in findings[0].title
        assert findings[0].url_template == "https://app.test/orders"


def test_mp22_requests_add_up_per_screen_across_steps_not_across_screens_or_roles() -> None:
    same = [log_for(_distinct(30), step_id="a"), log_for(_distinct(30, 100), step_id="b")]
    assert len(budget_findings(same, BUDGET)) == 1
    other_screen = [log_for(_distinct(30), step_id="a"),
                    log_for(_distinct(30, 100), step_id="b", screen_url="https://app.test/other")]
    assert budget_findings(other_screen, BUDGET) == []
    other_role = [log_for(_distinct(30), step_id="a"),
                  log_for(_distinct(30, 100), step_id="b", role_id="parent")]
    assert budget_findings(other_role, BUDGET) == []


def test_mp22_run_without_a_declared_budget_finds_nothing_and_with_one_finds_it() -> None:
    log = log_for(_polls("https://app.test/api/s", 6, 0.2))
    assert oracle_request_budget.run(_context(FakeNetworkPort([log], None))) == []
    assert len(oracle_request_budget.run(_context(FakeNetworkPort([log], BUDGET)))) == 1


def test_mp22_a_budget_exceeded_two_ways_gives_two_findings_with_distinct_ids() -> None:
    findings = budget_findings([log_for(_polls("https://app.test/api/s", 60, 0.2))], BUDGET)
    assert len(findings) == 2 and len({f.finding_id for f in findings}) == 2


# ---- shapes, capture and MPI1 ---------------------------------------------------------------

def test_the_shapes_are_closed() -> None:
    ok = {"max_requests_per_screen": 5, "min_poll_interval_s": 1}
    for bad in ({**ok, "max_requests_per_screen": 0}, {**ok, "min_poll_interval_s": 0},
                {**ok, "min_repeats_for_polling": 1}, {**ok, "extra": 1}):
        with pytest.raises(ValidationError):
            RequestBudget(**bad)
    with pytest.raises(ValidationError):
        NetworkSample(method="GET", url="https://app.test/", status=99, t_s=0.0)
    with pytest.raises(ValidationError):
        NetworkSample(method="GET", url="https://app.test/", status=200, t_s=-1.0)


@pytest.mark.parametrize("patch", [{"success_indicator": "toast for a@b.co"},
                                   {"repro_steps": []}, {"repro_steps": ["dance now"]},
                                   {"step_id": "Bad Id"}, {"extra": 1}])
def test_a_step_network_log_refuses_unsafe_or_unreplayable_input(patch: dict) -> None:
    base = {"step_id": "submit", "role_id": "teacher", "platform_id": "parent",
            "screen_url": "https://app.test/orders", "repro_steps": ["click #go"], "samples": []}
    StepNetworkLog(**base)
    with pytest.raises(ValidationError):
        StepNetworkLog(**{**base, **patch})


def test_capture_samples_reuses_network_capture_for_scope_and_redaction() -> None:
    log = log_for([("GET", f"https://app.test/a?k={SECRET}", 200, 0.25),
                   ("GET", "https://tracker.example.net/p", 200, 0.3)])
    [sample] = log.samples
    assert sample.t_s == 0.25 and sample.status == 200 and "[REDACTED]" in sample.url


def test_mpi1_findings_carry_no_personal_canary_and_no_provider_is_used() -> None:
    canary = "canary.person@example.com"
    log = log_for([("POST", f"{ORDERS}/987654?email={canary}", 500, 0.0),
                   *_polls("https://app.test/api/s?who=555-123-4567", 5, 0.1)], success="#ok")
    found = hidden_api_errors([log]) + budget_findings([log], BUDGET)
    blob = "".join(f.model_dump_json() for f in found)
    assert found and canary not in blob and "987654" not in blob and "555-123-4567" not in blob
    for module in (oracle_api_error, oracle_request_budget):
        assert "autotester.providers" not in inspect.getsource(module)
