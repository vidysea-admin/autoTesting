"""Pins the T-160..T-184 "revised goal contract" registration exactly.

Split from test_goal_done_checks.py once that file passed doctor's 300-line
cap again under AT-638's repair (same reason `test_goal_done_check_shapes.py`
split off earlier): a different responsibility from either half already
there. `is_capable_of_failing`'s predicate correctness lives in the shapes
file; goal.json-scanning guards over ALL tasks stay in the main file; this
file is neither -- it is a one-off snapshot test asserting one specific,
already-closed registration (D-039..D-045, T-160..T-184) is still exactly as
it was pinned, independent of whatever else gets added to goal.json later
(AT-638/ISS-at638-remainder-2: the previous version conflated this with "no
other task may ever be registered", which broke on ordinary ad hoc work).
"""

from __future__ import annotations

import json

from test_goal_done_checks import GOAL, REPO_ROOT


def test_revised_goal_contract_is_registered() -> None:
    data = json.loads(GOAL.read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in data["tasks"]}
    tests = "tests/"
    expected = {
        # AT-638: this node id moved with the test's file split (own done_check, kept accurate).
        "T-160": (["T-134"], tests + "test_goal_contract_registration.py::"
                  "test_revised_goal_contract_is_registered"),
        "T-161": (["T-100", "T-160"], tests + "test_ui_project_intake.py"),
        "T-162": (["T-161"], tests + "test_source_adapters.py "
                  "tests/test_source_adapters_audio.py "
                  "tests/test_source_adapters_email.py "
                  "tests/test_source_adapters_drive.py"),
        "T-163": (["T-135", "T-162"], tests + "test_orchestrate.py "
                  "tests/test_orchestrate_runners.py"),
        "T-164": (["T-163"], tests + "test_portal_persona.py"),
        "T-165": (["T-163", "T-144"], tests + "test_explore_completeness.py "
                  "tests/test_explore_traversal.py tests/test_persona_changes.py"),
        "T-166": (["T-125", "T-164", "T-165", "T-170"], tests + "test_eval_compiler.py"),
        "T-170": (["T-163"], tests + "test_network_assertions.py"),
        "T-171": (["T-165"], tests + "test_permission_coverage.py"),
        "T-172": (["T-163"], tests + "test_run_trace.py"),
        "T-173": (["T-163"], tests + "test_parallel_run.py"),
        "T-174": (["T-125"], tests + "test_cli_mcp.py"),
        "T-175": ([], tests + "test_prompt_skills.py"),
        "T-176": (["T-165"], tests + "test_script_replay.py"),
        "T-177": (["T-176"], tests + "test_agent_fallback.py"),
        "T-178": (["T-125"], tests + "test_failure_bundle.py"),
        "T-167": (["T-166", "T-110"], tests + "test_regression_trigger.py"),
        "T-168": (["T-164", "T-165", "T-167"], tests + "test_unified_report.py"),
        "T-169": (["T-136", "T-145", "T-168"], tests + "test_generic_acceptance.py"),
        # D-042: T-179..T-181
        "T-179": (["T-170", "T-172", "T-175"], tests + "test_agent_layer.py"),
        "T-180": (["T-179"], tests + "test_agent_subagents.py"),
        "T-181": (["T-180"], tests + "test_agent_gain.py"),
        "T-182": ([], tests + "test_viewport_locale_enact.py"),
        "T-183": ([], tests + "test_report_export_reason.py"),
        "T-184": ([], tests + "test_pinned_regression.py"),
    }
    # No CLI `-q`: pyproject.toml's addopts already sets it, and stacking a second one makes
    # pytest -qq, which prints no summary line at all (AT-503/AT-522, measured 2026-09-18).
    expected = {key: (deps, f"uv run pytest {spec}") for key, (deps, spec) in expected.items()}
    actual = {key: (by_id[key]["deps"], by_id[key]["done_check"]["cmd"]) for key in expected}
    assert actual == expected
    progress = data["progress"]
    # D-040: T-170, T-171; D-041: T-172..T-178; D-042: T-179..T-181; D-045: T-182..T-184
    #
    # No longer pinned to a literal count (AT-638/ISS-at638-remainder-2). `== 70` broke when
    # `f9e7d406` registered T-185..T-195 -- ordinary ad hoc issue-fix tasks (AT-453, AT-583,
    # AT-617, ...), never part of "the revised goal contract" this test pins (no D-0NN chain
    # comment, `deps: []`, absent from `expected` above) -- for a reason unrelated to whether
    # T-160..T-184 are still correctly registered (`actual == expected` already proves that).
    # A repo that keeps registering ad hoc work is healthy; re-bumping a magic count on every
    # unrelated task would make the assertion noise. What must never drift is the file's own
    # bookkeeping, so that self-consistency stays and the literal number is dropped.
    assert progress["total"] == len(data["tasks"])
    for key in ("done", "in_progress", "pending", "blocked"):
        assert progress[key] == sum(task["status"] == key for task in data["tasks"])
    assert progress["percent"] == round(100 * progress["done"] / progress["total"])
    contract = data["north_star"] + (REPO_ROOT / "plan.md").read_text(encoding="utf-8")
    phrases = ("Google Drive", "breadth-first", "Portal Persona", "API", "HTML",
               "Excel", "screenshots", "## 9. Revised product layer")
    assert all(phrase in contract for phrase in phrases)
    decisions = (REPO_ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    assert "## D-023 | 2026-09-10 | type: decision | status: ACTIVE" in decisions
    dashboard = (REPO_ROOT / ".goal" / "dashboard.html").read_text(encoding="utf-8")
    facts = (f'{progress["done"]}/{progress["total"]} tasks',
             f'{progress["percent"]}%', f'Remaining ({progress["pending"]})', data["north_star"])
    assert all(value in dashboard for value in facts)
