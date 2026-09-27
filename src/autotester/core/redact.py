"""Secret redaction. Every log line and stored artifact passes through here.

The rule this module exists to enforce: a secret VALUE must never reach a model
prompt, a log file, or an artifact on disk. Only placeholders travel.

Folding internals (Unicode normalisation, homoglyphs, encoded/reversed
spellings) live in `core.redact_fold` -- split out so this file stays under
the C2 line cap; every name anything outside this pair imports is re-exported
here unchanged, so `from autotester.core.redact import ...` keeps working.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from autotester.core.redact_fold import (
    ASCII_CONFUSABLES,
    BIDI_OVERRIDES,
    MIN_FOLDED_LEN,
    _contains_folded_secret,
    fold_credential,
)

__all__ = [
    "ASCII_CONFUSABLES",
    "BIDI_OVERRIDES",
    "MASK",
    "MIN_FOLDED_LEN",
    "PLACEHOLDER_RE",
    "Redactor",
    "assert_no_raw_secrets",
    "fold_credential",
    "has_placeholder",
    "placeholder_keys",
]

MASK = "[REDACTED]"
PLACEHOLDER_RE = re.compile(r"\{\{SECRET:([A-Z0-9_]+)\}\}")


class Redactor:
    """Replaces known secret values with `[REDACTED]` anywhere they appear.

    Construct once per run from the loaded environment, then pass every string
    that is about to be logged, prompted, or persisted through `scrub`.

    There is deliberately no minimum length: these are known-exact declared
    values, not heuristic guesses. A three-character password is a bad
    password, but leaking it is still a leak (checker finding AT-002).
    """

    def __init__(self, secrets: dict[str, str]) -> None:
        # Longest first, so a value that contains another is masked whole.
        self._values = sorted((v for v in secrets.values() if v), key=len, reverse=True)
        self._keys_by_value = {v: k for k, v in secrets.items()}
        # (raw_value, folded_value) pairs, kept together so the widened check
        # can search for the RAW value's exact encodings (AT-352 cycle 2 --
        # base64/hex output is case/punctuation-significant and must not be
        # folded) as well as its folded form, without recomputing either.
        # AT-352 cycle 3: NOT pre-filtered by MIN_FOLDED_LEN here any more --
        # a checker found this filter starved the exact-encoding search of
        # every secret whose FOLDED form fell under the floor, even though
        # that search is exact, not heuristic. `_contains_folded_secret`
        # applies the right floor to each half itself (see its docstring).
        self._widened = [(v, fold_credential(v)) for v in self._values]

    def scrub(self, text: str) -> str:
        """Return `text` with every known secret value masked."""
        for value in self._values:
            if value in text:
                key = self._keys_by_value.get(value, "")
                text = text.replace(value, f"{MASK}:{key}" if key else MASK)
        return text

    def scrub_obj(self, obj: Any) -> Any:
        """Recursively scrub strings inside dicts, lists, and tuples."""
        if isinstance(obj, str):
            return self.scrub(obj)
        if isinstance(obj, dict):
            return {k: self.scrub_obj(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return type(obj)(self.scrub_obj(v) for v in obj)
        return obj

    def is_clean(self, text: str) -> bool:
        """True when no known secret value appears in `text`, byte for byte."""
        return not any(value in text for value in self._values)

    def contains_folded(self, text: str) -> bool:
        """True when a secret appears in `text` once both sides are folded
        (AT-339), including through an encoded or reversed spelling (AT-352)
        such as base64, hex, HTML entities, double percent-encoding, or plain
        reversal -- see `redact_fold._contains_folded_secret`. Deliberately
        separate from `is_clean`, and NOT used by `scrub`: you cannot mask a
        transform, because the literal bytes are not there to replace. This
        answers the guard's question -- "could a reader recover a credential
        from what we are about to store?" -- which is a different question
        from redaction's."""
        return _contains_folded_secret(text, self._widened)

    def assert_clean(self, text: str) -> None:
        """Hard gate: raise if a known secret value survives in `text` even
        after `scrub` (D-041 RT6) -- the last check before something is
        persisted. Reuses this Redactor's own loaded values, so a caller
        never has to hold the raw secrets separately just to gate on them."""
        assert_no_raw_secrets(text, self._values)


def placeholder_keys(text: str) -> list[str]:
    """Secret keys referenced as `{{SECRET:KEY}}` inside `text`."""
    return PLACEHOLDER_RE.findall(text)


def has_placeholder(text: str) -> bool:
    return bool(PLACEHOLDER_RE.search(text))


def assert_no_raw_secrets(text: str, secrets: Iterable[str]) -> None:
    """Raise if a raw secret value is present, or if `text` carries one in a
    folded, encoded, or reversed spelling (AT-347). Used as a hard gate before
    prompting -- this is the ONE gate a folded credential reached unnoticed
    (`browser/secrets.py::guard_prompt`'s only caller path): the UI intake
    door already folds via `Redactor.contains_folded`, this door did not.

    The exact check is floorless: any non-empty declared value counts,
    regardless of length (AT-002). The widened check (fold-based AND
    exact-encoding) applies its floors the same way `Redactor` does --
    inside `_contains_folded_secret`, not here (AT-352 cycle 3) -- so a short
    secret's FOLDED form does not start refusing ordinary text that merely
    contains its letters, while its exact base64/base32/hex encodings still
    get searched for down to a shorter raw-length floor.

    Known encoding-coverage boundary (AT-607, disclosed rather than fixed --
    tests/test_redact_encoding_coverage.py pins both): a declared secret of
    7 or fewer raw characters gets NO base64/base32/hex protection at all --
    `MIN_FOLDED_LEN` (redact_fold.py) gates the exact-encoding search on the
    RAW value's length, by design (AT-352 cycle 3), not a bug in this gate.
    Separately, an EXACTLY-8-character secret still misses one specific
    spelling: base32 at byte-alignment offset 1 (mod 5). At that offset,
    `redact_encodings._alignment_needles`' padded byte stream splits into
    exactly two 5-byte groups, and its group-drop is coarse by design (an
    entire group is discarded once ANY of its bytes are unknown, even though
    only 1-2 of its 8 characters are actually affected) -- for an 8-byte
    secret both groups are edges, so both are dropped and no needle survives.
    Secrets of 9+ raw characters have no known misses (checker probe,
    qa/verdicts/at347-352-356-redact-fold.md cycle 3, AT-607).
    """
    values = [v for v in secrets if v]
    for value in values:
        if value in text:
            raise ValueError("refusing to proceed: raw secret value present in payload")
    widened = [(v, fold_credential(v)) for v in values]
    if _contains_folded_secret(text, widened):
        raise ValueError(
            "refusing to proceed: raw secret value present in payload "
            "(folded/encoded/reversed match)"
        )
