"""D-089 item 2 / T-177 AF4: a hung provider cannot outlive the deadline; the child is killed."""

from __future__ import annotations

import functools
import time

import pytest
from isolated_fake import Answer, scripted
from pydantic import BaseModel

from autotester.providers.base import Provider, ProviderError
from autotester.providers.isolated import IsolatedProvider, ProviderDeadline, _schema_ref

FAST = 60.0  # generous: spawn re-imports the package; only the hang tests rely on a short bound


def make(mode: str = "ok", **kw: float) -> IsolatedProvider:
    return IsolatedProvider(functools.partial(scripted, mode), **kw)


def test_an_answer_and_its_usage_cross_the_process_boundary() -> None:
    iso = make(deadline_s=FAST)
    assert iso.act("hi") == "echo:hi"
    assert isinstance(iso, Provider) and iso.available()
    assert [(u.role, u.calls, u.input_tokens) for u in iso.usage] == [("agent", 1, 7)]
    assert not iso.last_process.is_alive()


def test_an_importable_schema_comes_back_as_that_model() -> None:
    out = make(deadline_s=FAST).act("question", schema=Answer)
    assert out == Answer(text="echo:question")


def test_a_dynamic_schema_is_sent_as_json_schema_text() -> None:
    from pydantic import create_model

    dynamic: type[BaseModel] = create_model("Dyn", x=(int, ...))
    assert _schema_ref(dynamic) is None
    out = make(deadline_s=FAST).act("q", schema=dynamic)
    assert "JSON schema" in out and '"x"' in out  # the child echoed the schema instruction


def test_a_provider_error_in_the_child_is_a_provider_error_here() -> None:
    with pytest.raises(ProviderError, match="quota exceeded") as caught:
        make("boom", deadline_s=FAST).act("hi")
    assert not isinstance(caught.value, ProviderDeadline)


def test_a_hung_provider_returns_inside_the_deadline_and_the_child_is_dead() -> None:
    iso = make("hang", deadline_s=8.0)
    started = time.monotonic()
    with pytest.raises(ProviderDeadline, match="deadline 8s reached"):
        iso.act("hi")
    assert time.monotonic() - started < 8.0 + 6.0  # the bound, plus kill grace; not the 120 s hang
    assert not iso.last_process.is_alive()


def test_a_bound_wall_clock_caps_the_call_below_the_default() -> None:
    now = [100.0]
    iso = make("hang", deadline_s=FAST, clock=lambda: now[0])
    iso.bind_deadline(100.0 + 6.0)
    with pytest.raises(ProviderDeadline, match="deadline 6s reached"):
        iso.act("hi")
    iso.bind_deadline(now[0] - 1)  # already past: no child is even started
    iso.last_process = None
    with pytest.raises(ProviderDeadline, match="already reached"):
        iso.act("hi")
    assert iso.last_process is None


def test_other_roles_stay_unsupported() -> None:
    from autotester.providers.base import Unsupported

    with pytest.raises(Unsupported):
        make().judge("p", Answer)
