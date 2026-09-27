"""Turn a Pydantic model into a schema Gemini's `response_schema` will accept.

**AT-230.** Passing the Pydantic class straight through failed every real call
with `400 INVALID_ARGUMENT: Unknown name "additional_properties" at
'generation_config.response_schema'`. The cause is this codebase's own C1
invariant: every schema model sets `extra="forbid"`, which Pydantic emits as
`additionalProperties: false`, and Gemini's schema dialect has no such field.
`$defs`/`$ref` are rejected for the same reason — the dialect is a subset of
OpenAPI 3.0, not full JSON Schema.

**Why this survived a checker-PASS.** The T-131 provider unit was verified
against a *fake* client that accepted any config object, so the one thing that
could only fail against Google's actual endpoint was the one thing never
exercised. It surfaced within a second of the first real call. The lesson is not
"add a test" — it is that a seam whose whole purpose is talking to someone else's
API cannot be proven by a double that agrees with us.

**AT-265.** The first fix above shipped as a DENY-list of four keywords
(`additionalProperties`, `title`, `default`, `examples`) -- a record of what had
already 400'd, not a statement of what the dialect actually allows. Anything
else -- `const` (a single-value `Literal`), `prefixItems` (a `tuple[int, str]`),
`oneOf`/`discriminator` (a discriminated union) -- passed straight through to
Google untouched, because a deny-list's default is "keep". Verified against the
installed SDK (`google-genai` 2.22.0, no network): `google.genai.types.Schema`
has 25 fields, and `GenerateContentConfig(response_schema=<dict>)` performs no
local validation at all -- a dict is sent byte-for-byte, so any key outside that
set fails at Google exactly as `additionalProperties` did. This module now
filters by ALLOW-list against that field set (`ALLOWED_KEYS` below), so the
next unsupported keyword a new model shape emits is dropped by construction
instead of needing its own name added to a list someone has to remember to
update.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_SDK_SCHEMA_FIELD_ALIASES = frozenset({
    "anyOf", "default", "description", "enum", "example", "format", "items",
    "maxItems", "maxLength", "maxProperties", "maximum", "minItems",
    "minLength", "minProperties", "minimum", "nullable", "pattern",
    "properties", "propertyOrdering", "required", "title", "type",
})
"""The 22 keyword-position field names `google.genai.types.Schema` defines,
by their wire alias (`model_fields[name].alias`), EXCLUDING `additionalProperties`
and the bare `ref`/`defs` aliases.

`additionalProperties` is excluded even though it IS a real field on the SDK's
local type -- Google's endpoint 400s on it regardless (AT-230), so treating it
as allowed would readmit the original defect. `ref`/`defs` are excluded because
`_resolve` inlines every `$ref` before this filter ever runs, and Pydantic's own
spelling (`$ref`/`$defs`, with the dollar sign) never matches those bare aliases
in the first place -- admitting them here would be a no-op at best.

Counted directly against the installed SDK, not from memory:
`google.genai.types.Schema.model_fields` has 25 entries; this is those 25 minus
`additional_properties`, `ref`, and `defs` = 22."""

ALLOWED_KEYS = _SDK_SCHEMA_FIELD_ALIASES - {"title", "default"}
"""The keywords a schema NODE may keep, in keyword position -- everything else
(`const`, `prefixItems`, `oneOf`, `allOf`, `discriminator`, `exclusiveMinimum`,
`exclusiveMaximum`, `$schema`, `examples`, `additionalProperties`, and any
future keyword Pydantic starts emitting) is dropped, because it is not a
keyword Gemini's dialect can name.

`title` and `default` ARE genuinely in the SDK's field set (see above) but stay
excluded here: this is the same call AT-230 made and nothing about AT-265
changes it. `title` on a node is Pydantic's auto-generated class-name
annotation, never load-bearing for Gemini; `default` is redundant with
`required` already saying whether a field must be present. Keeping them costs
nothing at Google and buys nothing either, so the smaller surface wins.

**Only ever applied in keyword position.** Dropping them everywhere deleted
`ObservedIssue.title` -- a real field that happens to share its name with a
JSON-Schema annotation -- and Gemini answered
`required[3]: property is not defined`, because `required` still named a
property the schema no longer had. Inside a `properties` map the keys are
FIELD NAMES, and a field called `title` or `default` is just a field."""

MAX_REF_DEPTH = 20
"""A ceiling on `$ref` EXPANSION, not on structural nesting.

