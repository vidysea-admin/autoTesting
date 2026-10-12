"""AT-780: heuristic PII masking in core.redact (email, phone, person-name fields)."""

from __future__ import annotations

import time

import pytest
from timing_scale import timing_scale

from autotester.core.redact import mask_name_value, mask_pii, mask_pii_obj


@pytest.mark.parametrize("raw", [
    "jane.doe+x@example.co.in", "mail me at a_b@sub.example.com please"])
def test_email_is_masked(raw: str) -> None:
    out = mask_pii(raw)
    assert "<email>" in out and "@" not in out


@pytest.mark.parametrize("raw", [
    "+91 98765 43210", "+91-9876543210", "919876543210", "9876543210", "09876543210",
    "+1 (415) 555-2671", "415-555-2671", "+44 20 7946 0958", "+971 50 123 4567"])
def test_phone_is_masked(raw: str) -> None:
    out = mask_pii(f"call {raw} now")
    assert "<phone>" in out and not any(ch.isdigit() for ch in out.replace("<phone>", ""))


@pytest.mark.parametrize("raw", [
    "2024", "10", "scholarships in Canada", "2024-10-07", "Class 12", "Rs 50000",
    "version 3.2.1", "ref 12345", "/students/42", "{{SECRET:PW}}", "[REDACTED]:PW"])
def test_non_pii_is_left_alone(raw: str) -> None:
    assert mask_pii(raw) == raw


@pytest.mark.parametrize("label", [
    "Name", "First name textbox", "Last Name", "Full name", "Student name", "Parent's name",
    "Guardian", "Student", "Father name", "Applicant first name", "surname", "Given name"])
def test_person_name_fields_mask_a_word_value(label: str) -> None:
    assert mask_name_value(label, "Rahul Sharma") == "<name>"


@pytest.mark.parametrize(("label", "value"), [
    ("Search", "Rahul Sharma"), ("Course name", "Data Science"), ("University name", "MIT"),
    ("File name", "report.pdf"), ("Student ID", "S1234"), ("Class", "10"),
    ("Student email", "x"), ("Name", "2024"), ("Name", "10"), ("Name", None),
    ("Name", "{{SECRET:PW}}"), ("Student", "[REDACTED]:K")])
def test_other_fields_and_non_word_values_are_not_masked(label: str, value: str | None) -> None:
    assert mask_name_value(label, value) == value


def test_mask_pii_obj_recurses_and_is_deterministic() -> None:
    obj = {"a": ["x@y.com", {"b": "+91 98765 43210"}], "n": 2024}
    first = mask_pii_obj(obj)
    assert first == {"a": ["<email>", {"b": "<phone>"}], "n": 2024}
    assert mask_pii_obj(obj) == first and mask_pii_obj(first) == first


# ---- AT-780 hardening (cycle 0): leaks, over-masking, linear time -------------------------

@pytest.mark.parametrize("raw", [
    "jane+promo@example.com", "josé@exämple.com", "अनु@example.com", "jane@münchen.de",
    "user@localhost", "ops@intranet", "a.b+c@sub.example.co.in."])
def test_email_variants_are_masked_whole(raw: str) -> None:
    out = mask_pii(f"mail {raw} now")
    assert out.startswith("mail <email>") and "@" not in out
    assert "jane+" not in out and "josé" not in out


@pytest.mark.parametrize("raw", ["price @ 5 pm", "ping @handle", "a @ b", "x@", "@", "me@ there"])
def test_non_emails_with_an_at_sign_survive(raw: str) -> None:
    assert mask_pii(raw) == raw


def test_many_emails_in_one_string() -> None:
    assert mask_pii("a@b.com, c@d.org;e@f.io") == "<email>, <email>;<email>"


@pytest.mark.parametrize("raw", [
    "0141-2345678", "011 2345 6789", "011-2345 6789", "011 23456789", "0120-4567890",
    "022 2345 6789", "(011) 2345 6789"])
def test_indian_std_landline_is_masked(raw: str) -> None:
    assert mask_pii(f"call {raw} now") == "call <phone> now"


