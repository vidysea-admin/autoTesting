"""Offline physical request budgets, repair/fallback accounting and unknown usage."""
import json
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

import pytest
from litellm_fake import install, no_network, reply  # noqa: F401
from pydantic import BaseModel, ValidationError

from autotester.core.trace import TraceWriter
from autotester.providers.attempts import (
    AttemptBudgetExhausted,
    attempt_budget,
    reserve_attempt,
)
from autotester.providers.isolated import IsolatedProvider
from autotester.providers.litellm_provider import LiteLLMProvider
from autotester.providers.model_chain import ModelChainProvider
from autotester.schema.provider_attempt import ProviderAttempt
from autotester.stages.video_review import ReviewRefused, provider_cost
from autotester.store.project_store import ProjectStore
from autotester.ui.routes_report import _trace_card

pytestmark = pytest.mark.usefixtures("no_network")


class AttemptAnswer(BaseModel):
    ok: bool


def test_attempt_count_reserves_before_repair_and_fallback(monkeypatch, tmp_path):
    fake = install(monkeypatch, [reply("invalid"), TimeoutError("oops"), reply('{"ok":true}')])
    monkeypatch.setenv("OLLAMA_API_KEY", "fake-value")
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    chain = ModelChainProvider()
    with attempt_budget(2) as budget, pytest.raises(AttemptBudgetExhausted, match="max_calls"):
        chain.act("prompt", AttemptAnswer)
    assert len(fake.calls) == budget.used == 2
    assert [r.status for r in budget.attempts] == ["succeeded", "failed"]
    assert chain.served is None
    assert chain.usage[0].calls == 2 and chain.usage[0].failed_calls == 1
    assert chain.usage[0].input_tokens is None


def test_failed_attempts_trace_unknown_usage_and_preserve_winner(monkeypatch, tmp_path):
    fake = install(monkeypatch, [TimeoutError("secret-content"), reply('{"ok":true}')])
    monkeypatch.setenv("OLLAMA_API_KEY", "secret-content")
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    chain = ModelChainProvider()
    chain.trace = TraceWriter(tmp_path / "trace.jsonl", "run-1")
    with attempt_budget(3) as budget:
        assert chain.judge("private prompt", AttemptAnswer).ok
    assert len(fake.calls) == budget.used == 2
    assert chain.served.endswith("deepseek-v4.1-flash")
    assert [(u.calls, u.failed_calls) for u in chain.usage] == [(1, 1), (1, 0)]
    assert chain.usage[0].input_tokens is chain.usage[0].output_tokens is None
    rows = [json.loads(s) for s in (tmp_path / "trace.jsonl").read_text().splitlines()]
    assert rows[0]["failed"] and rows[0]["input_tokens"] is rows[0]["cost"] is None
    assert rows[1]["input_tokens"] == 11 and not rows[1]["failed"]
    assert "secret-content" not in str(rows) and "private prompt" not in str(rows)
    with pytest.raises(ReviewRefused, match="unknown"):
        provider_cost(chain)
    store = ProjectStore("demo", tmp_path)
    store.paths.run_trace("r1").parent.mkdir(parents=True, exist_ok=True)
    store.paths.run_trace("r1").write_text((tmp_path / "trace.jsonl").read_text())
    assert "unknown" in _trace_card(store, "r1")
    isolated = IsolatedProvider(lambda: chain)
    isolated._merge_usage([u.model_dump() for u in chain.usage])
    assert isolated.usage[0].calls == 2 and isolated.usage[0].failed_calls == 1
    assert isolated.usage[0].input_tokens is None
    unknown = reply('{"ok":true}')
    unknown.usage = None
    fake.responses.append(unknown)
    with attempt_budget(1) as missing:
        assert chain.act("again", AttemptAnswer).ok
    assert missing.attempts[0].input_tokens is None


def test_nested_budget_rejects_atomically_and_context_restores():
    with attempt_budget(2) as outer:
        with attempt_budget(0), pytest.raises(AttemptBudgetExhausted):
            reserve_attempt("fake", "judge", 120)
        assert outer.used == 0
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(copy_context().run, reserve_attempt, "fake", "judge", 120).result()
        assert outer.used == 1
    with attempt_budget(1) as fresh:
        reserve_attempt("fake", "judge", 120)
        assert fresh.used == 1
    with pytest.raises(ValidationError):
        ProviderAttempt(provider="fake", role="judge", payload="forbidden")
    for invalid in (-1, True, 1.5):
        with pytest.raises(ValueError), attempt_budget(invalid):
            pass


def test_deadline_caps_transport_and_exhausts_before_next_request(monkeypatch, tmp_path):
    fake = install(monkeypatch, [reply('{"ok":true}')])
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.setenv("OLLAMA_API_KEY", "fake-key")
    provider = LiteLLMProvider(model="ollama_chat/glm-5.3-flash")
    with (pytest.raises(AttemptBudgetExhausted, match="wall_clock_s"),
          attempt_budget(2, wall_clock_s=7) as budget):
        assert provider.act("prompt", AttemptAnswer).ok
        assert 0 < fake.calls[0]["timeout"] <= 7
        budget.deadline = 0
        provider.act("prompt", AttemptAnswer)
    assert len(fake.calls) == 1
    assert fake.calls[0]["num_retries"] == 0
    for invalid in (-1, float("inf"), float("nan")):
        with pytest.raises(ValueError), attempt_budget(1, invalid):
            pass
