"""AT-780: heuristic PII masking in core.redact (email, phone, person-name fields)."""

from __future__ import annotations

import pytest

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
