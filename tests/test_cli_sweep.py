"""`autotester sweep stamp` (AT-699, living-ledger L11): the one append-only writer of the
checker's sweep log `qa/.last-sweep`.

Every test points `AUTOTESTER_ROOT` at a tmp tree, so the real log is never touched. The
sabotage the contract names (open with "w" instead of "a"; drop the empty-line refusal) turns the
append test and the refusal tests red respectively.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.cli_subapps import SUBAPPS

runner = CliRunner()
HISTORY = b"sweep one ok\r\nsweep two ok\r\nsweep three \xe2\x9c\x93 ok\r\n"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "qa").mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def _log(root: Path, content: bytes) -> Path:
    path = root / "qa" / ".last-sweep"
    path.write_bytes(content)
    return path


def _stamp(line: str):
    return runner.invoke(app, ["sweep", "stamp", line])


def test_stamp_appends_one_line_and_keeps_history_byte_identical(root: Path) -> None:
    path = _log(root, HISTORY)
    result = _stamp("x")
    assert result.exit_code == 0, result.output
    data = path.read_bytes()
    assert data[: len(HISTORY)] == HISTORY
    assert data[len(HISTORY):] == b"x\r\n"  # the file's own CRLF style
    assert len(data.splitlines()) == len(HISTORY.splitlines()) + 1


def test_stamp_keeps_lf_style_of_an_lf_log(root: Path) -> None:
    path = _log(root, b"a\nb\n")
    assert _stamp("c").exit_code == 0
    assert path.read_bytes() == b"a\nb\nc\n"


def test_stamp_after_a_log_with_no_final_newline_does_not_glue_lines(root: Path) -> None:
    path = _log(root, b"a\r\nb")
    assert _stamp("c").exit_code == 0
    assert path.read_bytes() == b"a\r\nb\r\nc\r\n"


@pytest.mark.parametrize("line", ["", " ", "   ", "\t", " \t "])
def test_empty_or_whitespace_line_is_refused_and_file_unchanged(root: Path, line: str) -> None:
    path = _log(root, HISTORY)
    result = _stamp(line)
    assert result.exit_code != 0
    assert path.read_bytes() == HISTORY


@pytest.mark.parametrize("line", ["a\nb", "a\r\nb", "x\n", "x\r", "a\u2028b"])
def test_multi_line_argument_is_refused_and_file_unchanged(root: Path, line: str) -> None:
    path = _log(root, HISTORY)
    result = _stamp(line)
    assert result.exit_code != 0
    assert path.read_bytes() == HISTORY


def test_missing_log_is_created_with_exactly_the_one_line(root: Path) -> None:
    result = _stamp("first")
    assert result.exit_code == 0, result.output
    assert (root / "qa" / ".last-sweep").read_bytes() == b"first\n"
    assert sorted(p.name for p in (root / "qa").iterdir()) == [".last-sweep"]


def test_refused_stamp_does_not_create_a_missing_log(root: Path) -> None:
    assert _stamp("  ").exit_code != 0
    assert not (root / "qa" / ".last-sweep").exists()


def test_repeated_stamps_accumulate_in_order(root: Path) -> None:
    path = _log(root, HISTORY)
    for text in ("one", "two", "three"):
        assert _stamp(text).exit_code == 0
    assert path.read_bytes() == HISTORY + b"one\r\ntwo\r\nthree\r\n"


def test_sweep_is_registered_in_subapps() -> None:
    assert "sweep" in [name for name, _ in SUBAPPS]
