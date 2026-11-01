"""E4.2 (qa/contracts/e2e-fixes.md, AT-1421): the one-shot, read-only reachability preflight.

`probe_target(project)` returns None when the run may proceed (any HTTP answer, a skipped probe)
and ONE plain sentence naming the host and the failure class when it may not. Local stubs only
(`e2e_target_stub`): no real network, no credential, no `.env` value.
"""

from __future__ import annotations

import time

import pytest
from e2e_target_stub import responder, silent

from autotester.schema.project import Project
from autotester.stages import reachability
from autotester.stages.reachability import probe_target


def _project(url: str, domains: list[str] | None = None) -> Project:
    return Project(slug="demo", name="Demo", base_url=url,
                   allowed_domains=["127.0.0.1"] if domains is None else domains)


def test_a_target_that_accepts_and_never_answers_fails_within_the_bound() -> None:
    """The contract's blackhole: the real 10 s constant, done in well under 15 s."""
    with silent() as stub:
        started = time.monotonic()
        message = probe_target(_project(stub.url))
        elapsed = time.monotonic() - started
    assert message == "target 127.0.0.1 did not answer within 10 s from this server"
    assert elapsed <= 15


def test_the_message_names_the_host_and_never_the_path_or_query() -> None:
    with silent() as stub:
        url = stub.url + "secret/path?token=CANARY-TOKEN"
        message = probe_target(_project(url))
    assert "CANARY-TOKEN" not in (message or "") and "secret/path" not in (message or "")


@pytest.mark.parametrize("status", [200, 401, 404, 500, 503])
def test_any_http_answer_counts_as_reachable(status: int) -> None:
    """A 401/500 is the product's own answer: the run proceeds (the cases will say what broke)."""
    with responder(status) as stub:
        assert probe_target(_project(stub.url)) is None
        assert len(stub.requests) == 1


def test_a_refused_connection_is_named() -> None:
    with silent() as stub:
        url = stub.url
    message = probe_target(_project(url))  # the port is closed again
    assert message is not None and "127.0.0.1" in message and "refused" in message


def test_a_name_that_does_not_resolve_is_named() -> None:
    message = probe_target(_project("http://no-such-host.invalid/", ["no-such-host.invalid"]))
    assert message is not None and "no-such-host.invalid" in message and "DNS" in message


def test_a_host_outside_allowed_domains_is_refused_without_any_connection() -> None:
    with silent() as stub:
        assert probe_target(_project(stub.url, ["pathlynks.example"])) is None
        assert not stub.saw_connect()


def test_no_allowed_domains_means_no_probe() -> None:
    with silent() as stub:
        assert probe_target(_project(stub.url, [])) is None
        assert not stub.saw_connect()


@pytest.mark.parametrize("url", ["ftp://127.0.0.1/", "javascript://127.0.0.1/%0aalert(1)",
                                 "http://user:pw@127.0.0.1/", "127.0.0.1", ""])
def test_a_url_that_is_not_plain_http_is_not_probed(url: str) -> None:
    assert probe_target(_project(url)) is None


def test_the_probe_sends_no_credential_no_cookie_no_body_and_follows_in_scope_redirects() -> None:
    with responder(302, location="/next", cookie=True) as stub:
        assert probe_target(_project(stub.url)) is None
        assert [path for path, _ in stub.requests] == ["/", "/next"]
        for _, headers in stub.requests:
            assert not {"cookie", "authorization", "content-length"} & set(headers)


def test_a_redirect_leaving_allowed_domains_is_not_followed() -> None:
    with silent() as elsewhere:
        target = elsewhere.url.replace("127.0.0.1", "localhost")
        with responder(302, location=target) as stub:
            assert probe_target(_project(stub.url)) is None  # a 302 is an answer
        assert not elsewhere.saw_connect()


def test_the_total_bound_is_the_module_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reachability, "PROBE_TOTAL_S", 1.0)
    with silent() as stub:
        started = time.monotonic()
        message = probe_target(_project(stub.url))
    assert time.monotonic() - started < 4
    assert message == "target 127.0.0.1 did not answer within 1 s from this server"


def test_one_retry_rescues_a_first_attempt_that_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    real = reachability._attempt

    def flaky(opener, url, timeout):
        calls.append(1)
        return OSError("transient") if len(calls) == 1 else real(opener, url, timeout)

    monkeypatch.setattr(reachability, "_attempt", flaky)
    with responder(200) as stub:
        assert probe_target(_project(stub.url)) is None
    assert len(calls) == 2
