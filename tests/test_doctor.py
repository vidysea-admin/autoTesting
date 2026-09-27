"""The enforcement layer must actually catch the drift it claims to catch."""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester import doctor

try:
    import _winapi
except ImportError:  # not Windows
    _winapi = None


def make_repo(tmp_path: Path) -> Path:
    (tmp_path / "src" / "autotester").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    return tmp_path


def write_module(root: Path, name: str, body: str) -> None:
    (root / "src" / "autotester" / name).write_text(body, encoding="utf-8")


def write_pyproject(root: Path, dependencies: list[str]) -> None:
    deps = ",\n".join(f'    "{d}"' for d in dependencies)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "fixture"\ndependencies = [\n{deps}\n]\n', encoding="utf-8"
    )


def test_clean_repo_reports_nothing(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_module(root, "ok.py", "def small():\n    return 1\n")
    assert doctor.run(root) == []


def test_long_file_is_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_module(root, "big.py", "x = 1\n" * (doctor.MAX_FILE_LINES + 5))
    assert any(v.rule == "file-too-long" for v in doctor.run(root))


def test_the_line_cap_reads_every_file_c2_names_not_only_python(tmp_path: Path) -> None:
    """AT-419: C2 says "no file in src/ or tests/". Doctor measured only *.py, so a
    316-line visual_order.js printed "doctor: clean"."""
    root = make_repo(tmp_path)
    write_module(root, "browser.js", "x;\n" * (doctor.MAX_FILE_LINES + 1))
    fixtures = root / "tests" / "fixtures" / "site"
    fixtures.mkdir(parents=True)
    page = "<p>x</p>\n" * (doctor.MAX_FILE_LINES + 1)
    (fixtures / "page.html").write_text(page, encoding="utf-8")
    flagged = {v.location.replace("\\", "/") for v in doctor.run(root) if v.rule == "file-too-long"}
    assert flagged == {"src/autotester/browser.js", "tests/fixtures/site/page.html"}


def test_the_line_cap_allows_exactly_the_cap_and_skips_binary_files(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_module(root, "at_cap.js", "x;\n" * doctor.MAX_FILE_LINES)
    (root / "tests" / "shot.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe" + b"\n" * 400)
    assert not any(v.rule == "file-too-long" for v in doctor.run(root))


needs_junctions = pytest.mark.skipif(not hasattr(_winapi, "CreateJunction"),
                                     reason="Windows junctions only")


@needs_junctions
def test_the_line_cap_never_follows_a_junction_in_or_out_of_the_tree(tmp_path: Path) -> None:
    """AT-461: rglob walked junctions, so a loop crashed doctor (WinError 1921) and a
    junction to a foreign folder had that folder's files capped as if they were ours."""
    root = make_repo(tmp_path / "repo")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "big.txt").write_text("x\n" * (doctor.MAX_FILE_LINES + 100), encoding="utf-8")
    (root / "tests" / "loop").mkdir()
    _winapi.CreateJunction(str(root / "tests" / "loop"), str(root / "tests" / "loop" / "back"))
    _winapi.CreateJunction(str(outside), str(root / "tests" / "ext"))
    assert not any(v.rule == "file-too-long" for v in doctor.run(root))


@needs_junctions
def test_the_line_cap_still_walks_a_repo_opened_through_a_junction(tmp_path: Path) -> None:
    """The prune compares a directory with its RESOLVED parent, so a checkout reached
    through a junction is still ours, not a foreign tree."""
    real = make_repo(tmp_path / "real")
    (real / "tests" / "fixtures").mkdir()
    (real / "tests" / "fixtures" / "big.html").write_text("x\n" * (doctor.MAX_FILE_LINES + 1),
                                                          encoding="utf-8")
    _winapi.CreateJunction(str(real), str(tmp_path / "alias"))
    flagged = [v for v in doctor.run(tmp_path / "alias") if v.rule == "file-too-long"]
    assert [v.location.replace("\\", "/") for v in flagged] == ["tests/fixtures/big.html"]


def test_the_line_cap_skips_tool_cache_directories(tmp_path: Path) -> None:
    """AT-461: a gitignored .pytest_cache under tests/ is tooling output, not a file of ours."""
    root = make_repo(tmp_path)
    cache = root / "tests" / ".pytest_cache" / "v" / "cache"
    cache.mkdir(parents=True)
    (cache / "nodeids").write_text("t\n" * (doctor.MAX_FILE_LINES + 1), encoding="utf-8")
    assert not any(v.rule == "file-too-long" for v in doctor.run(root))


def test_long_function_is_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    body = "def huge():\n" + "    x = 1\n" * (doctor.MAX_FUNCTION_LINES + 5)
    write_module(root, "long_fn.py", body)
    assert any(v.rule == "function-too-long" for v in doctor.run(root))


def test_versioned_filename_is_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_module(root, "runner_v2.py", "x = 1\n")
    violations = doctor.run(root)
    assert any(v.rule == "drift-filename" for v in violations)


def test_duplicate_concept_across_modules_is_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_module(root, "a.py", "class Runner:\n    pass\n")
    write_module(root, "b.py", "class Runner:\n    pass\n")
    violations = doctor.run(root)
    assert any(v.rule == "duplicate-concept" for v in violations)


def test_root_clutter_is_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "_scratch_run.log").write_text("noise", encoding="utf-8")
    assert any(v.rule == "root-clutter" for v in doctor.run(root))


