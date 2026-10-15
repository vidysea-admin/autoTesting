"""AT-939 / AT-830: a declared secret is masked in every escaped spelling, in linear time."""

from __future__ import annotations

import re
import time
from urllib.parse import quote, quote_plus

import pytest

from autotester.core.redact import Redactor, mask_pii, scrub_url_credentials

SECRET = "p@ss w0rd/&=+Z"
R = Redactor({"PW": SECRET})


def _entities(s: str, hexa: bool) -> str:
    return "".join(f"&#x{ord(c):x};" if hexa else f"&#{ord(c)};" for c in s)


@pytest.mark.parametrize("form", [
    quote(SECRET, safe=""),
    quote(quote(SECRET, safe=""), safe=""),
    quote_plus(SECRET),
    re.sub(r"%[0-9A-F]{2}", lambda m: m.group().lower(), quote(SECRET, safe="")),
    "p&#64;ss w0rd/&=+Z",
    "p&#x40;ss w0rd/&=+Z",
    "p&#X40;ss+w0rd/&=+Z",
    _entities(SECRET, False),
    _entities(SECRET, True),
    "p%40ss%20w0rd%2F%26%3D%2BZ",
    "p%2540ss%2520w0rd%252F%2526%253D%252BZ",
])
def test_escaped_secret_masked(form):
    out = R.scrub(f"GET https://demo.test/g?pw={form}&x=1 -> 500")
    assert "[REDACTED]:PW" in out
    assert "w0rd" not in out and "&#" not in out and "%" not in out.replace("%2540", "")
    assert "x=1 -> 500" in out


def test_plus_variant_of_space():
    out = Redactor({"K": "hello world"}).scrub("q=hello+world&z=1")
    assert "hello" not in out and "z=1" in out


def test_unrelated_text_untouched():
    text = "100%25 off &amp; more &#64; %40 plus a+b"
    assert R.scrub(text) == text


def test_plain_still_masked_and_idempotent():
    once = R.scrub(f"a {SECRET} b {quote(SECRET, safe='')}")
    assert once.count("[REDACTED]:PW") == 2 and R.scrub(once) == once


def test_url_credentials_moved_to_redact():
    out = scrub_url_credentials("https://x/p?api_token=abc123&page=2&session_id=zzz")
    assert "abc123" not in out and "zzz" not in out and "page=2" in out


@pytest.mark.parametrize("text", ["jane.doe%40gmail.com", "x?e=jane%40ex.co.in&y=1",
                                  "%2B91%2098765%2043210", "%2B919876543210"])
def test_encoded_pii_masked(text):
    out = mask_pii(text)
    assert "jane" not in out and "9876" not in out


def test_percent_prose_not_masked():
    assert mask_pii("100%40 off, save 20%20 today") == "100%40 off, save 20%20 today"


def test_linear_time_100kb():
    blobs = ["%20" * 34000, "a" * 100_000, "%2B" + "1%20" * 25000, "x%40" * 25000,
             "&#64;" * 20000, "?k=" + "a" * 100_000, "a.b-" * 25000 + "%40"]
    for blob in blobs:
        t = time.perf_counter()
        R.scrub(blob)
        mask_pii(blob)
        scrub_url_credentials(blob)
        assert time.perf_counter() - t < 1.0, blob[:12]
