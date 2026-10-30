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


def _fn(call: str) -> str:
    return f"def f(slug):\n    p = ProjectPaths(slug).dir / 'x'\n    {call}\n"


KINDS = {
    "write_text": "p.write_text('a')",
    "write_bytes": "p.write_bytes(b'a')",
    "unlink": "p.unlink()",
    "glob": "list(p.glob('*'))",
    "rglob": "list(p.rglob('*'))",
    "iterdir": "list(p.iterdir())",
    "exists": "p.exists()",
    "stat": "p.stat()",
    "open": "open(p, 'w')",
    "os.replace": "os.replace(p, p)",
    "shutil.rmtree": "shutil.rmtree(p)",
}


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_every_listed_call_on_a_project_path_in_stages_is_flagged(tmp_path: Path,
                                                                  kind: str) -> None:
    body = "import os\nimport shutil\n\n\n" + _fn(KINDS[kind])
    found = check_state_bypass(_repo(tmp_path, "stages/job.py", body))
    assert [v.rule for v in found] == [STATE_BYPASS]
    assert found[0].location.startswith("stages/job.py:")
    assert kind in found[0].detail


def test_the_falsifier_write_text_on_a_projectpaths_path_turns_doctor_red(tmp_path: Path) -> None:
    root = _repo(tmp_path, "stages/job.py", _fn("p.write_text('a')"))
    assert STATE_BYPASS in {v.rule for v in doctor.run(root)}


def test_a_read_is_not_flagged_a_write_mode_is(tmp_path: Path) -> None:
    read = _fn("open(p, 'r')\n    p.read_text()")
    assert check_state_bypass(_repo(tmp_path, "stages/job.py", read)) == []
    for call in ("open(p, mode='a')", "p.open('wb')"):
        assert len(check_state_bypass(_repo(tmp_path, "stages/job.py", _fn(call)))) == 1


@pytest.mark.parametrize("area", ["store", "browser"])
def test_store_and_browser_are_exempt(tmp_path: Path, area: str) -> None:
    assert check_state_bypass(_repo(tmp_path, f"{area}/job.py", _fn("p.write_text('a')"))) == []


def test_a_path_that_is_not_state_is_not_flagged(tmp_path: Path) -> None:
    body = ("import tempfile\nfrom pathlib import Path\n\n\ndef f():\n"
            "    scratch = Path(tempfile.mkdtemp()) / 'x'\n    scratch.write_text('a')\n")
    assert check_state_bypass(_repo(tmp_path, "stages/job.py", body)) == []


@pytest.mark.parametrize("expr, flagged", [
    ("repo_root() / '.work' / 'a.json'", True),
    ("repo_root() / 'projects' / 'p'", True),
    ("team_path('a.json')", True),
    ("repo_root() / 'docs' / 'a.md'", False),
])
def test_repo_root_is_state_only_under_work_or_projects(tmp_path: Path, expr: str,
                                                        flagged: bool) -> None:
    body = f"def f():\n    p = {expr}\n    p.write_text('a')\n"
    assert bool(check_state_bypass(_repo(tmp_path, "stages/job.py", body))) is flagged


def test_taint_follows_a_derived_name(tmp_path: Path) -> None:
    body = ("def f(slug):\n    a = ProjectPaths(slug)\n    b = a.dir / 'x'\n    c = b / 'y'\n"
            "    c.write_text('a')\n")
    assert len(check_state_bypass(_repo(tmp_path, "stages/job.py", body))) == 1


@pytest.mark.parametrize("rel", sorted({
    "core/trace.py", "stages/orchestrate_checkpoint.py", "auth/audit.py", "delivery/inbox.py",
    "stages/schedule_store.py", "core/env.py"}))
def test_state_persisting_modules_flag_any_path_a_caller_hands_them(tmp_path: Path,
                                                                    rel: str) -> None:
    body = "def f(path):\n    path.write_text('a')\n"
    assert len(check_state_bypass(_repo(tmp_path / "a", rel, body))) == 1
    assert check_state_bypass(_repo(tmp_path / "b", "stages/other.py", body)) == []


def _line(body: str, text: str) -> int:
    return body.splitlines().index(text) + 1 + len(HEAD.splitlines())


def test_a_baseline_row_allows_exactly_that_site_and_a_stale_row_is_reported(
        tmp_path: Path) -> None:
    body = _fn("p.write_text('a')")
    line = _line(body, "    p.write_text('a')")
    ok = f'"stages/job.py:{line}:write_text | U3a"'
    assert check_state_bypass(_repo(tmp_path, "stages/job.py", body, baseline=ok)) == []
    moved = f'"stages/job.py:{line + 1}:write_text | U3a"'
    rules = sorted(v.rule for v in check_state_bypass(
        _repo(tmp_path, "stages/job.py", body, baseline=moved)))
    assert rules == [STATE_BYPASS, STATE_BYPASS_STALE]
    extra = f'{ok}, "stages/zzz.py:9:unlink | U3a"'
    assert [v.rule for v in check_state_bypass(
        _repo(tmp_path, "stages/job.py", body, baseline=extra))] == [STATE_BYPASS_STALE]


def test_a_permanent_row_allows_a_host_check(tmp_path: Path) -> None:
    body = _fn("p.stat()")
    perm = f'"stages/job.py:{_line(body, "    p.stat()")}:stat | host device probe, not state"'
    assert check_state_bypass(_repo(tmp_path, "stages/job.py", body, permanent=perm)) == []


def test_this_repo_is_clean() -> None:
    assert check_state_bypass(code_root()) == []
