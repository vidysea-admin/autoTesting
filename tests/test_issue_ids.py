"""AT-676 / AT-645: duplicate issue ids are refused on write and reported on check."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from autotester.ledger import issue_ids

ROOT = Path(__file__).resolve().parents[1]


def _ledger(root: Path, rows: list[dict], grandfather: list[dict] | None = None) -> Path:
    (root / "qa").mkdir(parents=True, exist_ok=True)
    path = root / "qa" / "issues.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    if grandfather is not None:
        (root / issue_ids.GRANDFATHER).write_text(json.dumps(grandfather), encoding="utf-8")
    return path


def test_append_refuses_duplicate_and_names_free_id(tmp_path: Path) -> None:
    path = _ledger(tmp_path, [{"id": "AT-5", "title": "a"}])
    with pytest.raises(ValueError, match="AT-6"):
        issue_ids.append_issue(path, {"id": "AT-5", "title": "b"})
    issue_ids.append_issue(path, {"id": issue_ids.next_issue_id(issue_ids.read_rows(path)),
                                  "title": "b"})
    assert [r["id"] for r in issue_ids.read_rows(path)] == ["AT-5", "AT-6"]


def test_check_flags_new_duplicate(tmp_path: Path) -> None:
    _ledger(tmp_path, [{"id": "AT-1", "title": "a"}, {"id": "AT-1", "title": "b"}])
    found = issue_ids.check_issue_id_unique(tmp_path)
    assert [v.rule for v in found] == ["issue-id-duplicate"]


def test_grandfathered_pair_is_skipped_but_a_third_row_is_not(tmp_path: Path) -> None:
    old = [{"id": "AT-1", "title": "a"}, {"id": "AT-1", "title": "b"}]
    _ledger(tmp_path, old, grandfather=old)
    assert issue_ids.check_issue_id_unique(tmp_path) == []
    _ledger(tmp_path, [*old, {"id": "AT-1", "title": "c"}])
    assert len(issue_ids.check_issue_id_unique(tmp_path)) == 1


def test_stale_grandfather_entries_are_harmless(tmp_path: Path) -> None:
    _ledger(tmp_path, [{"id": "AT-1", "title": "a"}], grandfather=[{"id": "AT-9", "title": "z"}])
    assert issue_ids.check_issue_id_unique(tmp_path) == []


def test_migration_renumbers_later_rows_on_a_copy(tmp_path: Path, capsys) -> None:
    spec = importlib.util.spec_from_file_location(
        "renumber", ROOT / "scripts" / "renumber_duplicate_issue_ids.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = [{"id": "AT-1", "title": "a"}, {"id": "AT-2", "title": "x"},
            {"id": "AT-1", "title": "b"}]
    path = _ledger(tmp_path, rows, grandfather=[{"id": "AT-1", "title": "b"}])
    before = path.read_text(encoding="utf-8")
    assert mod.main(["--dry-run", "--path", str(path)]) == 0
    assert path.read_text(encoding="utf-8") == before
    assert "AT-1 -> AT-3" in capsys.readouterr().out
    gf = tmp_path / issue_ids.GRANDFATHER
    assert mod.main(["--path", str(path), "--grandfather", str(gf)]) == 0
    assert [r["id"] for r in issue_ids.read_rows(path)] == ["AT-1", "AT-2", "AT-3"]
    assert json.loads(gf.read_text(encoding="utf-8")) == []
    assert issue_ids.check_issue_id_unique(tmp_path) == []


def test_real_ledger_has_no_ungrandfathered_duplicates() -> None:
    assert issue_ids.check_issue_id_unique(ROOT) == []
