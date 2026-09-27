"""Core utility tests. Redaction is a security control, so it is tested hardest.

Encoded/obfuscated-spelling regression tests (AT-347/AT-352/AT-356, three fix
cycles) live in test_redact_obfuscation.py; core.ids tests live in
test_ids.py -- both split out here in AT-352 cycle 3 when this file crossed
the C2 300-line cap.
"""

from __future__ import annotations

import pytest

from autotester.core.redact import (
    MASK,
    Redactor,
    assert_no_raw_secrets,
    has_placeholder,
    placeholder_keys,
)


def test_redactor_masks_secret_values_anywhere_in_text() -> None:
    redactor = Redactor({"PASSWORD": "hunter2trombone"})
    scrubbed = redactor.scrub("login failed for hunter2trombone at /login")
    assert "hunter2trombone" not in scrubbed
    assert MASK in scrubbed
    assert "PASSWORD" in scrubbed


def test_redactor_masks_longest_value_first() -> None:
    redactor = Redactor({"SHORT": "abcd", "LONG": "abcdefgh"})
    scrubbed = redactor.scrub("value=abcdefgh")
    assert "abcdefgh" not in scrubbed
    assert "LONG" in scrubbed


def test_redactor_walks_nested_structures() -> None:
    redactor = Redactor({"TOKEN": "s3cr3t-token"})
    payload = {"headers": {"auth": "Bearer s3cr3t-token"}, "list": ["s3cr3t-token"]}
    scrubbed = redactor.scrub_obj(payload)
    assert "s3cr3t-token" not in str(scrubbed)


def test_redactor_masks_even_very_short_declared_values() -> None:
    # AT-002: a declared value is known-exact, so no length floor applies.
    redactor = Redactor({"X": "ab"})
    assert "ab" not in redactor.scrub("token=ab")
    assert redactor.scrub("") == ""
    assert Redactor({"EMPTY": ""}).scrub("nothing to mask") == "nothing to mask"


def test_placeholder_helpers_find_secret_keys() -> None:
    text = "fill {{SECRET:PATHLYNKS_EMAIL}} then {{SECRET:PATHLYNKS_PASSWORD}}"
    assert has_placeholder(text)
    assert placeholder_keys(text) == ["PATHLYNKS_EMAIL", "PATHLYNKS_PASSWORD"]


def test_assert_no_raw_secrets_blocks_a_leaking_prompt() -> None:
    assert_no_raw_secrets("safe {{SECRET:PW}}", ["hunter2trombone"])
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets("password is hunter2trombone", ["hunter2trombone"])
