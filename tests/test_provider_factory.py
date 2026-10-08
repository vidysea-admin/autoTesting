"""T-202: `parse_spec`, the one default-provider factory, and the two call sites
that used to hardcode `LangChainFallbackProvider()` (ui/routes_runs.py,
ui/routes_learn.py). No network: the litellm module is a fake or never imported."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from litellm_fake import install
from test_coverage_wiring import _a_case, _project

import autotester.providers as providers
from autotester.providers.base import ProviderError
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.schema.enums import ProviderRole
from autotester.schema.flowspec import Screen
from autotester.schema.project import Project, ProviderConfig
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

SRC = Path(providers.__file__).resolve().parents[1]


def _project_with(**roles: str) -> Project:
    return Project(slug="demo", name="Demo", base_url="https://demo.test",
                   allowed_domains=["demo.test"], providers=ProviderConfig(**roles))


# -- LP1: the spec grammar and the registry ---------------------------------

def test_registry_resolves_litellm_with_a_round_trippable_label(
        monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    provider = providers.get("litellm", model="ollama/llama3.2")
    assert isinstance(provider, LiteLLMProvider)
    assert provider.label == "litellm:ollama/llama3.2"


@pytest.mark.parametrize(("spec", "expected"), [
    ("litellm:openai/gpt-4o", ("litellm", {"model": "openai/gpt-4o"})),
    ("litellm:ollama/llama3:8b", ("litellm", {"model": "ollama/llama3:8b"})),
    ("gemini:gemini-3.6-flash", ("gemini", {"model": "gemini-3.6-flash"})),
    ("gemini", ("gemini", {})),
    ("langchain-fallback", ("langchain-fallback", {})),
    ("gemini,anthropic", ("gemini,anthropic", {})),   # the vision ensemble list, unchanged
])
def test_parse_spec(spec: str, expected: tuple[str, dict[str, Any]]) -> None:
    assert providers.parse_spec(spec) == expected


@pytest.mark.parametrize("spec", [
    "litellm:", "litellm:https://user:pw@host/v1", "litellm:openai/gpt-4o@user:pw", "",
    "litellm:openai/gpt-4o user pw", "nosuchprovider-user:model", "gemini,nosuch-user",
])
def test_parse_spec_rejects_empty_models_and_embedded_credentials_without_echoing(
        spec: str) -> None:
    with pytest.raises(ProviderError) as info:
        providers.parse_spec(spec)
    message = str(info.value)
    assert "pw" not in message and "user" not in message.replace("provider", "")


# -- the factory ------------------------------------------------------------

def test_factory_default_is_the_langchain_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOTESTER_MODEL", raising=False)
    assert isinstance(providers.for_role(), LangChainFallbackProvider)
    assert isinstance(providers.for_role(_project_with(), "judge"),
                      LangChainFallbackProvider)


def test_factory_honours_autotester_model_when_the_project_is_on_defaults(
        monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    monkeypatch.setenv("AUTOTESTER_MODEL", "gemini/gemini-2.5-pro")
    chosen = providers.for_role(_project_with(), "judge")
    assert isinstance(chosen, LiteLLMProvider) and chosen.label == "litellm:gemini/gemini-2.5-pro"


def test_a_project_spec_beats_the_env_default_and_is_per_role(
        monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    monkeypatch.setenv("AUTOTESTER_MODEL", "gemini/gemini-2.5-pro")
    project = _project_with(judge="litellm:openai/gpt-4o")
    assert providers.for_role(project, "judge").label == "litellm:openai/gpt-4o"
    assert providers.for_role(project, "agent").label == "litellm:gemini/gemini-2.5-pro"
    assert providers.for_role(project, ProviderRole.JUDGE).label == "litellm:openai/gpt-4o"


def test_a_bare_project_id_still_resolves_through_the_registry(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOTESTER_MODEL", raising=False)
    assert providers.for_role(_project_with(agent="anthropic"), "agent").id == "anthropic"


def test_the_factory_serves_agent_and_judge_only() -> None:
    with pytest.raises(ProviderError, match="vision"):
        providers.for_role(_project_with(), "vision")


# -- LP2: the two call sites go through the factory -------------------------

def _calls_in(module_file: str) -> set[str]:
    folder = "stages" if module_file == "run_launcher.py" else "ui"
    tree = ast.parse((SRC / folder / module_file).read_text(encoding="utf-8"))
    return {n.func.id for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


@pytest.mark.parametrize("module_file", ["run_launcher.py", "routes_learn.py"])
def test_neither_route_constructs_the_langchain_provider_itself(module_file: str) -> None:
    calls = _calls_in(module_file)
    assert "LangChainFallbackProvider" not in calls
    assert "for_role" in calls


def _save(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **roles: str) -> None:
    """A project `demo` with one case and the given per-role provider specs."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    for key in ("GOOGLE_API_KEY", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    store = ProjectStore("demo", tmp_path)
    store.save_project(_project_with(**roles))
    _a_case(store)