def test_a_second_ai_tools_instruction_file_is_not_root_clutter(tmp_path: Path) -> None:
    """AT-283: AGENTS.md is a real project-instruction surface (parallel to CLAUDE.md
    for a different AI tool), not scratch — it must not trip the same gate a stray
    log file does."""
    root = make_repo(tmp_path)
    (root / "AGENTS.md").write_text("# instructions\n", encoding="utf-8")
    assert not any(v.rule == "root-clutter" for v in doctor.run(root))


# -- check_dependencies_declared (AT-130) --------------------------------------
# `pytest` is used as the "undeclared third-party import" fixture below because it
# is guaranteed installed (this file needs it to run) yet is never in
# [project].dependencies (it is a dev-group tool) -- a stand-in for the real bug,
# `google-genai` resolving only via `langchain-google-genai`'s transitive pin.


def test_undeclared_third_party_import_is_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "uses_pytest.py", "import pytest\n\n\ndef f():\n    return pytest\n")
    violations = [v for v in doctor.run(root) if v.rule == "undeclared-dependency"]
    assert any("uses_pytest.py" in v.location for v in violations)


def test_declared_third_party_import_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_pyproject(root, ["pytest"])
    write_module(root, "uses_pytest.py", "import pytest\n\n\ndef f():\n    return pytest\n")
    assert not any(v.rule == "undeclared-dependency" for v in doctor.run(root))


def test_a_lazy_import_inside_a_function_body_is_still_caught(tmp_path: Path) -> None:
    """The real AT-130 import was never module-level -- GeminiProvider imports
    `google.genai` lazily inside `_structured` so the SDK loads only when a provider
    call actually runs (test_providers.py: "both SDKs are imported lazily ... so
    these tests never need a real API key or a socket"). A check that only read
    module-level imports would have missed the exact bug it exists to catch."""
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "lazy.py", "def f():\n    import pytest\n    return pytest\n")
    violations = [v for v in doctor.run(root) if v.rule == "undeclared-dependency"]
    assert any("lazy.py" in v.location for v in violations)


def test_stdlib_imports_are_never_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "stdlib_user.py", "import os\nimport json\nfrom pathlib import Path\n")
    assert not any(v.rule == "undeclared-dependency" for v in doctor.run(root))


def test_own_package_imports_are_never_flagged(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "a.py", "def a():\n    return 1\n")
    write_module(root, "b.py", "from autotester.a import a\n")
    assert not any(v.rule == "undeclared-dependency" for v in doctor.run(root))


def test_an_import_the_environment_cannot_resolve_is_not_this_checks_job(tmp_path: Path) -> None:
    """A typo'd or genuinely-missing module is caught by `import` itself at runtime --
    this check only catches the "installed but undeclared" hazard."""
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "typo.py", "import totally_fake_module_xyz_at130\n")
    assert not any(v.rule == "undeclared-dependency" for v in doctor.run(root))


