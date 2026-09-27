"""Regression suite for AT-599 (a needle broken by whitespace) and AT-606
(the folded-secret scan was superlinear) -- both filed against the merged
at347-352-356-redact-fold work (qa/verdicts/at347-352-356-redact-fold.md).

Split out of test_redact_obfuscation.py, which was already at 290 of its
300-line C2 cap: these are two new, distinct concerns (whitespace-split
detection and scan performance), not more of that file's obfuscated-spelling
coverage. Synthetic fake secrets only.

Cycle 2: AT-599's own expected clause names "whitespace inside base64-
alphabet runs", not only line breaks -- a checker's cycle-1 repro showed a
space or a newline-plus-indent split both still evaded the line-break-only
strip. The space/tab/indent tests below close that gap.
"""

from __future__ import annotations

import base64
import random
import string
import textwrap
import time

import pytest

from autotester.core.redact import Redactor, assert_no_raw_secrets

WRAP_CRED = "ZEBRA_QUILT_WRAPTOKEN_47"


def _mid_token_break(encoded: str, newline: str = "\n") -> str:
    """Insert one line break at the midpoint of `encoded` -- AT-599's "a
    mid-token newline" case."""
    mid = len(encoded) // 2
    return encoded[:mid] + newline + encoded[mid:]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_contains_folded_catches_mid_token_newline_in_base64(newline: str) -> None:
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), newline)
    redactor = Redactor({"WRAP": WRAP_CRED})
    assert redactor.contains_folded(payload)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_assert_no_raw_secrets_blocks_mid_token_newline_in_base64(newline: str) -> None:
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), newline)
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(payload, [WRAP_CRED])


def test_contains_folded_catches_mid_token_newline_in_hex() -> None:
    payload = _mid_token_break(WRAP_CRED.encode().hex())
    redactor = Redactor({"WRAP": WRAP_CRED})
    assert redactor.contains_folded(payload)


def test_assert_no_raw_secrets_blocks_mid_token_newline_in_hex() -> None:
    payload = _mid_token_break(WRAP_CRED.encode().hex())
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(payload, [WRAP_CRED])


def test_contains_folded_catches_mid_token_space_in_base64() -> None:
    # Checker cycle-1 repro: a plain space split still evaded the line-break-
    # only strip, since a space is neither `\r` nor `\n`.
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), " ")
    redactor = Redactor({"WRAP": WRAP_CRED})
    assert redactor.contains_folded(payload)


def test_assert_no_raw_secrets_blocks_mid_token_space_in_base64() -> None:
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), " ")
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(payload, [WRAP_CRED])


def test_contains_folded_catches_mid_token_tab_in_base64() -> None:
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), "\t")
    redactor = Redactor({"WRAP": WRAP_CRED})
    assert redactor.contains_folded(payload)


def test_assert_no_raw_secrets_blocks_mid_token_tab_in_base64() -> None:
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), "\t")
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(payload, [WRAP_CRED])


def test_contains_folded_catches_newline_plus_indent_in_base64() -> None:
    # Checker cycle-1 repro: a newline followed by 4-space indentation (an
    # RFC 5322 folded header, an indented log dump, a YAML/PEM block) still
    # evaded the line-break-only strip, since the strip removed only the
    # newline and left the indent spaces splitting the needle in two.
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), "\n    ")
    redactor = Redactor({"WRAP": WRAP_CRED})
    assert redactor.contains_folded(payload)


def test_assert_no_raw_secrets_blocks_newline_plus_indent_in_base64() -> None:
    payload = _mid_token_break(base64.b64encode(WRAP_CRED.encode()).decode(), "\n    ")
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(payload, [WRAP_CRED])


def test_contains_folded_catches_mime_76_char_wrapped_base64() -> None:
    # `base64.encodebytes` wraps at exactly 76 chars per line with a trailing
    # newline -- real MIME behaviour once the encoded form is longer than one
    # line (AT-599's second named case). A repeated secret is used so the
    # encoding actually exceeds 76 characters and gets wrapped at all.
    long_secret = WRAP_CRED * 3
    wrapped = base64.encodebytes(long_secret.encode()).decode()
    assert "\n" in wrapped  # sanity: the fixture really is wrapped
    redactor = Redactor({"WRAP": long_secret})
    assert redactor.contains_folded(wrapped)