My first version counted every nested dict and list and capped at 12, which
`VideoObservation` blew through immediately -- a JSON schema is many levels deep
before any model nesting happens (`properties` -> each field -> its `items` ->
its type). It refused a schema that was perfectly fine. Only `$ref` resolution
can actually recurse forever, so that is the thing worth counting."""


class SchemaTooDeep(ValueError):
    """A model nested (or self-referential) past what inlining can flatten."""


def _translate(node: dict[str, Any]) -> dict[str, Any]:
    """Map constructs the dialect has no keyword for onto ones it does, before
    `ALLOWED_KEYS` would otherwise drop them and lose the information
    entirely (AT-265).

    - `oneOf` (a discriminated union) -> `anyOf`: Gemini has neither `oneOf`
      nor `discriminator`; `anyOf` is the closest construct it actually
      supports, and keeps the branch schemas instead of silently emptying the
      field down to nothing.
    - `const` (a single-value `Literal`) -> a one-element `enum`: Gemini has
      no `const`, but `enum` says the same thing (`kind` must equal exactly
      this one value) and IS in its dialect.

    Both only fire when the target key is not already present, so an explicit
    `anyOf`/`enum` the model itself emits is never clobbered."""
    if "oneOf" in node and "anyOf" not in node:
        node = {**node, "anyOf": node["oneOf"]}
    if "const" in node and "enum" not in node:
        node = {**node, "enum": [node["const"]]}
    return node


def _expand_ref(node: dict[str, Any], defs: dict[str, Any], refs: int) -> Any:
    """The `$ref` branch of `_resolve`, split out to keep that function under
    the file's 50-line ceiling. Same contract: inline the reference, or raise
    `SchemaTooDeep` if it cannot be."""
    if refs >= MAX_REF_DEPTH:
        # AT-267: name the reference, as the unresolvable branch below
        # already does. A deep-but-finite acyclic model 20 refs deep trips
        # this too, and 'is it self-referential?' with nothing to check
        # against just sent the reader looking for a cycle that may not
        # exist.
        raise SchemaTooDeep(
            f"$ref expanded {refs} deep at {node['$ref']!r} — "
            f"is a model self-referential?")
    name = str(node["$ref"]).rsplit("/", 1)[-1]
    if name not in defs:
        raise SchemaTooDeep(f"unresolvable $ref: {node['$ref']}")
    merged = {k: v for k, v in node.items() if k != "$ref"}
    return _resolve({**defs[name], **merged}, defs, refs + 1)


def _collapse_nullable_anyof(out: dict[str, Any]) -> dict[str, Any]:
    """`anyOf: [X, null]` is how Pydantic writes `X | None` (and, after
    `_translate`, how a discriminated union's `oneOf` arrives too). Gemini
    takes `nullable`, so collapse any null branch rather than sending a union
    member (`{"type": "null"}`) it has no type for.

    Not limited to the 2-member case: `int | str | None` is a 3-member
    `anyOf`, and an earlier `len(options) == 2` guard let its null branch
    survive untouched (AT-265) -- N-1 concrete branches after dropping null
    keep `anyOf`, exactly 1 collapses into the node directly, 0 leaves only
    `nullable`."""
    options = out.get("anyOf")
    if not isinstance(options, list):
        return out
    concrete = [o for o in options if not (isinstance(o, dict) and o.get("type") == "null")]
    if len(concrete) == len(options):
        return out
    out = {**out}
    out.pop("anyOf")
    out["nullable"] = True
    if len(concrete) == 1 and isinstance(concrete[0], dict):
        out = {**concrete[0], **out}
    elif len(concrete) > 1:
        out["anyOf"] = concrete
    return out


def _resolve(node: Any, defs: dict[str, Any], refs: int) -> Any:
    """Inline `$ref`s and keep only the keys Gemini's dialect defines.

    Inlined rather than passed through because Gemini's dialect has no `$defs`:
    a reference it cannot resolve is not a warning, it is a 400 on every call.

    `refs` counts only `$ref` expansions -- structural depth is unbounded and
    fine."""
    if isinstance(node, list):
        return [_resolve(item, defs, refs) for item in node]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        return _expand_ref(node, defs, refs)

    node = _translate(node)

    out: dict[str, Any] = {}
    for key, value in node.items():
        # ALLOW-list (AT-265): keep only what `google.genai.types.Schema`
        # actually defines. A deny-list's default is "keep", which is how
        # `const`/`prefixItems`/`oneOf` reached Google untouched; an
        # allow-list's default is "drop", so the next unnamed keyword a new
        # model shape emits is refused by construction, not by memory.
        if key not in ALLOWED_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            # Field names, not keywords -- every key here is kept verbatim.
            out[key] = {name: _resolve(sub, defs, refs) for name, sub in value.items()}
            continue
        out[key] = _resolve(value, defs, refs)

    return _collapse_nullable_anyof(out)


def gemini_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON schema, in the dialect Gemini's `response_schema` takes."""
    raw = model.model_json_schema()
    defs = raw.get("$defs", {})
    resolved = _resolve(raw, defs, 0)
    if not isinstance(resolved, dict):        # pragma: no cover - a model is always an object
        raise SchemaTooDeep(f"{model.__name__} did not resolve to an object schema")
    return resolved
