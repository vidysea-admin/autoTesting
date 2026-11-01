"""E7.4 (qa/contracts/e2e-fixes.md, AT-1420 diagnostic): every unreachable-target message carries
one stable `[stage=...]` token, still names only the host, and keeps its existing wording.
"""

from __future__ import annotations

import errno
import http.client
import socket
import ssl
import urllib.error
from pathlib import Path

import pytest
from e2e_run_fixture import seams, store_for
from e2e_target_stub import silent

from autotester.browser.session import BrowserSession
from autotester.schema.project import Project
from autotester.stages import reachability
from autotester.stages.reachability import _failure_message, probe_target
from autotester.stages.run_launcher import launch_run

HOST = "h.example"
CANARY_IP = "203.0.113.77"
CASES = [
    (urllib.error.URLError(socket.gaierror(11001, f"getaddrinfo {CANARY_IP}")), "dns",
     "could not be resolved (DNS)"),
    (urllib.error.URLError(ConnectionRefusedError(f"refused {CANARY_IP}")), "tcp", "refused"),
    (urllib.error.URLError(ConnectionResetError(f"reset {CANARY_IP}")), "tcp",
     "closed the connection"),
    (urllib.error.URLError(OSError(errno.ENETUNREACH, f"net unreachable {CANARY_IP}")), "tcp",
     "could not be reached"),
    (urllib.error.URLError(OSError(errno.EHOSTUNREACH, f"no route {CANARY_IP}")), "tcp",
     "could not be reached"),
    (urllib.error.URLError(ssl.SSLCertVerificationError(f"bad cert {CANARY_IP}")), "tls",
     "TLS handshake"),
    (urllib.error.URLError(ssl.SSLError(f"hs {CANARY_IP}")), "tls", "TLS handshake"),
    (http.client.RemoteDisconnected(f"closed {CANARY_IP}"), "http", "without an HTTP answer"),
    (http.client.BadStatusLine(f"garbage {CANARY_IP}"), "http", "without an HTTP answer"),
    (urllib.error.URLError(TimeoutError(f"timed out {CANARY_IP}")), "timeout",
     "did not answer within 10 s"),
    (TimeoutError("no answer"), "timeout", "did not answer within 10 s"),
    (ValueError(f"surprise {CANARY_IP}"), "unknown", "could not be reached"),
    (urllib.error.URLError(f"odd {CANARY_IP}"), "unknown", "could not be reached"),
]


@pytest.mark.parametrize(("exc", "stage", "wording"), CASES)
def test_each_failure_class_carries_its_stage_token_and_keeps_its_wording(
        exc: BaseException, stage: str, wording: str) -> None:
    message = _failure_message(HOST, exc)
    assert message.endswith(f" from this server [stage={stage}]")
    assert wording in message and message.startswith(f"target {HOST} ")
    assert message.count("[stage=") == 1


@pytest.mark.parametrize(("exc", "stage", "wording"), CASES)
def test_the_message_names_only_the_host(exc: BaseException, stage: str, wording: str) -> None:
    message = _failure_message(HOST, exc)
    assert CANARY_IP not in message and "getaddrinfo" not in message
    assert "surprise" not in message and "garbage" not in message and "odd " not in message


def test_a_closed_local_port_is_stage_tcp() -> None:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # nothing listens now
    message = probe_target(Project(slug="demo", name="Demo", base_url=f"http://127.0.0.1:{port}/",
                                   allowed_domains=["127.0.0.1"]))
    assert message is not None and message.endswith("[stage=tcp]")


def test_an_unresolvable_name_is_stage_dns() -> None:
    message = probe_target(Project(slug="demo", name="Demo", base_url="http://no-such-host.invalid/",
                                   allowed_domains=["no-such-host.invalid"]))
    assert message is not None and message.endswith("[stage=dns]")


def test_the_token_reaches_the_run_every_case_and_the_page_message(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The blackhole through `launch_run`: `skip_run` carries the one message to the Run and to
    each verdict note; no browser starts."""
    monkeypatch.setattr(reachability, "PROBE_TOTAL_S", 1.0)

    def boom(self):
        raise AssertionError("a browser was started for an unreachable target")

    monkeypatch.setattr(BrowserSession, "start", boom)
    with silent() as stub:
        store = store_for(tmp_path, monkeypatch, stub.url, cases=2)
        run = launch_run("demo", seams=seams(target_probe=probe_target))
    message = "target 127.0.0.1 did not answer within 1 s from this server [stage=timeout]"
    assert run.preflight_warnings == [message]
    verdicts = store.load_verdicts(run.id)
    assert len(verdicts) == 2 and all(message in (v.note or "") for v in verdicts)
