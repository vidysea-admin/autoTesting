"""T-209 fix cycle 1 (multi-role-platform.md MP9, MPI1): opaque record ids never survive in a URL.

All ids below are synthetic. One shared predicate (`segment_is_id_like`) drives BOTH
`stages.leak_evidence.templatise_url` and `schema.leak_evidence.validate_url_template`, so a raw id
that slips past the first is refused by the second. Also: `finding_id` cannot steer the screenshot
path out of the run directory, and a validation error never echoes the raw input.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.schema.leak_evidence import LeakEvidence, validate_url_template
from autotester.schema.multi_role_enums import FindingClass
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.stages import leak_evidence as stage

HOST = "https://a.example.test"
ID_FORMATS = {
    "nanoid-21": "V1StGXR8_Z5jdHi6B-myT",
    "base62-22": "aZ3kLm9QpR2tUvWx4YbC7d",
    "stripe-like": "cus_Nffrf7JkLm3pQw",
    "cuid2": "tz4a98xxat96iws9zmbrgj3a",
    "ulid": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "objectid": "507f1f77bcf86cd799439011",
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "numeric": "90210",
    "letters-only-22": "abcdefghijklmnopqrstuv",
    "unknown-word": "zorblax-quimby",
}
ROUTE_WORDS = ["students", "profile", "settings", "api", "v1"]


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(stage.LEAK_KEY_ENV, "synthetic-master-key-for-tests")


@pytest.mark.parametrize("raw", ID_FORMATS.values(), ids=ID_FORMATS.keys())
def test_templatise_turns_every_id_format_into_a_placeholder(raw: str) -> None:
    out = stage.templatise_url(f"{HOST}/students/{raw}/profile")
    assert out == f"{HOST}/students/{{id}}/profile"
    assert raw not in out


@pytest.mark.parametrize("raw", ID_FORMATS.values(), ids=ID_FORMATS.keys())
def test_validate_url_template_refuses_every_raw_id_format(raw: str) -> None:
    with pytest.raises(ValueError):
        validate_url_template(f"/students/{raw}")
    with pytest.raises(ValidationError):
        LeakEvidence(foreign_row_count=1, field_names=["Name"], url_template=f"/students/{raw}")
    validate_url_template("/students/{id}")  # the placeholder form is accepted


@pytest.mark.parametrize("raw", ID_FORMATS.values(), ids=ID_FORMATS.keys())
def test_no_id_format_reaches_the_file_write_finding_writes(tmp_path: Path, raw: str) -> None:
    rows = [{"id": raw, "Name": "Pupil Canary"}]
    ev = stage.collect_leak_evidence(
        project_slug="demo", run_dir=tmp_path, finding_id="leak-1", rows=rows, id_field="id",
        url=f"{HOST}/students/{raw}")
    finding = MultiRoleFinding(
        finding_id="leak-1", finding_class=FindingClass.DATA_LEAK, title="t", role="Parent",
        platform_id="parent", url_template=ev.url_template, count=1,
        steps=["login as Parent"], leak_evidence=ev)
    written = stage.write_finding(tmp_path, finding)
    assert raw not in written.read_text(encoding="utf-8")


def test_plain_route_words_are_kept() -> None:
    url = "/" + "/".join(ROUTE_WORDS)
    assert stage.templatise_url(f"{HOST}{url}") == f"{HOST}{url}"
    assert validate_url_template(url) == url


def test_query_string_values_do_not_survive() -> None:
    out = stage.templatise_url(f"{HOST}/api/v1/students?token=Zx9secret&q=Zorblax&page=2")
    assert out == f"{HOST}/api/v1/students?token={{value}}&q={{value}}&page={{value}}"
    for leaked in ("Zx9secret", "Zorblax"):
        assert leaked not in out
        with pytest.raises(ValueError):
            validate_url_template(f"/students?token={leaked}")


@pytest.mark.parametrize("bad", ["../escape", "a/b", "..\\x", "Upper", "", "x" * 80, "a.b"])
def test_finding_id_is_a_safe_slug(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        stage.collect_leak_evidence(
            project_slug="demo", run_dir=tmp_path / "run", finding_id=bad, rows=[{"id": "1"}],
            id_field="id", url="/students", screenshot_png=b"not-a-real-png")
    assert not (tmp_path / "escape").exists() and not (tmp_path / "run").exists()


def test_screenshot_destination_must_stay_inside_the_run_dir(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stage, "SCREENSHOT_DIR", "../outside")
    with pytest.raises(ValueError):
        stage.collect_leak_evidence(
            project_slug="demo", run_dir=tmp_path / "run", finding_id="leak-1",
            rows=[{"id": "1"}], id_field="id", url="/students", screenshot_png=b"x")
    assert not (tmp_path / "outside").exists()


def test_validation_errors_never_echo_the_raw_input() -> None:
    raw = ID_FORMATS["stripe-like"]
    with pytest.raises(ValidationError) as caught:
        LeakEvidence(foreign_row_count=1, field_names=["Name"], url_template=f"/students/{raw}")
    assert raw not in str(caught.value)
    with pytest.raises(ValidationError) as found:
        MultiRoleFinding(
            finding_id="leak-1", finding_class=FindingClass.DATA_LEAK, title="t", role="Parent",
            platform_id="parent", url_template=f"/students/{raw}", count=1, steps=["login as P"])
    assert raw not in str(found.value)
