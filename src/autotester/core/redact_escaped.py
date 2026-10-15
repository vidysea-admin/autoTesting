"""Escaped-spelling redaction: percent/entity/plus-encoded secrets, encoded PII, URL creds.

One job: find a declared secret (or an email/phone/credential param) when it is written in an
escaped spelling -- `%40`, `%2540`, `&#64;`, `&#x40;`, `+` for a space -- and report or mask it.
Decoded views carry a segment map back to the source, so a match is masked in place. Everything
here is linear: bounded quantifiers, single scans, no nested repetition.
"""

from __future__ import annotations

import html.entities
import re
from bisect import bisect_right
from typing import Any

_BASE = r"(?:%[0-9a-fA-F]{2})+|&#(?:\d{1,7}|[xX][0-9a-fA-F]{1,6});|&[A-Za-z][A-Za-z0-9]{1,31};"
_TOKEN = re.compile(_BASE)


def _decode_token(tok: str) -> str:
    if tok[0] == "%":
        raw = bytes(int(tok[i + 1:i + 3], 16) for i in range(0, len(tok), 3))
        return raw.decode("utf-8", "replace")
    if tok[1] == "#":
        body = tok[2:-1]
        try:
            return chr(int(body[1:], 16) if body[0] in "xX" else int(body))
        except (ValueError, OverflowError):
            return tok
    return html.entities.html5.get(tok[1:], tok)


class _View:
    """A decoded string plus the segments that map its indexes back to its parent string."""

    def __init__(self, parent: str) -> None:
        # segment = (d_lo, d_hi, o_lo, o_hi, identity)
        self.segs: list[tuple[int, int, int, int, bool]] = []
        pieces: list[str] = []
        d = o = 0
        self.decoded_any = False
        for m in _TOKEN.finditer(parent):
            if m.start() > o:
                n = m.start() - o
                self.segs.append((d, d + n, o, m.start(), True))
                pieces.append(parent[o:m.start()])
                d += n
            dec = _decode_token(m.group())
            if dec:
                self.segs.append((d, d + len(dec), m.start(), m.end(), False))
                pieces.append(dec)
                d += len(dec)
            self.decoded_any = self.decoded_any or dec != m.group()
            o = m.end()
        if o < len(parent):
            self.segs.append((d, d + len(parent) - o, o, len(parent), True))
            pieces.append(parent[o:])
        self.text = "".join(pieces)
        self._starts = [s[0] for s in self.segs]

    def span(self, lo: int, hi: int) -> tuple[int, int, bool]:
        """Parent span for decoded [lo, hi), and whether a decoded token is touched."""
        a = self.segs[bisect_right(self._starts, lo) - 1]
        b = self.segs[bisect_right(self._starts, hi - 1) - 1]
        o_lo = a[2] + (lo - a[0]) if a[4] else a[2]
        o_hi = b[2] + (hi - b[0]) if b[4] else b[3]
        return o_lo, o_hi, not (a[4] and b[4] and a is b)


def escaped_spans(text: str, values: list[tuple[str, str]]) -> list[tuple[int, int, str]]:
    """(start, end, key) in `text` for each secret that appears through an escaped spelling.

    `values` is [(secret, key)]. Decodes up to 2 levels; a secret containing a space is also
    searched with `+` for each space. A match made only of untouched literal text is skipped:
    plain replacement already masked it."""
    out: list[tuple[int, int, str]] = []
    cur, chain = text, []
    for level in range(3):
        if level:
            view = _View(cur)
            if not view.decoded_any:
                break
            chain.append(view)
            cur = view.text
        for value, key in values:
            needles = [(value, False)] + ([(value.replace(" ", "+"), True)] if " " in value else [])
            for needle, forced in needles:
                at = cur.find(needle)
                while at != -1:
                    lo, hi, touched = at, at + len(needle), forced
                    for v in reversed(chain):
                        lo, hi, t = v.span(lo, hi)
                        touched = touched or t
                    if touched:
                        out.append((lo, hi, key))
                    at = cur.find(needle, at + 1)
    return out


