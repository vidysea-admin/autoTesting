"""BROWSER_USE_BACKEND: browser-use (MIT) as the `ActuatorBackend` for unknown screens (T-177).

Contract: qa/contracts/agent-fallback.md AF3/AF6. Two seams keep it inside the system's rules:

- the model: browser-use wants a chat model; `ProviderChatModel` is one, backed by a
  `providers.base.Provider` (`Provider.act`), so no vendor client exists outside `providers/`
  and every prompt passes the caller's secret guard first (AF6);
- the actions: browser-use plans each step's actions, then calls `register_new_step_callback`
  BEFORE running them. That callback translates them to `FallbackAction`s and hands each to the
  adapter's `vet`; a refusal stops the agent before the action runs (AF3). An action browser-use
  offers that has no mapping here is refused, never guessed at.

browser-use drives its own async Playwright, so it attaches to the already-open browser over CDP
(`BrowserSession.cdp_url`); it cannot take the sync `BrowserSession.page`.

D-075: nothing leaves the box. browser-use 0.5.9 has two network-on-use switches, both read from
the environment and both defaulting to ON: `ANONYMIZED_TELEMETRY` (PostHog, eu.i.posthog.com) and
`BROWSER_USE_CLOUD_SYNC` (agent events to api.browser-use.com; it follows the telemetry switch
unless set). They are FORCED off below at import, before browser-use is ever imported, whatever
the user's environment says. Default extensions (a download from the Chrome store) are also
off. browser-use also calls
`load_dotenv()` in six of its modules at import, which would copy the repo `.env` (every
project's credentials) into `os.environ`: `PYTHON_DOTENV_DISABLED=1` stops exactly that call and
leaves AutoTester's own `core/env.py` loader (`dotenv_values`) untouched.

Guards: the model seam takes a REQUIRED secret `guard` (browser-use puts the page URL and field
values in its prompts); `for_session` defaults it to the session's secret scrubber. And X7: the
page each step starts on (where the previous action landed) is re-checked before it acts.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urljoin

from autotester.providers.base import Provider
from autotester.schema.agent_fallback import FallbackAction, FallbackActionKind
from autotester.stages.agent_actuator import (
    ActionRefused,
    ActuatorError,
    BoundExhausted,
    Vet,
)

K = FallbackActionKind
_NAME_ATTRS = ("aria-label", "title", "placeholder", "value", "name")


NO_NETWORK_ENV = {"ANONYMIZED_TELEMETRY": "false", "BROWSER_USE_CLOUD_SYNC": "false",
                  "PYTHON_DOTENV_DISABLED": "1"}
PROFILE = {"enable_default_extensions": False}  # kwargs for browser_use.BrowserSession


def _load() -> None:
    os.environ.update(NO_NETWORK_ENV)  # forced, not setdefault: the user's env must not win


_load()  # at import, before any `browser_use` import (they are all lazy, below)


class ProviderChatModel:
    """browser-use's `BaseChatModel`, answered by a `Provider` (text only; images are dropped)."""

    model = "provider-seam"
    _verified_api_keys = True  # there is no key: the Provider owns its own credentials

    def __init__(self, provider: Provider, guard: Callable[[str], str]) -> None:
        self._provider, self._guard = provider, guard

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        return handler(Any)  # browser-use validates its settings with this: accept any object

    @property
    def provider(self) -> str:
        return self._provider.id

    @property
    def name(self) -> str:
        return self._provider.label

    @property
    def model_name(self) -> str:
        return self.model

    async def ainvoke(self, messages: list[Any], output_format: type | None = None) -> Any:
        _load()
        from browser_use.llm.views import ChatInvokeCompletion

        prompt = self._guard("\n\n".join(
            f"[{m.role}]\n{getattr(m, 'text', '') or ''}" for m in messages))
        answer = await asyncio.to_thread(self._provider.act, prompt, schema=output_format)
        if output_format is None:
            completion: Any = answer if isinstance(answer, str) else str(answer)
        else:
            completion = (answer if isinstance(answer, output_format)
                          else output_format.model_validate(answer))
        return ChatInvokeCompletion(completion=completion, usage=None)


def _node_name(node: Any) -> str:
    attrs = getattr(node, "attributes", {}) or {}
    text = node.get_all_text_till_next_clickable_element().strip()
    return " ".join(p for p in [text, *(attrs.get(k, "") for k in _NAME_ATTRS)] if p)


def _role_of(node: Any) -> str:
    tag = getattr(node, "tag_name", "")
    return {"a": "link", "input": "textbox", "textarea": "textbox", "select": "combobox"
            }.get(tag, "button")


def _element(kind: K, params: dict, state: Any) -> FallbackAction:
    node = state.selector_map.get(params.get("index"))
    if node is None:
        return FallbackAction(kind=kind, target="")
    attrs = getattr(node, "attributes", {}) or {}
    href = attrs.get("href")
    submit = attrs.get("type") == "submit" or getattr(node, "tag_name", "") == "form"
    return FallbackAction(
        kind=kind, target=_node_name(node), role=_role_of(node),
        value=params.get("text"), is_form_submit=submit,
        url=urljoin(state.url, href) if href and kind is K.CLICK else None)


