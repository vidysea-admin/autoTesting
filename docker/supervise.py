"""Supervise the container's display, viewers and app as one fail-fast stack."""

from __future__ import annotations

import os
import shlex
import signal
import socket
import subprocess
import sys
import time


def endpoint_ready(endpoint: str) -> bool:
    """Connect to the expected socket before starting its dependent service."""
    unix = endpoint.startswith("unix:")
    family = socket.AF_UNIX if unix else socket.AF_INET
    address = endpoint[5:] if unix else ("127.0.0.1", int(endpoint[4:]))
    try:
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.1)
            connection.connect(address)
        return True
    except OSError:
        return False


def reap_children(children: list[subprocess.Popen]) -> None:
    """Collect tracked children and, when PID 1, any adopted orphan children."""
    if os.name != "posix":
        for child in children:
            child.poll()
        return
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return
        for child in children:
            if child.pid == pid:
                child.returncode = os.waitstatus_to_exitcode(status)


def signal_children(children: list[subprocess.Popen], sig: int) -> None:
    """Signal whole service groups, including descendants of exited leaders."""
    for child in children:
        try:
            if os.name == "posix":
                os.killpg(child.pid, sig)
            elif child.poll() is None:
                child.terminate() if sig == signal.SIGTERM else child.kill()
        except ProcessLookupError:
            pass


def stop_children(children: list[subprocess.Popen], grace: float) -> None:
    signal_children(children, signal.SIGTERM)
    deadline = time.monotonic() + grace
    # Keep the grace period even if leaders exit: descendants may still be flushing.
    while children and time.monotonic() < deadline:
        reap_children(children)
        time.sleep(0.05)
    signal_children(children, signal.SIGKILL if os.name == "posix" else signal.SIGTERM)
    for child in children:
        child.wait()
    reap_children(children)


def run_stack(services: list[tuple[str, list[str]]], *, timeout=60.0, grace=2.0) -> int:
    """Return failure on any child exit/startup failure; drain all children on signals."""
    children: list[subprocess.Popen] = []
    stopping = 0

    def request_stop(signum, _frame):
        nonlocal stopping
        stopping = signum

    previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for endpoint, command in services:
            if stopping:
                return 128 + stopping
            children.append(subprocess.Popen(command, start_new_session=os.name == "posix"))
            deadline = time.monotonic() + timeout
            while True:
                reap_children(children)
                if stopping:
                    return 128 + stopping
                if any(child.returncode is not None for child in children):
                    print("container service exited; restarting stack", file=sys.stderr)
                    return 1
                if not endpoint or endpoint_ready(endpoint):
                    break
                if time.monotonic() >= deadline:
                    print("container service startup timed out", file=sys.stderr)
                    return 1
                time.sleep(0.05)
        while not stopping:
            reap_children(children)
            if any(child.returncode is not None for child in children):
                print("container service exited; restarting stack", file=sys.stderr)
                return 1
            time.sleep(0.05)
        return 128 + stopping
    except OSError:
        print("container service could not start", file=sys.stderr)
        return 1
    finally:
        stop_children(children, grace)
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if len(arguments) == 0 or len(arguments) % 2:
        raise SystemExit("expected readiness endpoint / command pairs")
    raise SystemExit(run_stack([(arguments[i], shlex.split(arguments[i + 1]))
                               for i in range(0, len(arguments), 2)]))
