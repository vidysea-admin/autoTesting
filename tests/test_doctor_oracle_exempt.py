"""The G11 oracle plug-in contract vs two doctor rules (DOE1, DOE2).

`stages/oracle_<OracleName value>.py` must expose a top-level `run`, and `OracleName.COPY_LINT`
fixes one stem that contains `_copy`. These tests pin the narrow exemptions AND that every other
case of the same two rules stays red. (A separate file: tests/test_doctor.py sits at C2's cap.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester import doctor
from autotester.schema.multi_role_enums import OracleName


def make_repo(tmp_path: Path) -> Path:
    (tmp_path / "src" / "autotester" / "stages").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    return tmp_path


def put(root: Path, rel: str, body: str = "x = 1\n") -> None:
    (root / "src" / "autotester" / rel).write_text(body, encoding="utf-8")


def rules(violations: list[doctor.Violation], rule: str) -> list[doctor.Violation]:
    return [v for v in violations if v.rule == rule]


RUN = "def run(context):\n    return []\n"


def test_every_oracle_stem_passes_the_filename_rule_with_no_hand_list(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    for oracle in OracleName:
        put(root, f"stages/oracle_{oracle.value}.py")
    assert OracleName.COPY_LINT.value == "copy_lint"
    assert (root / "src/autotester/stages/oracle_copy_lint.py").exists()
    assert doctor.check_file_names(root) == []


@pytest.mark.parametrize("name", [
    "foo_copy", "oracle_notreal_copy", "oracle_copy_lint_copy", "oracle_copy_lint_v2",
    "oracle_tenant_new", "xoracle_copy_lint",
])
def test_every_other_banned_name_stays_red(tmp_path: Path, name: str) -> None:
    root = make_repo(tmp_path)
    put(root, f"stages/{name}.py")
    flagged = rules(doctor.check_file_names(root), "drift-filename")
    assert [Path(v.location).name for v in flagged] == [f"{name}.py"]


def test_run_in_oracle_modules_is_not_a_duplicate_of_doctor_run(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    put(root, "doctor.py", RUN)
    for oracle in OracleName:
        put(root, f"stages/oracle_{oracle.value}.py", RUN)
    assert doctor.check_duplicate_definitions(root) == []


def test_run_in_oracle_modules_is_exempt_whichever_module_is_seen_first(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    put(root, "stages/oracle_mailbox.py", RUN)
    put(root, "zzz_last.py", RUN)
    put(root, "aaa_first.py", "x = 1\n")
    assert doctor.check_duplicate_definitions(root) == []


def test_run_in_two_non_oracle_modules_still_collides(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    put(root, "a.py", RUN)
    put(root, "b.py", RUN)
    put(root, "stages/oracle_mailbox.py", RUN)
    assert len(rules(doctor.check_duplicate_definitions(root), "duplicate-concept")) == 1


@pytest.mark.parametrize("rel", ["stages/oracle_notreal.py", "stages/runner.py",
                                 "oracle_mailbox.py"])
def test_run_outside_a_real_oracle_module_still_collides(tmp_path: Path, rel: str) -> None:
    root = make_repo(tmp_path)
    put(root, "doctor.py", RUN)
    put(root, rel, RUN)
    assert len(rules(doctor.check_duplicate_definitions(root), "duplicate-concept")) == 1


def test_other_names_in_oracle_modules_still_collide(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    put(root, "a.py", "class Finder:\n    pass\n")
    put(root, "stages/oracle_mailbox.py", "class Finder:\n    pass\n" + RUN)
    assert len(rules(doctor.check_duplicate_definitions(root), "duplicate-concept")) == 1