_MAPPERS: dict[str, Callable[[dict, Any], FallbackAction]] = {
    "go_to_url": lambda p, s: FallbackAction(kind=K.NAVIGATE, url=p.get("url")),
    "search_google": lambda p, s: FallbackAction(
        kind=K.NAVIGATE, url="https://www.google.com/search"),
    "go_back": lambda p, s: FallbackAction(kind=K.BACK),
    "wait": lambda p, s: FallbackAction(kind=K.WAIT),
    "scroll": lambda p, s: FallbackAction(kind=K.SCROLL),
    "scroll_to_text": lambda p, s: FallbackAction(kind=K.SCROLL),
    "extract_structured_data": lambda p, s: FallbackAction(kind=K.WAIT),
    "send_keys": lambda p, s: FallbackAction(kind=K.PRESS_KEY, value=p.get("keys")),
    "click_element_by_index": lambda p, s: _element(K.CLICK, p, s),
    "input_text": lambda p, s: _element(K.FILL, p, s),
    "select_dropdown_option": lambda p, s: _element(K.SELECT, p, s),
    "get_dropdown_options": lambda p, s: _element(K.WAIT, p, s),
    "upload_file": lambda p, s: _element(K.UPLOAD, p, s),
}


def to_actions(output: Any, state: Any) -> Iterator[FallbackAction]:
    """browser-use's planned actions as guard-readable ones; an unmapped action is refused."""
    for model in output.action:
        for name, params in model.model_dump(exclude_none=True).items():
            if name == "done":
                continue
            mapper = _MAPPERS.get(name)
            if mapper is None:
                raise ActionRefused(f"browser-use action {name!r} has no guard mapping")
            yield mapper(params or {}, state)


class BrowserUseBackend:
    """Drive the open browser at `cdp_url` with browser-use, vetting every action first."""

    def __init__(self, provider: Provider, cdp_url: str, guard: Callable[[str], str],
                 allowed_domains: list[str] | None = None) -> None:
        self.provider, self.cdp_url, self.guard = provider, cdp_url, guard
        self.allowed_domains = allowed_domains or []

    @classmethod
    def for_session(cls, provider: Provider, session: Any,
                    guard: Callable[[str], str] | None = None) -> BrowserUseBackend:
        """Attach to the browser `session` already opened (D-075); never launch another.
        `guard` defaults to the session's secret scrubber, never to the identity function."""
        cdp_url = session.cdp_url
        if cdp_url is None:
            raise ActuatorError("the session exposes no CDP endpoint; "
                                "construct BrowserSession(..., expose_cdp=True)")
        domains = [f"*.{d}" for d in session.project.allowed_domains]  # browser-use's own check
        return cls(provider, cdp_url, guard or session.secrets.redactor().scrub, domains)

    def run(self, task: str, vet: Vet, *, max_steps: int, timeout_s: float) -> object:
        with ThreadPoolExecutor(max_workers=1) as pool:  # never inside a caller's running loop
            return pool.submit(asyncio.run, self._drive(task, vet, max_steps, timeout_s)).result()

    def _profile(self) -> dict[str, Any]:
        domains = {"allowed_domains": self.allowed_domains} if self.allowed_domains else {}
        return {**PROFILE, **domains}

    async def _drive(self, task: str, vet: Vet, max_steps: int, timeout_s: float) -> dict:
        _load()
        from browser_use import Agent
        from browser_use import BrowserSession as BuSession

        taken: list[FallbackAction] = []
        stopped: list[ActuatorError] = []

        def on_step(state: Any, output: Any, _n: int) -> None:
            try:
                getattr(vet, "landed", lambda _url: None)(state.url)  # X7, before acting
                for action in to_actions(output, state):
                    vet(action)
                    taken.append(action)
            except ActuatorError as exc:
                stopped.append(exc)
                agent.stop()
                raise

        agent = Agent(task=task, llm=ProviderChatModel(self.provider, self.guard),
                      browser_session=BuSession(cdp_url=self.cdp_url, **self._profile()),
                      use_vision=False,
                      register_new_step_callback=on_step, max_failures=1)
        try:
            history = await asyncio.wait_for(agent.run(max_steps=max_steps), timeout_s)
        except TimeoutError as exc:
            raise BoundExhausted(f"wall_clock_s={timeout_s:g} reached") from exc
        if stopped:
            raise stopped[0]
        return {
            "actions": [a.model_dump(mode="json") for a in taken],
            "observed": history.final_result() or "(the agent produced no final text)",
            "evidence_ref": f"browser-use:{agent.id}#steps={history.number_of_steps()}",
            "resolved": bool(history.is_done() and history.is_successful()),
        }
