"""mongo-store M16: the doctor rule that fails a raw filesystem call on a state path.

Each case builds a tiny repo (`src/autotester/<dir>/<module>.py`, optional `pyproject.toml`
baseline) and runs `check_state_bypass` on it; the last case runs the rule on this real tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autotester import doctor
from autotester.core.paths import code_root
from autotester.ledger.committed_fresh import STATE_BYPASS, STATE_BYPASS_STALE, check_state_bypass

HEAD = "from autotester.core.paths import ProjectPaths, repo_root, team_path\n\n\n"


def _repo(tmp_path: Path, rel: str, body: str, baseline: str = "", permanent: str = "") -> Path:
    module = tmp_path / "src" / "autotester" / rel
    module.parent.mkdir(parents=True, exist_ok=True)  # also creates tmp_path itself
    module.write_text(HEAD + body, encoding="utf-8")
    table = ""
    if baseline or permanent:
        table = ("[tool.autotester.doctor.state-bypass]\n"
                 f"baseline = [{baseline}]\npermanent = [{permanent}]\n")
    (tmp_path / "pyproject.toml").write_text(table, encoding="utf-8")
    return tmp_path


def _fn(call: str, imports: str = "") -> str:
    return f"{imports}def f(slug):\n    p = ProjectPaths(slug).dir / 'x'\n    {call}\n"


def _found(tmp_path: Path, body: str, rel: str = "stages/job.py") -> list[str]:
    return [v.rule for v in check_state_bypass(_repo(tmp_path, rel, body))]


KINDS = {
    "write_text": "p.write_text('a')",
    "write_bytes": "p.write_bytes(b'a')",
    "unlink": "p.unlink()",
    "glob": "list(p.glob('*'))",
    "rglob": "list(p.rglob('*'))",
    "iterdir": "list(p.iterdir())",
    "exists": "p.exists()",
    "stat": "p.stat()",
    "mkdir": "p.mkdir(parents=True)",
    "touch": "p.touch()",
    "rename": "p.rename(p)",
    "rmdir": "p.rmdir()",
    "open": "open(p, 'w')",
    "os.replace": "os.replace(p, p)",
    "os.makedirs": "os.makedirs(p)",
    "os.listdir": "os.listdir(p)",
    "os.path.exists": "os.path.exists(p)",
    "shutil.rmtree": "shutil.rmtree(p)",
    "shutil.copyfile": "shutil.copyfile('a', p)",
}


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_every_listed_call_on_a_project_path_in_stages_is_flagged(tmp_path: Path,
                                                                  kind: str) -> None:
    body = "import os\nimport shutil\n\n\n" + _fn(KINDS[kind])
    found = check_state_bypass(_repo(tmp_path, "stages/job.py", body))
    assert [v.rule for v in found] == [STATE_BYPASS]
    assert found[0].location.startswith("stages/job.py:")
    assert f"`{kind}`" in found[0].detail


ALIASED = {
    "import os as o": "o.replace(p, p)",
    "import shutil as sh": "sh.rmtree(p)",
    "from shutil import copyfile": "copyfile('a', p)",
    "from shutil import rmtree as rt": "rt(p)",
    "from os import remove": "remove(p)",
    "from os import makedirs as mk": "mk(p)",
    "from os import path as osp": "osp.exists(p)",
    "import os.path": "os.path.isfile(p)",
}


@pytest.mark.parametrize("imp", sorted(ALIASED))
def test_an_import_alias_does_not_hide_a_raw_call(tmp_path: Path, imp: str) -> None:
    assert _found(tmp_path, _fn(ALIASED[imp], imports=imp + "\n\n\n")) == [STATE_BYPASS]


def test_an_import_of_something_else_is_not_mistaken_for_os(tmp_path: Path) -> None:
    body = _fn("remove(p)", imports="from mylib import remove\n\n\n")
    assert _found(tmp_path, body) == []


@pytest.mark.parametrize("body, flagged", [
    ("def f(slug):\n    a, b = ProjectPaths(slug).dir, 5\n    a.write_text('x')\n", 1),
    ("def f(slug):\n    a, b = 5, ProjectPaths(slug).dir\n    a.write_text('x')\n", 0),  # clean
    ("def f(slug):\n    a, b = ProjectPaths(slug).dir\n    b.write_text('x')\n", 1),  # whole
    ("def f(slug):\n    for q in ProjectPaths(slug).dir.glob('*'):\n        q.unlink()\n", 2),
    ("def f(slug):\n    with ProjectPaths(slug).dir as d:\n        d.touch()\n", 1),
    ("def f(slug):\n    return [q.unlink() for q in ProjectPaths(slug).dir.glob('*')]\n", 2),
    ("def where(slug):\n    return ProjectPaths(slug).dir / 'x'\n\n\n"
     "def f(slug):\n    d = where(slug)\n    (d / 'a').write_text('x')\n", 1),
], ids=["tuple", "clean-tuple-element", "whole-unpack", "for", "with", "comprehension", "helper"])
def test_taint_follows_unpacking_loops_with_and_a_helper_that_returns_a_path(
        tmp_path: Path, body: str, flagged: int) -> None:
    assert len(_found(tmp_path, body)) == flagged  # a `for` over a glob flags the glob as well


def test_an_unknown_open_mode_counts_as_a_write_and_a_read_does_not(tmp_path: Path) -> None:
    unknown = _fn("open(p, mode)").replace("(slug)", "(slug, mode)")
    assert _found(tmp_path, unknown) == [STATE_BYPASS]
    assert _found(tmp_path, _fn("open(p)")) == []
    assert _found(tmp_path, _fn("open(p, 'r')\n    p.read_text()")) == []
    for call in ("open(p, mode='a')", "p.open('wb')"):
        assert _found(tmp_path, _fn(call)) == [STATE_BYPASS]


def test_the_falsifier_write_text_on_a_projectpaths_path_turns_doctor_red(tmp_path: Path) -> None:
    root = _repo(tmp_path, "stages/job.py", _fn("p.write_text('a')"))
    assert STATE_BYPASS in {v.rule for v in doctor.run(root)}


@pytest.mark.parametrize("area", ["store", "browser"])
def test_store_and_browser_are_exempt(tmp_path: Path, area: str) -> None:
    assert check_state_bypass(_repo(tmp_path, f"{area}/job.py", _fn("p.write_text('a')"))) == []


def test_a_path_that_is_not_state_is_not_flagged(tmp_path: Path) -> None:
    body = ("import tempfile\nfrom pathlib import Path\n\n\ndef f():\n"
            "    scratch = Path(tempfile.mkdtemp()) / 'x'\n    scratch.write_text('a')\n"
            "    scratch.mkdir()\n")
    assert _found(tmp_path, body) == []


@pytest.mark.parametrize("expr, flagged", [
    ("repo_root() / '.work' / 'a.json'", True),
    ("repo_root() / 'projects' / 'p'", True),
    ("team_path('a.json')", True),
    ("repo_root() / 'docs' / 'a.md'", False),
])
def test_repo_root_is_state_only_under_work_or_projects(tmp_path: Path, expr: str,
                                                        flagged: bool) -> None:
    body = f"def f():\n    p = {expr}\n    p.write_text('a')\n"
    assert bool(_found(tmp_path, body)) is flagged


def test_taint_follows_a_derived_name(tmp_path: Path) -> None:
    body = ("def f(slug):\n    a = ProjectPaths(slug)\n    b = a.dir / 'x'\n    c = b / 'y'\n"
            "    c.write_text('a')\n")
    assert len(_found(tmp_path, body)) == 1


@pytest.mark.parametrize("rel", sorted({
    "core/trace.py", "stages/orchestrate_checkpoint.py", "auth/audit.py", "delivery/inbox.py",
    "stages/schedule_store.py", "core/env.py"}))
def test_state_persisting_modules_flag_any_path_a_caller_hands_them(tmp_path: Path,
                                                                    rel: str) -> None:
    body = "def f(path):\n    path.write_text('a')\n"
    assert len(check_state_bypass(_repo(tmp_path / "a", rel, body))) == 1
    assert check_state_bypass(_repo(tmp_path / "b", "stages/other.py", body)) == []


def _row(rel: str, func: str, kind: str, owner: str = "U3d") -> str:
    return f'"{rel}:{func}:{kind} | {owner}"'


def test_a_baseline_row_allows_that_site_wherever_its_line_moves(tmp_path: Path) -> None:
    body = _fn("p.write_text('a')")
    row = _row("stages/job.py", "f", "write_text")
    assert check_state_bypass(_repo(tmp_path, "stages/job.py", body, baseline=row)) == []
    shifted = "# an unrelated comment\n# and another\n" + body
    assert check_state_bypass(_repo(tmp_path, "stages/job.py", shifted, baseline=row)) == []


def test_a_row_for_another_function_or_kind_does_not_allow_the_site(tmp_path: Path) -> None:
    body = _fn("p.write_text('a')")
    for row in (_row("stages/job.py", "g", "write_text"), _row("stages/job.py", "f", "unlink")):
        rules = sorted(v.rule for v in check_state_bypass(
            _repo(tmp_path, "stages/job.py", body, baseline=row)))
        assert rules == [STATE_BYPASS, STATE_BYPASS_STALE]


def test_a_row_counts_sites_and_a_stale_row_is_reported(tmp_path: Path) -> None:
    body = _fn("p.write_text('a')\n    p.write_text('b')")
    row = _row("stages/job.py", "f", "write_text")
    one = check_state_bypass(_repo(tmp_path, "stages/job.py", body, baseline=row))
    assert [v.rule for v in one] == [STATE_BYPASS]  # two sites, one row: the second is flagged
    two = _repo(tmp_path, "stages/job.py", body, baseline=f"{row}, {row}")
    assert check_state_bypass(two) == []
    three = f"{row}, {row}, {row}"
    assert [v.rule for v in check_state_bypass(
        _repo(tmp_path, "stages/job.py", body, baseline=three))] == [STATE_BYPASS_STALE]
    gone = _fn("pass")
    assert [v.rule for v in check_state_bypass(
        _repo(tmp_path, "stages/job.py", gone, baseline=row))] == [STATE_BYPASS_STALE]


def test_a_method_and_a_module_level_call_get_their_own_scope_names(tmp_path: Path) -> None:
    body = ("class K:\n    def m(self, slug):\n        ProjectPaths(slug).dir.write_text('a')\n\n\n"
            "ProjectPaths('s').dir.write_text('b')\n")
    rows = ", ".join(_row("stages/job.py", scope, "write_text") for scope in ("K.m", "<module>"))
    assert check_state_bypass(_repo(tmp_path, "stages/job.py", body, baseline=rows)) == []


def test_a_permanent_row_allows_a_host_check(tmp_path: Path) -> None:
    perm = '"stages/job.py:f:stat | host device probe, not state"'
    repo = _repo(tmp_path, "stages/job.py", _fn("p.stat()"), permanent=perm)
    assert check_state_bypass(repo) == []


def test_this_repo_is_clean() -> None:
    assert check_state_bypass(code_root()) == []
