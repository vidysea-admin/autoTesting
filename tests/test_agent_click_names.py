"""D-086 HG-1: READ_ONLY click names are cleaned (blank, zero-width, spacing, lookalikes)."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_agent_read_only import AW, RO, TA, A, _one, _run
from test_agent_tools import Spies, spies  # noqa: F401

from autotester.schema.agent_layer import RefusalClass
from autotester.schema.enums import WritePolicy


@pytest.fixture
def spy(spies: Spies) -> Spies:  # noqa: F811
    return spies


_BLANK = ["   ", "\t\n", "\u200b", "\u00a0", "\ufeff", "\u200c", "\u200d", " \u200b\u00a0 "]
_HIDDEN_COMMIT = ["Place  order", "Place-order", "Place_order", "Sign\u00a0in", "Save\u200bdraft",
                  "SAVE", "De\u200blete", "D\u0435lete", "\uff24elete", "\uff33ave", "S\u0430ve"]


@pytest.mark.parametrize("name", _BLANK)
def test_read_only_refuses_a_blank_or_zero_width_click_name_as_unnamed(
        tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.refusal is RefusalClass.WRITE_POLICY and "read_only" in out.summary
    assert spy.sessions == 0 and spy.count("run_case") == 0


@pytest.mark.parametrize("name", _HIDDEN_COMMIT)
def test_read_only_refuses_a_commit_or_delete_name_hidden_by_spacing_or_lookalikes(
        tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.refusal is RefusalClass.WRITE_POLICY
    assert spy.sessions == 0 and spy.count("run_case") == 0


@pytest.mark.parametrize("name", ["Home", "Next", "Search", " Home ", "Home\u200b"])
def test_read_only_still_allows_benign_names_with_stray_spacing(
        tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.ok and spy.count("run_case") == 1


@pytest.mark.parametrize("policy", [TA, AW])
def test_other_policies_also_refuse_a_blank_click_name(
        tmp_path: Path, spy: Spies, policy: WritePolicy) -> None:
    _, out = _run(tmp_path, spy, policy, _one(A.CLICK, "\u200b"))
    assert out.refusal is RefusalClass.WRITE_POLICY and spy.count("run_case") == 0


@pytest.mark.parametrize(
    "name", ["\u2800", "\u3164", "\u115f\u1160", "\uffa0", " \u2800\u3164 \u200b"])
def test_read_only_refuses_invisible_filler_names_as_unnamed(
        tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.refusal is RefusalClass.WRITE_POLICY and spy.sessions == 0


@pytest.mark.parametrize("name", ["Close account", "Deactivate", "Remove account",
                                  "Cancel subscription", "Unsubscribe", "Delete account"])
def test_read_only_refuses_account_destructive_names(
        tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.refusal is RefusalClass.WRITE_POLICY and spy.sessions == 0


@pytest.mark.parametrize("name", ["Home", "Next", "Search", "Caf\u00e9", "English", "Close"])
def test_read_only_still_allows_benign_names(tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.refusal is None
