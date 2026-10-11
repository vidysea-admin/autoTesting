"""Harness: fake litellm + temp repo root + leak detector. No network, no pytest."""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import traceback
import types
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

sys.path.insert(0, os.environ["PYTHONPATH"])

SCRATCH = Path(__file__).parent
_NO = ("AUTOTESTER_MODEL", "LITELLM_API_KEY", "LITELLM_API_BASE", "OLLAMA_BASE_URL",
       "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


class Ans(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: str


def reply(content=None, tool_args=None):
    tc = None
    if tool_args is not None:
        tc = [types.SimpleNamespace(function=types.SimpleNamespace(
            name="answer", arguments=tool_args if isinstance(tool_args, str) else json.dumps(tool_args)))]
    msg = types.SimpleNamespace(content=content, tool_calls=tc)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)],
                                 usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1))


class Fake(types.ModuleType):
    def __init__(self, responses, schema=True, tool=True):
        super().__init__("litellm")
        self.responses, self.calls, self.schema, self.tool = list(responses), [], schema, tool

    def completion(self, **kw):
        self.calls.append(kw)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def supports_response_schema(self, model, custom_llm_provider=None):
        return self.schema

    def supports_function_calling(self, model, custom_llm_provider=None):
        return self.tool

    def validate_environment(self, model=None, api_key=None, api_base=None, api_version=None):
        return {"keys_in_environment": True, "missing_keys": []}


class Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, r):
        self.lines.append(r.getMessage())


class FakeTrace:
    def __init__(self):
        self.rows = []

    def record_llm(self, **kw):
        self.rows.append(kw)


def run(env_text: str | None, prompt: str, *, responses=None, exports: dict | None = None,
        secrets=None, images=None, endpoint: dict | None = None, strategy="schema",
        model="openai/gpt-4o", call="judge", env_bytes: bytes | None = None):
    """Run one provider call. Returns dict(outcome, fake, exc, logs, provider, trace)."""
    tmp = Path(tempfile.mkdtemp(prefix="t202b-"))
    if env_bytes is not None:
        (tmp / ".env").write_bytes(env_bytes)
    elif env_text is not None:
        (tmp / ".env").write_text(env_text, encoding="utf-8")
    for k in _NO:
        os.environ.pop(k, None)
    saved = {}
    for k, v in {**(exports or {}), **(endpoint or {})}.items():
        saved[k] = os.environ.get(k)
        os.environ[k] = v
    os.environ["AUTOTESTER_ROOT"] = str(tmp)
    fake = Fake(responses if responses is not None else [reply('{"verdict":"ok"}')],
                schema=(strategy == "schema"), tool=(strategy == "tool"))
    sys.modules["litellm"] = fake
    cap = Cap()
    root = logging.getLogger()
    old = root.level
    root.setLevel(logging.DEBUG)
    root.addHandler(cap)
    from autotester.providers.litellm_provider import LiteLLMProvider
    p = LiteLLMProvider(model=model, secrets=secrets or [])
    tr = FakeTrace()
    p.trace = tr
    exc = None
    try:
        if call == "judge":
            p.judge(prompt, Ans, images=images)
        else:
            p.act(prompt, Ans)
    except Exception as e:  # noqa: BLE001
        exc = e
    finally:
        root.removeHandler(cap)
        root.setLevel(old)
        for k in saved:
            if saved[k] is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = saved[k]
        for k in (exports or {}):
            os.environ.pop(k, None)
        os.environ.pop("AUTOTESTER_ROOT", None)
    return {"fake": fake, "exc": exc, "logs": cap.lines, "p": p, "trace": tr}


def chain_texts(exc):
    """str/repr/traceback/__cause__/__context__ texts of an exception chain."""
    out = []
    seen = set()
    stack = [exc]
    while stack:
        e = stack.pop()
        if e is None or id(e) in seen:
            continue
        seen.add(id(e))
        out += [("str", str(e)), ("repr", repr(e))]
        stack += [e.__cause__, e.__context__]
    out.append(("tb", "".join(traceback.format_exception(exc))))
    return out


def where_leaked(r, needle: str, *, allow_api_key=False):
    """List of places `needle` appears (exact substring)."""
    hits = []
    for i, c in enumerate(r["fake"].calls):
        for k, v in c.items():
            if allow_api_key and k == "api_key":
                continue
            if needle in json.dumps(v, default=str, ensure_ascii=False):
                hits.append(f"call{i}.{k}")
    if r["exc"] is not None:
        # only the surface a caller would normally see: str/repr/traceback.format_exception
        e = r["exc"]
        for name, t in (("exc.str", str(e)), ("exc.repr", repr(e)),
                        ("exc.traceback_fmt", "".join(traceback.format_exception(e)))):
            if needle in t:
                hits.append(name)
        # programmatic chain (not shown by format_exception when suppressed)
        for tag, ch in (("__cause__", e.__cause__), ("__context__", e.__context__)):
            if ch is not None and needle in (str(ch) + repr(ch)):
                hits.append(f"exc.{tag}.str(programmatic)")
    for l in r["logs"]:
        if needle in l:
            hits.append("log")
    for u in r["p"].usage:
        if needle in u.model_dump_json():
            hits.append("usage")
    for row in r["trace"].rows:
        if needle in json.dumps(row, default=str):
            hits.append("trace")
    return hits


def outcome(r) -> str:
    if r["fake"].calls:
        return f"CALLED({len(r['fake'].calls)})"
    e = r["exc"]
    return f"REFUSED/{type(e).__name__}" if e else "NOCALL-NOEXC"
