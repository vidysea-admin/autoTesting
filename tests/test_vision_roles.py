"""Offline visual-role policy, exact receipts and explicit ensemble resolution."""
import json

import pytest
from litellm_fake import no_network  # noqa: F401

import autotester.providers as providers
from autotester.providers import vision_roles
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget, reserve_attempt
from autotester.providers.availability import AvailabilityFailure
from autotester.providers.base import ProviderError
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.ollama_cloud import DEEPSEEK, GLM
from autotester.providers.vision_roles import GEMINI_VISION_MODEL, VisionChainProvider
from autotester.schema.enums import SourceKind
from autotester.schema.project import Project, ProviderConfig

pytestmark = pytest.mark.usefixtures("no_network")


def project(**config):
    return Project(slug="demo", name="Demo", base_url="https://demo.test",
                   providers=ProviderConfig(**config))


def test_role_defaults_preserve_text_override_and_visual_fallback_opt_out(monkeypatch):
    monkeypatch.setenv("AUTOTESTER_MODEL", "ollama_chat/explicit-text")
    record = project()
    visual = providers.for_role(record, "vision")
    assert isinstance(visual, VisionChainProvider)
    assert visual.label == "vision-chain"
    assert visual.order() == [DEEPSEEK, GEMINI_VISION_MODEL]
    assert providers.for_role(record, "agent")._model == "ollama_chat/explicit-text"
    assert GLM not in visual.order()
    assert providers.for_role(project(vision="mock"), "vision").id == "mock"
    disabled = providers.for_role(project(vision_allow_gemini_fallback=False), "vision")
    assert disabled.order() == [DEEPSEEK]
    with pytest.raises(ValueError):
        ProviderConfig(vision_allow_gemini_fallback="false")
    with pytest.raises(ProviderError):
        VisionChainProvider(model=GLM)


def test_lazy_group_preserves_override_tags_all_ensemble_members_and_dedup(monkeypatch):
    asked = []

    def get(name, **options):
        asked.append((name, options))
        return name

    monkeypatch.setattr(providers, "get", get)
    record = project(vision="mock,anthropic,mock")
    assert providers.for_teaching_group(record, SourceKind.VIDEO) == ["mock", "anthropic"]
    assert asked == [("mock", {}), ("anthropic", {})]
    asked.clear()
    override = "litellm:ollama_chat/custom:cloud"
    assert providers.for_teaching_group(record, SourceKind.VIDEO, override=override) == ["litellm"]
    assert asked == [("litellm", {"model": "ollama_chat/custom:cloud"})]
    asked.clear()
    monkeypatch.setenv("AUTOTESTER_MODEL", "ollama_chat/text-only")
    assert providers.for_teaching_group(record, SourceKind.DOC) == ["litellm"]
    assert asked == [("litellm", {"model": "ollama_chat/text-only"})]
    with pytest.raises(ProviderError, match="ensemble"):
        providers.for_teaching(record, SourceKind.VIDEO)


def test_live_receipt_set_is_bound_and_tampering_never_becomes_capability(tmp_path, monkeypatch):
    path = vision_roles._RECEIPTS
    original = json.loads(path.read_bytes())
    assert set(vision_roles.checked_capabilities()) == {DEEPSEEK, GEMINI_VISION_MODEL}
    for change in ("answer", "prompt", "model", "physical", "duplicate"):
        record = json.loads(json.dumps(original))
        result = record["records"][0]["result"]
        if change == "answer":
            result["observed"]["images"][0]["left_shape"] = "triangle"
        elif change == "prompt":
            result["capability"]["prompt_sha256"] = "0"*64
        elif change == "model":
            result["capability"]["model"] = GLM
        elif change == "physical":
            result["attempts"] = []
        else:
            record["records"].append(record["records"][0])
        target = tmp_path/(change+".json")
        target.write_bytes(json.dumps(record).encode())
        monkeypatch.setattr(vision_roles, "_RECEIPTS", target)
        with pytest.raises(ProviderError, match="invalid"):
            vision_roles.checked_capabilities()


def test_vision_chain_falls_back_only_on_eligible_failure_and_keeps_global_budget(
        tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setattr(LiteLLMProvider, "available", lambda self: True)
    calls, error = [], [AvailabilityFailure("service")]

    def see_video(self, *args, **kwargs):
        calls.append(self._model)
        attempt, _ = reserve_attempt(self.label, "vision", 120)
        if self._model == DEEPSEEK:
            attempt.status = "failed"
            raise error[0]
        attempt.status = "succeeded"
        return ProviderConfig()

    monkeypatch.setattr(LiteLLMProvider, "see_video", see_video)
    chain = VisionChainProvider()
    with attempt_budget(4) as budget:
        result = chain.see_video(tmp_path/"neutral.mp4", "safe", ProviderConfig)
        assert isinstance(result, ProviderConfig)
    assert calls == [DEEPSEEK, GEMINI_VISION_MODEL] and len(budget.attempts) == 2
    assert chain.served == "litellm:"+GEMINI_VISION_MODEL
    assert "service" in chain.fallback_reasons[0]
    for refused in (ProviderError("privacy refused"), AttemptBudgetExhausted("global cap")):
        error[0], calls[:] = refused, []
        with pytest.raises(type(refused)):
            chain.see_video(tmp_path/"neutral.mp4", "safe", ProviderConfig)
        assert calls == [DEEPSEEK] and chain.served is None
    calls.clear()
    with attempt_budget(0), pytest.raises(AttemptBudgetExhausted):
        chain.see_video(tmp_path/"neutral.mp4", "safe", ProviderConfig)
    assert calls == [DEEPSEEK]


def test_actual_parser_preserves_distinct_ensemble_model_tags_and_custom_settings():
    first = "litellm:ollama_chat/custom:cloud"
    second = "litellm:gemini/custom:tag"
    assert providers.parse_spec(first) == ("litellm", {"model": "ollama_chat/custom:cloud"})
    record = project(vision=f"{first},{second},{first},vision-chain",
                     agent="mock", judge="anthropic", vision_allow_gemini_fallback=False)
    original = record.model_dump()
    group = providers.for_teaching_group(record, SourceKind.VIDEO)
    assert [p.label for p in group] == [first, second, "vision-chain"]
    assert group[0]._model == "ollama_chat/custom:cloud"
    assert group[1]._model == "gemini/custom:tag"
    assert group[2].order() == [DEEPSEEK]
    override = providers.for_teaching_group(record, SourceKind.VIDEO, override=second)
    assert [p.label for p in override] == [second]
    assert record.model_dump() == original
    with pytest.raises(ProviderError, match="ensemble"):
        providers.for_role(record, "vision")
    for invalid in ("unknown:model", "litellm:", "litellm:https://invalid.test"):
        with pytest.raises(ProviderError):
            providers.for_teaching_group(record, SourceKind.VIDEO, override=f"{first},{invalid}")
