"""The Gemini response-schema sanitiser's ALLOW-list — AT-265.

Split from test_gemini_schema.py (already scoped to the response-schema
sanitiser, AT-230) once its own line count crossed the 300-line ceiling.
Same seam, different hazard: AT-230 was one keyword (`additionalProperties`)
that had already 400'd; AT-265 is every keyword that HASN'T yet, because the
sanitiser it fixed was a deny-list of four names, not an allow-list of the
dialect's actual field set. Every probe here is a constructed schema shape
that leaked an unsupported keyword through the old deny-list untouched —
confirmed against the buggy code before the fix (see
qa/manifests/at265-gemini-schema-allowlist.md) — never a live 400, per the
issue's own evidence (AT-265: "LATENT, NOT LIVE").

Contract: qa/contracts/ingest.md (provider seam), I11.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from autotester.providers.gemini_schema import ALLOWED_KEYS, gemini_schema
from autotester.schema.observation import VideoObservation


def keys_anywhere(node: object) -> set[str]:
    """Every dict KEY in the tree. Structural, not a substring search over
    the rendered JSON — see test_gemini_schema.py's identical helper for why
    (a `$ref`-shaped word inside a docstring is not a `$ref`)."""
    found: set[str] = set()
    if isinstance(node, dict):
        found |= set(node)
        for value in node.values():
            found |= keys_anywhere(value)
    elif isinstance(node, list):
        for item in node:
            found |= keys_anywhere(item)
    return found


class _Cat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["cat"] = "cat"
    lives: int = 9


class _Dog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["dog"] = "dog"
    breed: str = "lab"


class _LiteralModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["only"]


class _TupleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pair: tuple[int, str]


class _DiscriminatedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pet: Annotated[_Cat | _Dog, Field(discriminator="kind")]


class _NullableUnionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    val: int | str | None = None


def test_a_single_value_literal_becomes_enum_not_const() -> None:
    """AT-265 probe 1. `const` is not in Gemini's dialect; `enum` says the
    same thing (`kind` must equal exactly this one value) and is."""
    schema = gemini_schema(_LiteralModel)
    kind = schema["properties"]["kind"]

    assert "const" not in keys_anywhere(schema)
    assert kind["enum"] == ["only"]


def test_a_tuple_drops_prefixItems_rather_than_leaking_it() -> None:
    """AT-265 probe 2. The old sanitiser sent `prefixItems` with no `items` --
    a shape Google refuses. `prefixItems` has no Gemini equivalent (only
    homogeneous arrays are expressible), so it is dropped cleanly, leaving a
    valid if less specific array schema instead of a malformed one."""
    schema = gemini_schema(_TupleModel)

    assert "prefixItems" not in keys_anywhere(schema)


def test_a_discriminated_union_becomes_anyOf_not_a_dropped_oneOf() -> None:
    """AT-265 probe 3. The old sanitiser dropped `discriminator` but kept the
    `oneOf` it belonged to -- an invalid keyword Google 400s on. `oneOf` has
    no Gemini equivalent by name, but `anyOf` expresses the same "matches one
    of these shapes" constraint and IS in the dialect, so this translates
    rather than silently emptying the field."""
    schema = gemini_schema(_DiscriminatedModel)
    pet = schema["properties"]["pet"]
    keys = keys_anywhere(schema)

    assert "oneOf" not in keys
    assert "discriminator" not in keys
    assert isinstance(pet.get("anyOf"), list)
    assert len(pet["anyOf"]) == 2


def test_a_three_way_union_with_none_collapses_the_null_branch() -> None:
    """AT-265 probe 4. The old collapse only fired for a 2-member `anyOf`
    (plain `X | None`), so `int | str | None` -- a 3-member `anyOf` -- kept
    its `{"type": "null"}` branch untouched; Gemini has no `null` type."""
    schema = gemini_schema(_NullableUnionModel)
    val = schema["properties"]["val"]

    assert val.get("nullable") is True
    assert not any(
        isinstance(o, dict) and o.get("type") == "null"
        for o in val.get("anyOf", [])
    )
    assert {o.get("type") for o in val["anyOf"]} == {"integer", "string"}


def test_no_keyword_outside_the_sdk_field_set_ever_survives() -> None:
    """I11's actual criterion, stated directly rather than through one probe
    at a time: nothing in a rendered schema may be a keyword outside
    `google.genai.types.Schema`'s field set. Sweeps every hazard shape plus
    the real production model."""
    hazards = [_LiteralModel, _TupleModel, _DiscriminatedModel,
               _NullableUnionModel, VideoObservation]

    def offending_keys(node: object) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "properties" and isinstance(value, dict):
                    for sub in value.values():         # field names, not keywords
                        found |= offending_keys(sub)
                    continue
                if key not in ALLOWED_KEYS:
                    found.add(key)
                found |= offending_keys(value)
        elif isinstance(node, list):
            for item in node:
                found |= offending_keys(item)
        return found

    for model in hazards:
        assert offending_keys(gemini_schema(model)) == set(), model.__name__


def test_ALLOWED_KEYS_matches_the_installed_SDKs_actual_field_set() -> None:
    """Guards against drift on a `google-genai` upgrade: if the SDK adds,
    renames, or removes a field, this fails loudly instead of the allow-list
    silently going stale. Verified against the installed package, the way
    AT-265's own evidence was gathered -- not from memory."""
    from google.genai import types

    from autotester.providers.gemini_schema import _SDK_SCHEMA_FIELD_ALIASES

    sdk_aliases = {
        field.alias or name for name, field in types.Schema.model_fields.items()
    }

    assert sdk_aliases - {"additionalProperties", "ref", "defs"} == _SDK_SCHEMA_FIELD_ALIASES
    assert ALLOWED_KEYS <= _SDK_SCHEMA_FIELD_ALIASES
