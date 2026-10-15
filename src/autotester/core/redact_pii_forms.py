"""Extra PII spellings for `redact.mask_pii`: obfuscated emails and labelled name fields (AT-840).

One job: rewrite `a [at] b (dot) c`, `a%40b.c`, fullwidth `＠` and `a at b dot c` into a plain
`a@b.c` so the existing email masker sees it, and mask the value of explicit `first_name:` /
`name=` style fields. Free-text names ("Ravi Kumar") are NOT detected -- too guessy.
All patterns are linear: no nested quantifiers over overlapping classes.
"""

from __future__ import annotations

import re
import unicodedata

_AT_WORD = re.compile(r"\s*[\[(\{<]\s*at\s*[\])\}>]\s*", re.IGNORECASE)
_DOT_WORD = re.compile(r"\s*[\[(\{<]\s*dot\s*[\])\}>]\s*", re.IGNORECASE)
_SPOKEN = re.compile(
    r"\b([\w.+-]{1,64})[ \t]+at[ \t]+([\w-]{1,63}(?:[ \t]+dot[ \t]+[\w-]{1,63})+)\b", re.IGNORECASE
)
_SPOKEN_DOT = re.compile(r"[ \t]+dot[ \t]+", re.IGNORECASE)
_NAME_FIELD = re.compile(
    r"\b((?:[a-z]{1,20}[_ -])?name)(\"?[ \t]*[:=][ \t]*\"?)([^\n,;\"]{1,80})", re.IGNORECASE
)


def normalize_email_forms(text: str) -> str:
    """Plain-ASCII `@` / `.` for obfuscated email spellings; text with none is returned as is."""
    if text.isascii() and "%" not in text and "at" not in text.lower():
        return text
    for _ in range(2):  # %40 and double-encoded %2540
        view = _View(text) if "%" in text or "&" in text else None
        text = view.text if view is not None and view.decoded_any else text
    text = unicodedata.normalize("NFKC", text)
    text = _AT_WORD.sub("@", text)
    if "@" in text:
        text = _DOT_WORD.sub(".", text)
    return _SPOKEN.sub(lambda m: m.group(1) + "@" + _SPOKEN_DOT.sub(".", m.group(2)), text)


def mask_name_fields(text: str, mask_name_value) -> str:
    """`<name>` for the value of a person-name field; `mask_name_value` decides per label."""
    def repl(m: re.Match[str]) -> str:
        value = m.group(3).rstrip()
        masked = mask_name_value(m.group(1), value)
        if masked == value:
            return m.group(0)
        return m.group(1) + m.group(2) + masked + m.group(3)[len(value):]

    return _NAME_FIELD.sub(repl, text) if ":" in text or "=" in text else text
