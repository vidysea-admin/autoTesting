"""T-177 follow-up F1/F2/F4: the exact pin, the telemetry switch, and the session-fed backend.

Contract: D-075. The telemetry checks run in a fresh interpreter, because "set at import" and
"before browser-use is first imported" cannot be observed from a process that already has both.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from autotester.core.redact import Redactor
from autotester.providers.mock import MockProvider
from autotester.stages.agent_actuator import ActuatorError
from autotester.stages.browser_use_backend import (
    BrowserUseBackend,
    ProviderChatModel,
    _load,
)

ROOT = Path(__file__).resolve().parents[1]
SWITCHES = ("ANONYMIZED_TELEMETRY", "BROWSER_USE_CLOUD_SYNC")


def test_f1_pyproject_pins_browser_use_exactly() -> None:
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["project"]["dependencies"]
    assert [d.split("#")[0].strip() for d in deps if d.startswith("browser-use")] == [
        "browser-use==0.5.9"]


def test_f1_uv_lock_records_the_exact_specifier_and_version() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text("utf-8"))
    pkgs = {p["name"]: p for p in lock["package"]}
    assert pkgs["browser-use"]["version"] == "0.5.9"
    requires = pkgs["autotester"]["metadata"]["requires-dist"]
    assert [r["specifier"] for r in requires if r["name"] == "browser-use"] == ["==0.5.9"]
    assert importlib.metadata.version("browser-use") == "0.5.9"


def run_fresh(body: str, **env: str) -> dict:
    """Run `body` in a new interpreter with browser-use's switches pre-set to ENABLED."""
    child = {k: v for k, v in os.environ.items() if k != "PYTHON_DOTENV_DISABLED"}
    child.update({k: "true" for k in SWITCHES} | env)
    done = subprocess.run([sys.executable, "-c", textwrap.dedent(body)], env=child,
                          capture_output=True, text=True, timeout=120, cwd=ROOT)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_f2_importing_the_backend_forces_telemetry_and_cloud_sync_off() -> None:
    out = run_fresh("""
        import json, os, sys
        assert "browser_use" not in sys.modules
        import autotester.stages.browser_use_backend  # noqa: F401
        print(json.dumps({k: os.environ.get(k) for k in ("ANONYMIZED_TELEMETRY",
                                                         "BROWSER_USE_CLOUD_SYNC")}))
    """)
    assert out == {"ANONYMIZED_TELEMETRY": "false", "BROWSER_USE_CLOUD_SYNC": "false"}


def test_f2_no_telemetry_client_or_cloud_sync_is_constructed_by_an_agent() -> None:
    """Even with the user's environment saying 'true', browser-use builds no PostHog client."""
    out = run_fresh("""
        import json
        import autotester.stages.browser_use_backend as b
        import browser_use.telemetry.service as svc
        built = []
        svc.Posthog = lambda *a, **k: built.append((a, k))
        from browser_use import Agent, BrowserSession
        from browser_use.config import CONFIG
        from autotester.providers.mock import MockProvider
        agent = Agent(task="t", llm=b.ProviderChatModel(MockProvider(), guard=str),
                      browser_session=BrowserSession(cdp_url="http://127.0.0.1:9", **b.PROFILE),
                      use_vision=False)
        print(json.dumps({"posthog_built": len(built), "telemetry": CONFIG.ANONYMIZED_TELEMETRY,
                          "cloud": CONFIG.BROWSER_USE_CLOUD_SYNC,
                          "client": agent.telemetry._posthog_client is not None,
                          "agent_sync": agent.enable_cloud_sync,
                          "has_cloud": hasattr(agent, "cloud_sync"),
                          "ext": agent.browser_session.browser_profile.enable_default_extensions}))
    """)
    assert out == {"posthog_built": 0, "telemetry": False, "cloud": False, "client": False,
                   "agent_sync": False, "has_cloud": False, "ext": False}


class FakeSession:
    """Stands in for BrowserSession: only `cdp_url`, `project` and `secrets` are read."""

    def __init__(self, cdp_url: str | None) -> None:
        self._url, self.reads = cdp_url, 0
        self.project = SimpleNamespace(allowed_domains=["pathlynks.test"])
        self.secrets = SimpleNamespace(redactor=lambda: Redactor({"K": "hunter2"}))

    @property
    def cdp_url(self) -> str | None:
        self.reads += 1
        return self._url


def test_f4_backend_is_built_from_the_sessions_cdp_url() -> None:
    session = FakeSession("http://127.0.0.1:9333")
    backend = BrowserUseBackend.for_session(MockProvider(), session)
    assert session.reads >= 1 and backend.cdp_url == "http://127.0.0.1:9333"


