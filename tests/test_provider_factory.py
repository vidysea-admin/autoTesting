"""T-202: `parse_spec`, the one default-provider factory, and the two call sites
that used to hardcode `LangChainFallbackProvider()` (ui/routes_runs.py,
ui/routes_learn.py). No network: the litellm module is a fake or never imported."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from litellm_fake import install, no_network  # noqa: F401  (autouse via pytestmark)
from test_coverage_wiring import _a_case, _project
from test_expand_cli import _seed, root  # noqa: F401
from test_ui_runs_queue import held  # noqa: F401
from typer.testing import CliRunner

import autotester.providers as providers
from autotester.cli import app as cli_app
from autotester.providers.base import ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.model_chain import ModelChainProvider
from autotester.providers.vision_roles import VisionChainProvider
from autotester.schema.enums import ProviderRole
from autotester.schema.flowspec import Screen
from autotester.schema.project import Project, ProviderConfig
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

pytestmark = pytest.mark.usefixtures("no_network")   # LL12: a forgotten fake fails loudly
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

def test_factory_default_is_the_model_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOTESTER_MODEL", raising=False)
    assert isinstance(providers.for_role(), ModelChainProvider)
    assert isinstance(providers.for_role(_project_with(), "judge"),
                      ModelChainProvider)


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


def test_the_factory_resolves_the_receipt_bound_visual_role() -> None:
    assert isinstance(providers.for_role(_project_with(), "vision"), VisionChainProvider)


# -- LP2: the two call sites go through the factory -------------------------

def _calls_in(module_file: str) -> set[str]:
    tree = ast.parse((SRC / "ui" / module_file).read_text(encoding="utf-8"))
    return {n.func.id for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}


@pytest.mark.parametrize("module_file", ["routes_runs.py", "routes_learn.py"])
def test_neither_route_constructs_the_langchain_provider_itself(module_file: str) -> None:
    calls = _calls_in(module_file)
    assert "LangChainFallbackProvider" not in calls
    assert "for_role" in calls


def _save(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **roles: str) -> None:
    """A project `demo` with one case and the given per-role provider specs."""
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    for key in ("GOOGLE_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY"):
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


def test_ll2_with_neither_the_run_path_is_the_model_chain(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [], missing_keys=["OLLAMA_API_KEY"])
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
    import autotester.ui.routes_runs as routes_runs_module

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


# -- LL11: an unavailable LiteLLM provider is refused the same way on every surface ------------

def test_a_malformed_spec_on_the_learn_route_is_a_refusal_page_not_a_500(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, [])
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = _project(tmp_path, screens=[Screen(id="s1", name="Home", url_pattern="/")])
    store.save_project(store.load_project().model_copy(
        update={"providers": ProviderConfig(agent="litellm:https://user:pw-canary@host/v1")}))
    response = TestClient(app).post("/projects/demo/cases/generate")
    assert "No model provider configured" in response.text and "pw-canary" not in response.text


def test_ll11_a_queued_run_whose_litellm_judge_lost_its_key_ends_refused_with_no_browser(
        held, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    import autotester.ui.routes_runs as routes_runs

    client, jobs, ran = held
    client.post("/projects/demo/run", follow_redirects=False)        # gates passed, now queued
    install(monkeypatch, [], missing_keys=["OPENAI_API_KEY"])
    store = ProjectStore("demo")
    store.save_project(store.load_project().model_copy(
        update={"providers": ProviderConfig(judge="litellm:openai/gpt-4o")}))
    monkeypatch.setattr(routes_runs, "for_role", providers.for_role)   # the real factory
    jobs.pop()()
    page = client.get("/projects/demo/report").text
    assert ran == [] and "refused" in page
    assert "litellm:openai/gpt-4o" in page and "OPENAI_API_KEY" in page


def test_ll11_the_cli_exits_non_zero_with_the_same_one_line_reason(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    install(monkeypatch, [], missing_keys=["OPENAI_API_KEY"])
    _seed(root)
    result = CliRunner().invoke(cli_app, ["expand", "demo", "--provider", "litellm:openai/gpt-4o"])
    assert result.exit_code == 1 and "Traceback" not in result.output
    assert "litellm:openai/gpt-4o" in result.output and "OPENAI_API_KEY" in result.output
    assert len(result.output.strip().splitlines()) == 1
    assert "model call failed" not in result.output      # refused BEFORE any model call


def test_ll11_the_cli_refuses_a_malformed_spec_without_echoing_it(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    install(monkeypatch, [])
    _seed(root)
    result = CliRunner().invoke(
        cli_app, ["expand", "demo", "--provider", "litellm:https://user:pw-canary@host/v1"])
    assert result.exit_code == 1 and "pw-canary" not in result.output
    assert "Traceback" not in result.output
