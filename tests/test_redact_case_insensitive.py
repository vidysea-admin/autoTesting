"""Redactor.scrub also masks a declared secret echoed in ANOTHER CASE (checker verdict
`run-error-text-evidence` F9: a secret `pass word 9` printed as `PASS WORD 9` stayed visible).

The case-insensitive pass is guarded so it never masks ordinary words: it applies only to a
value of at least `CI_MIN_LEN` characters that holds a non-letter, or `CI_MIN_LETTERS` (8, Umesh
2026-10-29; it was 12) letters when it is letters only. Exact-case masking is unchanged and
still floorless. Synthetic fake secrets only.
"""

from __future__ import annotations

from autotester.core.redact import MASK, Redactor


def test_secret_in_another_case_is_masked_with_its_key() -> None:
    red = Redactor({"APP_PASSWORD": "Tr0ub4dor&3x"})

    out = red.scrub("Wrong TR0UB4DOR&3X, also tr0ub4dor&3x and Tr0ub4dor&3x")

    assert "tr0ub4dor" not in out.lower()
    assert out.count(f"{MASK}:APP_PASSWORD") == 3


def test_secret_with_spaces_in_another_case_is_masked() -> None:
    out = Redactor({"K": "pass word 9"}).scrub("bad credential PASS WORD 9 here")

    assert "word" not in out.lower() and MASK in out


def test_unicode_case_variant_is_masked() -> None:
    out = Redactor({"K": "\u00dcn\u00efcode-Pw-7"}).scrub("echo \u00dcN\u00cfCODE-PW-7 end")

    assert "CODE-PW" not in out and MASK in out


def test_short_secret_stays_exact_case_only_so_ordinary_words_survive() -> None:
    red = Redactor({"K": "pass"})

    assert red.scrub("Passing PASS pass") == f"Passing PASS {MASK}:K"
    assert Redactor({"K": "admin12"}).scrub("ADMIN12 admin12") == f"ADMIN12 {MASK}:K"


def test_letters_only_secret_of_eight_or_more_is_masked_in_another_case() -> None:
    for secret, echo in [("sunshine", "bad SUNSHINE here"), ("mypassword", "got MyPassword now"),
                         ("password", "Password PASSWORD"), ("correcthorse", "say CorrectHorse")]:
        out = Redactor({"K": secret}).scrub(echo)

        assert secret[:5] not in out.lower() and MASK in out


def test_letters_only_secret_under_eight_keeps_exact_case_only() -> None:
    red = Redactor({"K": "welcome"})  # 7 letters: an ordinary word, so a case variant survives

    assert red.scrub("Welcome WELCOME welcome") == f"Welcome WELCOME {MASK}:K"


def test_exact_case_masking_is_unchanged_and_floorless() -> None:
    assert Redactor({"K": "ab"}).scrub("xab AB") == f"x{MASK}:K AB"
    assert Redactor({"K": "hunter2"}).scrub("pw hunter2") == f"pw {MASK}:K"


def test_scrub_obj_and_empty_inputs() -> None:
    red = Redactor({"K": "Tr0ub4dor&3x"})

    assert red.scrub_obj({"a": ["TR0UB4DOR&3X"]}) == {"a": [f"{MASK}:K"]}
    assert Redactor({}).scrub("TEXT") == "TEXT"
    assert red.scrub("") == ""