def test_f4_a_session_without_a_cdp_endpoint_is_refused_not_guessed() -> None:
    with pytest.raises(ActuatorError, match="expose_cdp"):
        BrowserUseBackend.for_session(MockProvider(), FakeSession(None))


def test_f4_the_agent_attaches_to_that_url_only(monkeypatch: pytest.MonkeyPatch) -> None:
    import browser_use

    seen: dict[str, Any] = {}

    class FakeBu:
        def __init__(self, **kw: Any) -> None:
            seen["bu"] = kw

    class FakeHistory:
        def final_result(self) -> str:
            return "ok"

        def number_of_steps(self) -> int:
            return 1

        def is_done(self) -> bool:
            return True

        def is_successful(self) -> bool:
            return True

    class FakeAgent:
        id = "a1"

        def __init__(self, **kw: Any) -> None:
            seen["agent"] = kw

        async def run(self, max_steps: int) -> FakeHistory:
            return FakeHistory()

    monkeypatch.setattr(browser_use, "BrowserSession", FakeBu)
    monkeypatch.setattr(browser_use, "Agent", FakeAgent)
    backend = BrowserUseBackend.for_session(MockProvider(), FakeSession("http://127.0.0.1:9333"))
    out = asyncio.run(backend._drive("task", lambda a: None, 3, 5.0))
    assert out["resolved"] is True
    assert seen["bu"]["cdp_url"] == "http://127.0.0.1:9333"
    assert seen["bu"]["enable_default_extensions"] is False
    assert seen["bu"]["allowed_domains"] == ["*.pathlynks.test"]  # defence in depth
    assert os.environ["ANONYMIZED_TELEMETRY"] == "false"


# -- fix cycle 1: item 4, the model shim is a real browser-use chat model -----------------------

def test_item4_provider_chat_model_satisfies_browser_uses_type_check(
        monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    _load()
    from browser_use import Agent
    from browser_use.llm.base import BaseChatModel

    def no_network(*_a: Any, **_k: Any) -> None:
        raise AssertionError("constructing an Agent must not touch the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    model = ProviderChatModel(MockProvider(), guard=str)
    assert isinstance(model, BaseChatModel)
    agent = Agent(task="t", llm=model, use_vision=False)  # raised ValueError before the fix
    assert agent.llm is model


# -- item 5: browser-use's import-time load_dotenv must not read our .env ----------------------

def test_item5_a_dotenv_sentinel_never_reaches_the_environment(tmp_path: Path) -> None:
    sentinel = tmp_path / ".env"
    sentinel.write_text("AT_SENTINEL_SECRET=hunter2\n", encoding="utf-8")
    out = run_fresh(f"""
        import dotenv.main, json, os
        dotenv.main.find_dotenv = lambda *a, **k: {str(sentinel)!r}
        import autotester.stages.browser_use_backend as b
        b._load()
        import browser_use
        from browser_use import Agent
        import browser_use.telemetry.service, browser_use.tokens.service
        print(json.dumps({{"leaked": os.environ.get("AT_SENTINEL_SECRET"),
                          "off": os.environ.get("PYTHON_DOTENV_DISABLED")}}))
    """)
    assert out == {"leaked": None, "off": "1"}


def test_item5_autotesters_own_env_loader_is_unaffected_by_the_switch(tmp_path: Path) -> None:
    from autotester.core.env import dotenv_values  # the loader uses dotenv_values

    _load()
    env = tmp_path / ".env"
    env.write_text("AT_OWN_KEY=1\n", encoding="utf-8")
    assert dotenv_values(env) == {"AT_OWN_KEY": "1"}


# -- item 6: the secret guard is never the identity function by default ------------------------

def test_item6_a_guard_must_be_given_explicitly_to_the_bare_constructors() -> None:
    with pytest.raises(TypeError):
        ProviderChatModel(MockProvider())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        BrowserUseBackend(MockProvider(), "http://127.0.0.1:9")  # type: ignore[call-arg]


def test_item6_for_session_defaults_to_the_sessions_secret_scrubber() -> None:
    backend = BrowserUseBackend.for_session(MockProvider(), FakeSession("http://127.0.0.1:9333"))
    masked = backend.guard("url=https://x.test/?pw=hunter2")
    assert "hunter2" not in masked and "[REDACTED]" in masked
    explicit = BrowserUseBackend.for_session(MockProvider(), FakeSession("http://127.0.0.1:9"),
                                             guard=lambda t: "G:" + t)
    assert explicit.guard("a") == "G:a"
