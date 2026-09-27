"""Credential-guard helpers: refuse a real secret typed into any UI text field.

Split out of `ui/helpers.py` (AT-567 -- the file sat at the C2 300-line cap
with no headroom) into its own module because these four functions are one
concern -- catching a pasted credential before it reaches a git-tracked file
or a screenshot -- distinct from the slug/id/url validation the rest of
`helpers.py` does. Re-exported from `ui/helpers` so every existing importer
(`ui/app.py`, `ui/routes_cases.py`, `ui/routes_credentials.py`, and others)
keeps working unchanged.
"""

from __future__ import annotations

from urllib.parse import unquote_plus

from fastapi import HTTPException

from autotester.browser.secrets import SecretStore
from autotester.core.redact import BIDI_OVERRIDES, PLACEHOLDER_RE
from autotester.schema.project import Project


def _credential_variants(text: str) -> list[str]:
    """The forms a pasted credential can arrive in that all recover trivially.

    AT-074: `Redactor.is_clean` is a plain substring test, so a value that was
    URL-encoded, or that a user broke with a stray space or newline, sailed
    through and was written to a git-tracked file — recoverable with one
    `unquote_plus` or a whitespace strip. Matching is done against every form,
    not just the literal one.

    AT-339: case and separator transforms are NOT handled here, because they
    need both sides folded and only the redactor holds the values — see
    `Redactor.contains_folded`, applied to EVERY form in this list at each call
    site. Adding a `.casefold()` entry to this list would have done nothing:
    the stored value would still be compared in its original case.

    AT-346: the fold used to be applied to the raw text only, never to these
    variants, so each guard covered exactly the half the other did not —
    `zebra%5Fquilt%5Fapikey%5F31` survived folding with its escapes intact, and
    the `unquote_plus` form that would have exposed it was only ever compared
    byte-for-byte. Composition is the point: decode, THEN fold.
    """
    decoded = unquote_plus(text)
    return [
        text,
        decoded,
        "".join(text.split()),
        "".join(decoded.split()),
    ]


def _refuse_direction_override(value: str, field: str) -> None:
    """Refuse text carrying a bidi OVERRIDE, on its own terms (AT-355).

    Checked before the credential comparison, and never folded away, because
    subtracting the override is what let the leak through: it deletes the
    character that causes the reordering and then compares a string that is not
    the credential, while a reader sees the credential in plain type.

    The message names the override rather than claiming a credential, because
    this fires on text holding no credential at all -- saying otherwise would
    send the user hunting for a secret that is not there, which is the same
    false diagnosis the "split across" message made in AT-339.
    """
    if any(override in value for override in BIDI_OVERRIDES):
        raise HTTPException(400, (
            f"{field} contains a text-direction override character. It makes text "
            f"render in a different order than it is stored, so what you see is not "
            f"what is saved. Remove it and type the value plainly."
        ))


def _refuse_unsafe_value(
    value: str, project: Project, secrets: SecretStore, *, field: str = "this field",
    exempt_value: str | None = None,
) -> None:
    """One field. Placeholders must name a declared key; a literal must not be
    a real `.env` value. Two distinct mistakes, both silent before this existed:
    - Typing the credential ITSELF into a text box. `cases.jsonl` is git-TRACKED
      in a public repo, so that is a credential committed in cleartext; and
      because no `{{SECRET:KEY}}` placeholder is present, `session.fill` never
      tags the field, so it shows up in every screenshot too.
    - Referencing a key the project has not declared. That resolved only at
      typing time, deep inside `_value_for`, surfacing as a stringified
      `UndeclaredSecret` inside a generic ERRORED outcome.
    """
    if not value:
        return
    _refuse_direction_override(value, field)
    referenced = PLACEHOLDER_RE.findall(value)
    if referenced:
        for key in referenced:
            if project.secret(key) is None:
                raise HTTPException(400, (
                    f"this project has not declared a credential called '{key}'. "
                    f"Declare it in Project settings first, then use it here."
                ))
        return
    if exempt_value is not None and value == exempt_value:
        # AT-078/AT-087: byte-identical to what THIS SAME FIELD already holds
        # on disk -- never another field's value (the flat-set bug) or fresh
        # input (AT-083).
        return
    if value in secrets.public_values():
        # AT-086: a declared-public .env value (never inferred --
        # core.env.PUBLIC_ENV_KEYS) is not a credential at all.
        return
    redactor = secrets.redactor()
    variants = _credential_variants(value)
    if (any(not redactor.is_clean(v) for v in variants)
            or any(redactor.contains_folded(v) for v in variants)):
        raise HTTPException(400, (
            f"{field} looks like it contains a real credential. Values are stored in "
            f"the repository in plain text and appear in screenshots, so they must "
            f"never be typed in directly. Declare it in Project settings and use "
            f"{{{{SECRET:KEY}}}} in a step's Value box — note that only a Value is "
            f"substituted, not a URL or a title."
        ))


def _refuse_unsafe_submission(
    texts: list[tuple[str, str]], project: Project, secrets: SecretStore,
    *, exempt: dict[str, str] | None = None,
) -> None:
    """Every user-supplied field of a case, and their concatenation.

    AT-070: the guard was wired to the value box alone, so the same credential
    typed into the title, the target or the expect box sailed through into a
    git-tracked `cases.jsonl`. The title was the worst of the three — U6 leaves
    `rationale=None`, so `claim_of` falls back to the title and feeds it to the
    grade prompt, where `guard_prompt` raises and 500s every later run.

    AT-083: matching runs over EVERY value in `.env`, declared or not -- an
    undeclared key is still a credential, and this repo is public.

    `exempt` maps a field's label to the ONE already-stored value it may
    re-submit unchanged (AT-078/AT-087 -- per-field, never a flat set that
    lets one field's value exempt another). AT-071/AT-087: fields checked one
    at a time also missed a value split across rows/types and reassembled on
    disk -- so the joined text is checked too, with an exempt field kept IN it
    as CONTEXT (dropping it hid exactly this split). Only each field's own
    exempt value, and any declared-public value (AT-086), is excluded from
    the join's match set -- every OTHER secret still trips it.
    """
    exempt = exempt or {}
    for label, text in texts:
        _refuse_unsafe_value(
            text.strip(), project, secrets, field=label, exempt_value=exempt.get(label),
        )
    fresh = [(label, text.strip()) for label, text in texts]
    joined = "".join(text for _label, text in fresh)
    excluded = {v for v in exempt.values() if v} | secrets.public_values()
    redactor = secrets.redactor(exclude=excluded)
    joined_variants = _credential_variants(joined)
    if joined and (any(not redactor.is_clean(v) for v in joined_variants)
                   or any(redactor.contains_folded(v) for v in joined_variants)):
        raise HTTPException(400, (
            "a real credential appears to be split across "
            f"{', '.join(sorted({label for label, t in fresh if t}))}. Declare it in Project "
            "settings and use {{SECRET:KEY}} in a step's Value box instead."
        ))