def test_no_pyproject_is_not_this_checks_job(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write_module(root, "uses_pytest.py", "import pytest\n")
    assert not any(v.rule == "undeclared-dependency" for v in doctor.run(root))


# -- AT-590: TYPE_CHECKING-only and try/except-optional imports are soft --------
# The false-positive AT-130's own checker found: an installed-but-undeclared package
# guarded by `if TYPE_CHECKING:` or `try/except ImportError` is a deliberate optional,
# not a transitive accident, and must not get the hard-import "add the direct
# package" advice.

_SOFT_IMPORT_SHAPES = [
    pytest.param("from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n"
                 "    import pytest\n", id="type_checking_bare"),
    pytest.param("import typing\n\nif typing.TYPE_CHECKING:\n"
                 "    import pytest\n", id="type_checking_dotted"),
    pytest.param("from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n"
                 "    if True:\n        import pytest\n", id="nested_in_type_checking"),
    pytest.param("try:\n    import pytest\nexcept ImportError:\n"
                 "    pytest = None\n", id="try_except_import_error"),
    pytest.param("try:\n    import pytest\nexcept ModuleNotFoundError:\n"
                 "    pytest = None\n", id="try_except_module_not_found_error"),
    pytest.param("try:\n    import pytest\nexcept (ImportError, ModuleNotFoundError):\n"
                 "    pytest = None\n", id="try_except_tuple_of_both"),
    pytest.param("try:\n    if True:\n        import pytest\nexcept ImportError:\n"
                 "    pytest = None\n", id="nested_in_try_except"),
]


@pytest.mark.parametrize("body", _SOFT_IMPORT_SHAPES)
def test_soft_import_guard_shapes_are_not_flagged(tmp_path: Path, body: str) -> None:
    """AT-590: each guard shape, including an import nested inside it, is exempt."""
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "opt.py", body)
    assert not any(v.rule == "undeclared-dependency" for v in doctor.run(root))


_LOOKS_LIKE_A_GUARD_BUT_IS_HARD = [
    pytest.param("from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    pass\n"
                 "else:\n    import pytest\n", id="type_checking_else_branch"),
    pytest.param("try:\n    x = 1\nexcept ImportError:\n    x = 2\n"
                 "import pytest\n", id="after_the_try_block"),
    pytest.param("try:\n    import pytest\nexcept Exception:\n"
                 "    pytest = None\n", id="except_exception_too_broad"),
    pytest.param("try:\n    import pytest\nexcept:\n"
                 "    pytest = None\n", id="bare_except_too_broad"),
    pytest.param("try:\n    import pytest\nexcept ImportError:\n    raise\n",
                 id="reraise"),
    pytest.param("try:\n    import pytest\nexcept ImportError as e:\n"
                 "    raise RuntimeError('pip install pytest') from e\n",
                 id="raise_from"),
    pytest.param("import sys\n\ntry:\n    import pytest\nexcept ImportError:\n"
                 "    sys.exit('need pytest')\n", id="sys_exit"),
]


@pytest.mark.parametrize("body", _LOOKS_LIKE_A_GUARD_BUT_IS_HARD)
def test_shapes_that_look_like_a_guard_but_are_not_stay_hard(tmp_path: Path, body: str) -> None:
    """AT-590's required behaviour: an else/after-try import, or a handler broader
    than ImportError/ModuleNotFoundError, does not prove the failure was a missing
    package -- neither qualifies as soft. AT-619: nor does a handler that re-raises,
    raises a new error, or exits -- that is a required-dependency guard, not a
    graceful degrade -- so all stay flagged, end to end through doctor.run."""
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "opt.py", body)
    violations = [v for v in doctor.run(root) if v.rule == "undeclared-dependency"]
    assert any("opt.py" in v.location for v in violations)


def test_a_hard_import_alongside_a_soft_one_in_the_same_file_is_still_flagged(
        tmp_path: Path) -> None:
    """AT-590's regression pin: the guard-shape carve-out must not go blind to a
    genuinely hard undeclared import living in the same file as a soft one."""
    root = make_repo(tmp_path)
    write_pyproject(root, [])
    write_module(root, "mixed.py",
                 "from typing import TYPE_CHECKING\n\n"
                 "if TYPE_CHECKING:\n"
                 "    import pytest\n\n"
                 "import pytest\n")
    violations = [v for v in doctor.run(root) if v.rule == "undeclared-dependency"]
    assert len(violations) == 1
    assert "mixed.py" in violations[0].location


def test_the_real_repo_declares_every_third_party_import_it_makes() -> None:
    """Direct regression proof for AT-130: run the check against this actual repo, not
    a fixture -- clean now that both `google-genai` and `starlette` (the second live
    instance this check found) are declared."""
    assert doctor.check_dependencies_declared(doctor.repo_root()) == []
