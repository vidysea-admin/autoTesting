"""One job: the schema and answer-parsing half of the LiteLLM provider.

Three structured-output strategies, picked by model capability, never by vendor
name: `schema` (response_format json_schema), `tool` (one forced `answer`
function), `json` (JSON mode + prompt, with one counted repair). Every one ends
in `schema.model_validate`; a partial or coerced object is never returned.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from autotester.providers.gemini_schema import gemini_schema

ModelT = TypeVar("ModelT", bound=BaseModel)

TOOL_NAME = "answer"
_FENCE = re.compile(r"\A\s*```(?:json)?\s*(.*?)\s*```\s*\Z", re.DOTALL)


def json_schema_for(model: str, schema: type[BaseModel]) -> dict[str, Any]:
    """AT-230: Gemini's dialect rejects `additionalProperties` and `$defs`, which
    this repo's `extra="forbid"` models emit -- so a `gemini/...` model gets the
    existing translation, imported rather than re-implemented."""
    if model.startswith(("gemini/", "vertex_ai/")):
        return gemini_schema(schema)
    return schema.model_json_schema()


def request_options(strategy: str, model: str, schema: type[BaseModel]) -> dict[str, Any]:
    """The strategy-specific kwargs for one `litellm.completion` call."""
    body = json_schema_for(model, schema)
    if strategy == "schema":
        return {"response_format": {"type": "json_schema", "json_schema": {
            "name": TOOL_NAME, "schema": body, "strict": False}}}
    if strategy == "tool":
        return {
            "tools": [{"type": "function", "function": {
                "name": TOOL_NAME, "description": "Return the structured answer.",
                "parameters": body}}],
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        }
    return {"response_format": {"type": "json_object"}}


def json_mode_instruction(schema: type[BaseModel]) -> str:
    """Appended to the prompt in `json` mode so a model with no schema support
    still knows the exact shape (small local models)."""
    return ("\n\nReply with ONE JSON object only, no prose and no code fence, matching this "
            f"JSON Schema:\n{json.dumps(schema.model_json_schema())}")


def loads_json(text: str) -> Any:
    """Parse a model's text as JSON, tolerating a code fence or surrounding prose."""
    body = text.strip()
    fenced = _FENCE.match(body)
    if fenced:
        body = fenced.group(1)
    try:
        return json.loads(body)
    except ValueError:
        start, end = body.find("{"), body.rfind("}")
        if start < 0 or end <= start:
            raise
        return json.loads(body[start:end + 1])


def answer_text(message: Any, strategy: str) -> str:
    """The raw JSON text of the answer: the forced tool call's arguments for the
    `tool` strategy (falling back to content), else the message content."""
    if strategy == "tool":
        calls = getattr(message, "tool_calls", None) or []
        if calls:
            return str(calls[0].function.arguments)
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("the model returned no answer")
    return content


def parse_answer(message: Any, strategy: str, schema: type[ModelT], *,
                 strict: bool = False) -> ModelT:
    """Validate the model's answer against `schema`; ValueError (incl. pydantic's)
    on anything that is not exactly that shape."""
    data = loads_json(answer_text(message, strategy))
    return schema.model_validate_json(json.dumps(data), strict=strict)