def _run_refusal(client: TestClient) -> str:
    response = client.post("/projects/demo/run")
    assert response.status_code == 400, response.text
    return response.text


def test_ll2_a_project_judge_spec_builds_the_litellm_provider_with_that_model(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [], missing_keys=["OPENAI_API_KEY"])
    monkeypatch.setenv("AUTOTESTER_MODEL", "ignored/for-this-project")
    _save(tmp_path, monkeypatch, judge="litellm:openai/gpt-4o")
    text = _run_refusal(TestClient(app))
    assert "litellm:openai/gpt-4o" in text and "OPENAI_API_KEY" in text  # LL11: model + variable


def test_ll2_the_server_model_applies_when_the_project_is_on_defaults(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [], missing_keys=["GEMINI_API_KEY"])
    monkeypatch.setenv("AUTOTESTER_MODEL", "gemini/gemini-2.5-pro")
    _save(tmp_path, monkeypatch)
    text = _run_refusal(TestClient(app))
    assert "litellm:gemini/gemini-2.5-pro" in text and "GEMINI_API_KEY" in text


def test_ll2_with_neither_the_run_path_is_the_langchain_fallback_as_today(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    _save(tmp_path, monkeypatch)
    text = _run_refusal(TestClient(app))
    assert "no AI provider is configured" in text and "litellm" not in text


def test_a_malformed_project_spec_is_a_400_not_a_500(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    _save(tmp_path, monkeypatch, judge="litellm:https://user:pw-canary@host/v1")
    text = _run_refusal(TestClient(app))
    assert "pw-canary" not in text


def test_trigger_run_asks_the_factory_for_the_judge_of_this_project(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import autotester.stages.run_launcher as routes_runs_module

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _project(tmp_path, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    _a_case(store)
    asked: list[tuple[str, str]] = []

    class _Unavailable:
        def available(self) -> bool:
            return False

    def fake_factory(project: Project, role: str) -> Any:
        asked.append((project.slug, str(role)))
        return _Unavailable()

    monkeypatch.setattr(routes_runs_module, "for_role", fake_factory)
    response = TestClient(app).post("/projects/demo/run")
    assert response.status_code == 400 and "no AI provider" in response.text
    assert asked == [("demo", "judge")]


def test_generate_cases_asks_the_factory_for_the_agent_of_this_project(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import autotester.ui.routes_learn as routes_learn_module

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    _project(tmp_path, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    asked: list[tuple[str, str]] = []

    class _Unavailable:
        def available(self) -> bool:
            return False

    def fake_factory(project: Project, role: str) -> Any:
        asked.append((project.slug, str(role)))
        return _Unavailable()

    monkeypatch.setattr(routes_learn_module, "for_role", fake_factory)
    response = TestClient(app).post("/projects/demo/cases/generate")
    assert "No model provider configured" in response.text
    assert asked == [("demo", "agent")]


@pytest.mark.parametrize("source", ["server", "constructor", "project-list"])
def test_factory_and_direct_constructor_refuse_malformed_inputs_without_echoing(
        monkeypatch, source):
    fake = install(monkeypatch, [])
    bad = "https://user:secret-canary@host/v1"
    with pytest.raises(ProviderError) as error:
        if source == "server":
            monkeypatch.setenv("AUTOTESTER_MODEL", bad)
            providers.for_role(_project_with())
        elif source == "constructor":
            LiteLLMProvider(model=bad)
        else:
            providers.for_role(_project_with(agent="gemini,anthropic"), "agent")
    assert "secret-canary" not in str(error.value) and fake.calls == []


@pytest.mark.parametrize("source", ["server", "project"])
def test_malformed_learn_configuration_returns_400_without_persistence(
        tmp_path, monkeypatch, source):
    fake = install(monkeypatch, [])
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _project(tmp_path, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    bad = "https://user:learn-canary@host/v1"
    if source == "server":
        monkeypatch.setenv("AUTOTESTER_MODEL", bad)
    else:
        project = store.load_project()
        project.providers.agent = f"litellm:{bad}"
        store.save_project(project)
    response = TestClient(app).post("/projects/demo/cases/generate")
    assert response.status_code == 400 and "/settings/providers" in response.text
    assert "learn-canary" not in response.text and store.list_cases() == [] and fake.calls == []
