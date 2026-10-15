"""One job: make a URL path template safe to store -- no email, phone, token, UUID or JWT.

`url_template` folds numeric ids only. A path such as `/user/jo@x.com/p` or `/reset/<token>`
would otherwise reach the tracked crawl summary and the run report verbatim (AT-887). Emails and
phones are found by `core.redact.mask_pii` (the one PII detector); this adds the token shapes it
does not know. A folded segment becomes `{var}`; ordinary slugs stay readable.
"""

from __future__ import annotations

import re

from autotester.core.redact import mask_pii

VAR = "{var}"
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_JWT = re.compile(r"[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*")
_DIGITS = re.compile(r"\d{6,}")
_B64ISH = re.compile(r"[A-Za-z0-9_=+-]{16,}")


def _is_secretish(seg: str) -> bool:
    if _UUID.fullmatch(seg) or _JWT.fullmatch(seg) or _DIGITS.search(seg):
        return True
    if not _B64ISH.fullmatch(seg):
        return False
    words = [p for p in re.split(r"[-_]", seg) if p.isalpha()]
    mixed = any(c.isdigit() for c in seg) and any(c.isalpha() for c in seg)
    return (mixed and len(words) < 2) or (len(seg) >= 24 and "-" not in seg and "_" not in seg)


def safe_path(path: str) -> str:
    """`path` with each PII- or token-shaped segment replaced by `{var}`."""
    out = []
    for seg in path.split("/"):
        if seg and (mask_pii(seg) != seg or _is_secretish(seg)):
            seg = VAR
        out.append(seg)
    return mask_pii("/".join(out))