def mask_spans(text: str, spans: list[tuple[int, int, str]], mask: str) -> str:
    """Replace the union of `spans` with `mask` (`mask:KEY` when the span has a key)."""
    if not spans:
        return text
    spans.sort(key=lambda s: (s[0], -s[1]))
    out, pos = [], 0
    for lo, hi, key in spans:
        if hi <= pos:
            continue
        out.append(text[pos:max(lo, pos)])
        out.append(f"{mask}:{key}" if key else mask)
        pos = hi
    out.append(text[pos:])
    return "".join(out)


# --- encoded PII (AT-830): `%40` is "@", `%2B` is "+" ---------------------------------------
_LOCAL_CH = re.compile(r"[\w.%+-]")
_HOST_CH = re.compile(r"[\w.-]")


def mask_encoded_emails(text: str) -> str:
    """`<email>` for each `local%40host.tld`: widen from every `%40` -- linear."""
    if "%40" not in text:
        return text
    out, pos, n = [], 0, len(text)
    at = text.find("%40")
    while at != -1:
        hi = at + 3
        while hi < min(n, at + 260) and _HOST_CH.match(text[hi]):
            hi += 1
        host = text[at + 3:hi].rstrip(".-_")
        label = host.rpartition(".")[2]
        lo = at
        if "." in host and host[0] not in ".-" and len(label) >= 2 and label.isalpha():
            while lo > max(pos, at - 256) and _LOCAL_CH.match(text[lo - 1]):
                lo -= 1
        if lo < at:
            out += (text[pos:lo], "<email>")
            pos = at + 3 + len(host)
            at = text.find("%40", pos)
        else:
            at = text.find("%40", at + 3)
    return "".join(out) + text[pos:]


_ENC_PHONE = re.compile(r"(?<![\w+])%2[bB](\d[\d\s().%-]{0,80})")
_PHONE_SEP = (" ", "\t", "\n", "\r", "(", ")", ".", "-")


def _phone_end(s: str) -> tuple[int, int]:
    """(digits, end) of the phone-shaped prefix of `s`, stopping at 17 digits."""
    i, digits, end = 0, 0, 0
    while i < len(s) and digits < 17:
        c = s[i]
        if c.isdigit() and c.isascii():
            digits, i, end = digits + 1, i + 1, i + 1
        elif c == "%" and s[i:i + 3] in ("%20", "%28", "%29"):
            i += 3
        elif c in _PHONE_SEP:
            i += 1
        else:
            break
    return digits, end


def mask_encoded_phones(text: str) -> str:
    """`<phone>` for `%2B` + 8..17 digits with `%20 %28 %29 space ( ) . -` separators."""
    if "%2" not in text:
        return text

    def repl(m: re.Match[str]) -> str:
        digits, end = _phone_end(m.group(1))
        tail = m.group(1)[end:end + 1]
        if digits < 8 or (tail and (tail.isalnum() or tail == "_")):
            return m.group()
        return "<phone>" + m.group(1)[end:]

    return _ENC_PHONE.sub(repl, text)


# --- URL credential params (one concept, one place) ---------------------------------------
_CRED_WORDS = ("token", "key", "secret", "password", "passwd", "sig", "session", "auth", "code")
_URL_PARAM = re.compile(r"([?&;])([\w.-]{1,80})=([^&\s\"'<>]+)")


def scrub_url_credentials(text: str, mask: str = "[REDACTED]") -> str:
    """Mask the value of every `?token=...`-style query parameter in `text`."""
    if "=" not in text:
        return text

    def repl(m: re.Match[str]) -> str:
        name = m.group(2).lower()
        if any(w in name for w in _CRED_WORDS):
            return f"{m.group(1)}{m.group(2)}={mask}"
        return m.group()

    return _URL_PARAM.sub(repl, text)


def scrub_url_credentials_obj(obj: Any) -> Any:
    """`scrub_url_credentials` over every string inside dicts, lists and tuples."""
    if isinstance(obj, str):
        return scrub_url_credentials(obj)
    if isinstance(obj, dict):
        return {k: scrub_url_credentials_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(scrub_url_credentials_obj(v) for v in obj)
    return obj
