"""T-202: the LiteLLM provider's boundaries -- secret egress (LP7), credentials only
from the environment (LP8), no telemetry / lazy import (LP10), availability and a
clear error for a missing key or model (LP11). Fake `litellm` only (D-070)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from litellm_fake import install, no_network, reply
from pydantic import BaseModel, ConfigDict

from autotester.providers.base import ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider

pytestmark = pytest.mark.usefixtures("no_network")

GOOD = {"verdict": "pass", "score": 3, "inner": {"note": "ok"}}
SECRET = "hunter2-very-secret-value"


class Inner(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: str
    score: int
    inner: Inner


@pytest.fixture(autouse=True)
def _isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))  # no real .env in the guard


def _provider(model: str = "openai/gpt-4o", **options: Any) -> LiteLLMProvider:
    return LiteLLMProvider(model=model, **options)


def _with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LITELLM_API_KEY", "k-for-test")


# -- LP7: secret egress ------------------------------------------------------

def test_assert_no_raw_secrets_runs_before_every_call_including_the_repair(
        monkeypatch: pytest.MonkeyPatch) -> None:
    import autotester.providers.litellm_provider as mod

    seen: list[str] = []
    real = mod.assert_no_raw_secrets
    monkeypatch.setattr(mod, "assert_no_raw_secrets",
                        lambda text, values: (seen.append(text), real(text, values))[1])
    fake = install(monkeypatch, [reply("bad"), reply(json.dumps(GOOD))], response_schema=False,
                   function_calling=False)
    _with_key(monkeypatch)
    _provider("ollama/llama3.2", secrets=[SECRET]).judge("the prompt", Answer)
    assert len(seen) == len(fake.calls) == 2 and "the prompt" in seen[0]


def test_a_prompt_carrying_a_secret_never_reaches_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError) as info:
        _provider(secrets=[SECRET]).judge(f"log in with {SECRET}", Answer)
    assert fake.calls == [] and SECRET not in str(info.value)


def test_dotenv_values_are_guarded_without_any_option(tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text(f"PATHLYNKS_USER_PASSWORD={SECRET}\n", encoding="utf-8")
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError):
        _provider().judge(f"password is {SECRET}", Answer)
    assert fake.calls == []


def test_a_vendor_error_never_echoes_the_prompt_or_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    prompt = "PRIVATE-PROMPT-TEXT about a student"
    install(monkeypatch, [RuntimeError(f"bad request for {prompt} using key k-for-test")])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError) as info:
        _provider().judge(prompt, Answer)
    assert "PRIVATE-PROMPT-TEXT" not in str(info.value) and "k-for-test" not in str(info.value)
    assert "openai/gpt-4o" in str(info.value)


# -- LP8: credentials only from the environment, as explicit kwargs ----------

def test_key_and_base_become_explicit_kwargs_and_environ_is_untouched(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    monkeypatch.setenv("LITELLM_API_KEY", "k1")
    monkeypatch.setenv("LITELLM_API_BASE", "http://models.internal:8000/v1")
    before = dict(os.environ)
    _provider("openai/served-model").judge("g", Answer)
    assert fake.calls[0]["api_key"] == "k1"
    assert fake.calls[0]["api_base"] == "http://models.internal:8000/v1"
    assert dict(os.environ) == before


def test_ollama_reuses_ollama_base_url_and_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    provider = _provider("ollama/llama3.2")
    assert provider.available()
    provider.judge("g", Answer)
    assert fake.calls[0]["api_base"] == "http://localhost:11434" and "api_key" not in fake.calls[0]


# -- LP10: no telemetry, lazy import -----------------------------------------

def test_no_callbacks_are_registered_and_telemetry_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    _provider().judge("g", Answer)
    assert not (fake.success_callback or fake.failure_callback or fake.callbacks)
    assert not getattr(fake, "telemetry", False)


def test_the_real_pinned_sdk_is_quiet_after_the_provider_loads_it() -> None:
    """LL10 against the real package, not the fake: telemetry False, no callback list
    non-empty, and not one socket connect while it is imported (the pinned version has no
    `litellm.telemetry` switch of its own; the provider sets the attribute so it reads False)."""
    code = chr(10).join([
        "import socket",
        "def refuse(*a, **k): raise AssertionError('network touched')",
        "socket.socket.connect = refuse",
        "from autotester.providers.litellm_provider import LiteLLMProvider",
        "LiteLLMProvider(model='openai/gpt-4o').available()",
        "import litellm",
        "assert litellm.telemetry is False",
        "assert not (litellm.success_callback or litellm.failure_callback or litellm.callbacks)",
        "print('quiet')"])
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=240)
    assert done.returncode == 0 and "quiet" in done.stdout, done.stderr[-800:]


def test_importing_providers_does_not_import_litellm() -> None:
    code = "import sys, autotester.providers; assert 'litellm' not in sys.modules"
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr


# -- LP11 + clear unavailability --------------------------------------------

def test_available_needs_a_model_and_a_credential_or_an_endpoint(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [], missing_keys=["OPENAI_API_KEY"])
    assert LiteLLMProvider().available() is False                 # no model
    assert _provider().available() is False                       # model, no key
    monkeypatch.setenv("LITELLM_API_KEY", "k")
    assert _provider().available() is True                        # model + key
    monkeypatch.delenv("LITELLM_API_KEY")
    monkeypatch.setenv("LITELLM_API_BASE", "http://h/v1")
    assert _provider().available() is True                        # model + endpoint
    assert fake.calls == []


def test_a_missing_key_is_a_clear_error_naming_the_key_and_makes_no_call(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [], missing_keys=["OPENAI_API_KEY"])
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        _provider().judge("g", Answer)
    assert fake.calls == []


def test_no_model_configured_says_how_to_set_one(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [])
    with pytest.raises(ProviderError, match="AUTOTESTER_MODEL"):
        LiteLLMProvider().act("p", Answer)
    assert fake.calls == []


def test_a_call_without_a_schema_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError, match="schema"):
        _provider().act("p", None)


# -- LL5 (stage guard first, provider guard second), LL8, LL11, LL12 ----------

def test_the_stage_guard_fires_before_the_provider_is_ever_reached(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.browser.secrets import SecretStore
    from autotester.schema.enums import Outcome, Result
    from autotester.schema.project import Project, SecretRef
    from autotester.schema.run import RawResult
    from autotester.schema.verdict import Criterion, Rubric
    from autotester.stages.grade import grade

    (tmp_path / ".env").write_text(f"DEMO_PASSWORD={SECRET}\n", encoding="utf-8")
    project = Project(slug="demo", name="Demo", base_url="https://demo.test",
                      allowed_domains=["demo.test"],
                      secrets=[SecretRef(key="DEMO_PASSWORD", domains=["demo.test"])])
    secrets = SecretStore.load(project, tmp_path / ".env")
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    _with_key(monkeypatch)
    rubric = Rubric(id="rub_x", case_id="case_x",
                    criteria=[Criterion(id="c1", text=f"evidence shows {SECRET}")])
    verdict = grade(rubric, RawResult(case_id="case_x", outcome=Outcome.COMPLETED), "run_1",
                    _provider(), secrets=secrets)
    assert verdict.result is Result.BLOCKED and fake.calls == []  # BLOCKED, not a ProviderError


def test_an_exported_vendor_key_is_guarded_though_it_is_not_in_dotenv(
        monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [reply(json.dumps(GOOD))])
    monkeypatch.setenv("OPENAI_API_KEY", "sk-exported-canary-1234567890")
    with pytest.raises(ProviderError) as info:
        _provider().judge("my key is sk-exported-canary-1234567890", Answer)
    assert fake.calls == [] and "canary" not in str(info.value)


def test_neither_the_key_nor_the_endpoint_appears_in_an_error(
        monkeypatch: pytest.MonkeyPatch) -> None:
    base = "http://user:pw-canary@models.internal:8000/v1"
    install(monkeypatch, [RuntimeError(f"cannot reach {base} with key k-canary-key")])
    monkeypatch.setenv("LITELLM_API_KEY", "k-canary-key")
    monkeypatch.setenv("LITELLM_API_BASE", base)
    with pytest.raises(ProviderError) as info:
        _provider("openai/served").judge("g", Answer)
    assert no_network, "the real SDK never reached the socket guard"
    text = str(info.value)
    assert "canary" not in text and "models.internal" not in text


def test_an_exported_vendor_key_echoed_by_a_vendor_error_is_withheld(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """AT-790 (LL8): a vendor error that echoes a vendor-native key (here a Gemini
    `?key=` URL) must not reach the ProviderError; only LITELLM_* was withheld."""
    canary = "AIza-EXPORTED-CANARY-999"
    install(monkeypatch, [RuntimeError(f"404 for https://vendor.test/v1/models?key={canary}")])
    _with_key(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", canary)
    with pytest.raises(ProviderError) as info:
        _provider("gemini/gemini-2.5-pro").judge("g", Answer)
    assert canary not in str(info.value) and "gemini/gemini-2.5-pro" in str(info.value)


def test_a_dotenv_value_echoed_by_a_vendor_error_is_withheld(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AT-790 (LL8): any `.env` value, not only the LITELLM_* pair, is withheld."""
    canary = "sk-ant-DOTENV-CANARY-777"
    (tmp_path / ".env").write_text(f"ANTHROPIC_API_KEY={canary}\n", encoding="utf-8")
    install(monkeypatch, [RuntimeError(f"auth failed for key {canary}")])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError) as info:
        _provider("anthropic/claude-sonnet-4-5").judge("g", Answer)
    assert canary not in str(info.value)


