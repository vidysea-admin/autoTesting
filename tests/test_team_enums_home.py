"""TF8 (team-foundation.md): one home for the Group 10 vocabularies.

`schema/team_enums.py` holds the team closed value sets; `schema/enums.py` holds every older one.
No enum is defined in both, and a stage never re-types a team value as a bare string literal.
"""

from __future__ import annotations

import ast
import enum
from pathlib import Path

from autotester.schema import enums, team_enums

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"


def _enums_of(module) -> dict[str, frozenset[str]]:
    return {name: frozenset(m.value for m in obj)
            for name, obj in vars(module).items()
            if isinstance(obj, type) and issubclass(obj, enum.Enum)
            and obj.__module__ == module.__name__}


def test_no_enum_is_defined_in_both_vocabulary_files() -> None:
    old, new = _enums_of(enums), _enums_of(team_enums)
    assert new, "team_enums.py defines no vocabulary"
    assert not old.keys() & new.keys(), sorted(old.keys() & new.keys())
    old_sets = set(old.values())
    assert [name for name, values in new.items() if values in old_sets] == []


def test_the_docstring_names_the_home_and_the_old_file() -> None:
    doc = team_enums.__doc__ or ""
    assert "Group 10" in doc and "schema/enums.py" in doc


def test_stages_use_the_enums_not_retyped_literals() -> None:
    old_values = {v for values in _enums_of(enums).values() for v in values}
    team_values = {v for values in _enums_of(team_enums).values() for v in values}
    # plain words ("failed", "manual", "stale") mean other things in other stages; the compound
    # values below are the ones only the team vocabulary owns.
    distinctive = {v for v in team_values - old_values if "_" in v}
    assert {"catch_up", "skipped_overlap", "blocked_no_credentials", "team_button"} <= distinctive
    offenders = []
    for path in sorted((SRC / "stages").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef))
                      and n.body and isinstance(n.body[0], ast.Expr)
                      and isinstance(n.body[0].value, ast.Constant)}
        offenders += [f"{path.name}:{n.lineno} {n.value!r}" for n in ast.walk(tree)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)
                      and n.value in distinctive and id(n) not in docstrings]
    assert offenders == []