@pytest.mark.parametrize("raw", [
    "98765 43210", "98765-43210", "98765.43210", "9876 543 210", "98 76 54 32 10",
    "98.76.54.32.10", "(98765) 43210", "[98765 43210]", "098765 43210", "+91 (98765) 43210",
    "(+91) 98765 43210", "+1.415.555.2671", "415.555.2671", "(415) 555 2671",
    "\u0969\u096e\u096d\u096c\u096b\u096a\u0969\u0968\u0967\u0966"])
def test_phone_written_with_dots_groups_or_brackets_is_masked(raw: str) -> None:
    out = mask_pii(f"tel {raw} ok")
    assert "<phone>" in out and not any(ch.isdigit() for ch in out), out
    assert "(" not in out and ")" not in out


def test_a_twelve_digit_run_is_not_partially_masked() -> None:
    assert mask_pii("id 123456789012 end") == "id 123456789012 end"
    assert mask_pii("id 12345678901234 end") == "id 12345678901234 end"


@pytest.mark.parametrize("raw", ["Rs 50000", "FY 2023-24", "1 2 3 4 5", "12.5 kg", "v 10.0.1.4"])
def test_short_numbers_survive_the_new_phone_patterns(raw: str) -> None:
    assert mask_pii(raw) == raw


@pytest.mark.parametrize("label", [
    "\u0928\u093e\u092e", "\u092a\u093f\u0924\u093e \u0915\u093e \u0928\u093e\u092e",
    "fname", "lname", "first_name", "firstName", "last_name", "FNAME", "Dad", "Mother", "Father",
    "guardian", "Mom", "Daddy", "\u092a\u093f\u0924\u093e",
    "\u091b\u093e\u0924\u094d\u0930 \u0915\u093e \u0928\u093e\u092e"])
def test_more_person_labels_mask_a_word_value(label: str) -> None:
    assert mask_name_value(label, "Rahul Sharma") == "<name>"


@pytest.mark.parametrize("label", [
    "Bank name", "Business name", "Plan name", "Course name", "University name",
    "Student country", "Student course", "Student type", "Name of university",
    "Name of the course", "Partner name", "Scholarship name", "Template name", "bank_name",
    "planName", "Guardian consent checkbox", "Counsellor dashboard",
    "\u0935\u093f\u0936\u094d\u0935\u0935\u093f\u0926\u094d\u092f\u093e\u0932\u092f "
    "\u0915\u093e \u0928\u093e\u092e",
    "\u0928\u093e\u092e\u093e\u0902\u0915\u0928 \u0938\u0902\u0916\u094d\u092f\u093e"])
def test_non_person_labels_are_not_masked(label: str) -> None:
    assert mask_name_value(label, "Data Science") == "Data Science"


@pytest.mark.parametrize("raw", [
    "https://x.com/p?email=jane.doe%40gmail.com&phone=%2B919876543210",
    "jane%40gmail.com", "a%2Bb%40x.org", "q=%2B91%2098765%2043210", "e=JANE%40GMAIL.COM"])
def test_at830_percent_encoded_email_and_phone_are_masked(raw: str) -> None:
    out = mask_pii(raw)
    assert "gmail" not in out.lower() and "x.org" not in out and "98765" not in out
    assert "<email>" in out or "<phone>" in out


def test_at830_percent_sign_text_is_left_alone() -> None:
    assert mask_pii("50%25 off, page=%2Bx") == "50%25 off, page=%2Bx"


_ADVERSARIAL = {
    "alnum_run": "a" * 200_000, "digit_run": "1" * 200_000, "dotted": "a." * 100_000,
    "dashed": "a-" * 100_000, "many_at": "a@" * 50_000,
    "one_at": "x" * 100_000 + "@" + "y" * 100_000, "digit_groups": ("9" * 9 + " ") * 20_000,
    "parens": "(" * 200_000, "plus_digits": "+" + "1" * 200_000,
}


@pytest.mark.parametrize("name", sorted(_ADVERSARIAL))
def test_mask_pii_is_linear_on_adversarial_input(name: str) -> None:
    raw = _ADVERSARIAL[name]
    start = time.perf_counter()
    mask_pii(raw)
    assert time.perf_counter() - start < 1.0 * timing_scale()