def test_an_extra_secret_echoed_by_a_vendor_error_is_withheld(
        monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [RuntimeError(f"rejected login {SECRET}")])
    _with_key(monkeypatch)
    with pytest.raises(ProviderError) as info:
        _provider(secrets=[SECRET]).judge("an unrelated prompt", Answer)
    assert SECRET not in str(info.value)


def test_unavailable_reason_names_the_model_and_the_variable_and_nothing_secret(
        monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [], missing_keys=["OPENAI_API_KEY"])
    reason = _provider().unavailable_reason()
    assert reason is not None and "litellm:openai/gpt-4o" in reason and "OPENAI_API_KEY" in reason
    monkeypatch.setenv("LITELLM_API_KEY", "k")
    assert _provider().unavailable_reason() is None


def test_a_test_that_forgets_the_fake_fails_loudly_instead_of_going_online(
        monkeypatch: pytest.MonkeyPatch, no_network: list[object]) -> None:
    """LL12: with no fake installed, the real SDK is reached and the first real socket
    connect raises the guard's error (surfaced inside the typed ProviderError)."""
    import sys

    monkeypatch.delitem(sys.modules, "litellm", raising=False)
    monkeypatch.setenv("LITELLM_MODE", "PRODUCTION")
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    monkeypatch.setenv("LITELLM_API_BASE", "http://203.0.113.7:9/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test-not-real-0000")
    with pytest.raises(ProviderError):
        _provider("openai/served").judge("g", Answer)
    assert no_network, "the real SDK never reached the socket guard"
    monkeypatch.delitem(sys.modules, "litellm", raising=False)