def test_assert_no_raw_secrets_blocks_mime_76_char_wrapped_base64() -> None:
    long_secret = WRAP_CRED * 3
    wrapped = base64.encodebytes(long_secret.encode()).decode()
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets(wrapped, [long_secret])


def test_line_wrapped_benign_prose_has_no_false_positive() -> None:
    # AT-599's fix must not turn ordinary word-wrapped text into a bypass
    # report: text wrapped at a fixed width (as an email client or a terminal
    # would) has line breaks between plain words on both sides -- the same
    # shape the fix's line-unwrapped view has to tolerate without matching.
    prose = (
        "You are grading a student essay for clarity and structure. Respond "
        "with a JSON object containing a score between one and five and a "
        "short rationale explaining the grade in plain language for a parent."
    ) * 3
    wrapped = textwrap.fill(prose, width=76)
    assert "\n" in wrapped
    redactor = Redactor({"WRAP": WRAP_CRED})
    assert not redactor.contains_folded(wrapped)
    assert_no_raw_secrets(wrapped, [WRAP_CRED])  # must not raise


def test_space_separated_benign_prose_has_no_false_positive() -> None:
    # The `\s+` widening (cycle 2) collapses every space between ordinary
    # words too, not only line breaks -- this must not turn plain space-
    # separated prose into a bypass report.
    prose = (
        "Please  double   check the extracted grade level and subject "
        "before  saving   this record to the student's profile."
    )
    assert " " in prose
    redactor = Redactor({"WRAP": WRAP_CRED})
    assert not redactor.contains_folded(prose)
    assert_no_raw_secrets(prose, [WRAP_CRED])  # must not raise


def _make_corpus(n: int, seed: int = 4606) -> str:
    rng = random.Random(seed)  # AT-606: fixed seed, a reproducible bound
    out: list[str] = []
    total = 0
    while total < n:
        chunk = "".join(rng.choices(string.ascii_letters + string.digits + " .,\n", k=12))
        out.append(chunk)
        total += len(chunk)
    return "".join(out)[:n]


def _best_of(fn, repeats: int = 3) -> float:
    """Minimum wall time over a few repeats, to damp scheduler noise without
    hiding a real superlinear regression (which would be slow every time)."""
    return min(_timed(fn) for _ in range(repeats))


def _timed(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus() -> None:
    # AT-606: 518 KB of clean text took 11.8 s before the fix (superlinear).
    # 3 s is loose on purpose -- this pins "not superlinear any more", not a
    # tight performance target that would flake on a loaded machine.
    secrets = {f"KEY{i}": f"Sup3rS3cret{i}ValueZq7kP2x" for i in range(5)}
    redactor = Redactor(secrets)
    text = _make_corpus(500 * 1024)

    def run() -> None:
        redactor.contains_folded(text)
        assert_no_raw_secrets(text, list(secrets.values()))

    elapsed = _best_of(run, repeats=1)
    assert elapsed < 3.0, f"500 KB scan took {elapsed:.2f}s, expected under 3s"


def test_redact_scan_time_roughly_doubles_not_quadruples_with_input_size() -> None:
    # A superlinear (roughly quadratic) scan quadruples when the input
    # doubles; a linear one roughly doubles. The bound sits well below 4x so
    # it still catches a regression back to superlinear behaviour without
    # flaking on ordinary machine noise for a genuinely linear scan.
    secrets = {f"KEY{i}": f"Sup3rS3cret{i}ValueZq7kP2x" for i in range(5)}
    redactor = Redactor(secrets)
    small = _make_corpus(250 * 1024, seed=1)
    large = _make_corpus(500 * 1024, seed=2)

    small_time = _best_of(lambda: redactor.contains_folded(small))
    large_time = _best_of(lambda: redactor.contains_folded(large))

    ratio = large_time / max(small_time, 1e-6)
    assert ratio < 3.0, f"doubling input size took {ratio:.2f}x longer, expected roughly 2x"
