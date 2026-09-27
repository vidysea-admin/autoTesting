"""A `done_check` must be able to fail — C9 for the second of its three fields.

C9 says a declared control value is honoured or rejected, never silently
ignored. Its Verify clause tested only `base_criticality`; nothing anywhere
pinned `done_check` (AT-141). Meanwhile T-126, T-150 and T-135 all carried
`uv run autotester doctor` — which passes on a clean repo whether or not the
task it guards has been started, so it would have reported "done" for work
nobody had done (AT-100, AT-115).

That is the AT-100 shape three times, not the twice AT-115 recorded, and it
lives in the machinery that decides whether anything is finished.

The guard is deliberately STATIC. Running every pending task's `done_check` for
real would take minutes and would itself pass once the work landed — the
property worth pinning is not "it fails today" but "it is *capable* of failing",
i.e. it names something specific to this task rather than asserting the repo is
healthy.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOAL = REPO_ROOT / ".goal" / "goal.json"

ALWAYS_TRUE = ("true", ":", "exit 0")
"""Commands that cannot fail at all. AT-100's original was literally
`{"cmd": "true"}` on the live production ERP crawl."""


def tasks() -> list[dict]:
    return json.loads(GOAL.read_text(encoding="utf-8"))["tasks"]


SHELL_NEUTERING = ("|", "#", "`", "$(", ">", "<", "&")
"""Characters that can make a command's exit code mean something other than
what the command in front of them did. `pytest x.py | true`, `true # pytest
x.py`, `cmd > /dev/null || exit 0` — AT-158 measured four such families, all
admitted because the predicate looked at TOKENS rather than at what actually
runs. Rejected outright: a `done_check` needs none of them, and a waiver is
the way to ask for one."""

RUNNERS = ("uv", "run", "poetry", "pdm", "hatch", "env")
"""Wrapper words that precede the real program. `uv run pytest x.py` runs
pytest; the program is the first token that is not one of these."""


def _program(parts: list[str]) -> str:
    """The command that actually executes, not any token that resembles one.

    AT-158's root cause: this used to ask `"pytest" in parts`, so `echo pytest
    tests/x.py` and `true # pytest tests/x.py` both read as pytest invocations.
    A program name is only a program name in the program position."""
    for token in parts:
        if token in RUNNERS or "=" in token:
            continue
        return Path(token).name
    return ""


def _is_task_specific(segment: str) -> bool:
    """Does this ONE command depend on a particular task's deliverables?

    An ALLOWLIST (AT-155): a command qualifies only as a shape known to depend
    on a deliverable. Anything unrecognised is rejected and the way past that
    is a written `waiver`, not a cleverer command — a denylist on shell
    commands fails open by construction, which is what AT-154/AT-155 were.
    """
    if segment.strip() in ALWAYS_TRUE:
        return False
    if any(ch in segment for ch in SHELL_NEUTERING):
        return False
    try:
        parts = shlex.split(segment)
    except ValueError:
        return False  # unbalanced quotes: not a command anyone can reason about
    if not parts:
        return False
    program = _program(parts)
    if program == "check_deliverable.py" or any(
            p.endswith("check_deliverable.py") for p in parts[:3]):
        # Its own no-assertion guard exits 2, so a bare invocation always fails.
        return True
    if program == "pytest" or (program.startswith("python") and "-m" in parts
                               and "pytest" in parts):
        if any(p in ("--collect-only", "--co") for p in parts):
            return False  # collects without running: exit 0 on anything importable
        # A path is specific only when it names a FILE or a node id. `tests/`
        # is the whole suite wearing a path (AT-154).
        return any(p.endswith(".py") or "::" in p for p in parts)
    if program.startswith("python"):
        # AT-159: `python3` and a script outside scripts/ are the SAME shape
        # this branch was written for — an interpreter running a repo script.
        if "-c" in parts or "-m" in parts:
            return False
        return any(p.endswith(".py") for p in parts[1:])
    return False


def _is_bare_exit(segment: str) -> bool:
    """`exit`/`exit N` terminates the shell immediately -- nothing after it,
    across ANY separator, ever runs (AT-359 cycle 2)."""
    try:
        parts = shlex.split(segment)
    except ValueError:
        return False
    return len(parts) in (1, 2) and parts[0] == "exit"


def _truncate_after_first_exit(command: str) -> str:
    """Scan segments left to right across `;`/`&&` and cut after the first
    bare `exit`: `exit 0 && X` / `exit 0; X` both exit 0 without X ever
    running -- AT-100's shape wearing `exit` (checker FAIL, cycle 1). A
    trailing `exit` (e.g. `pytest x.py && exit 0`) is untouched."""
    parts = re.split(r"(;|&&)", command)
    for i in range(0, len(parts), 2):
        if _is_bare_exit(parts[i].strip()):
            return "".join(parts[:i + 1])
    return command


def is_capable_of_failing(command: str) -> bool:
    """Can this `done_check` distinguish done from not-started?

    `||` disqualifies the command anywhere; a leading/mid-chain bare `exit`
    hides everything after it (`_truncate_after_first_exit`). Otherwise `;`
    and `&&` score differently (AT-359): a `;`-sequence's exit status is its
    LAST group's alone; a `&&`-chain propagates the FIRST failure, so any
    task-specific segment in the group is enough regardless of what
    follows. AT-161's flatten-and-any() missed a `;`-terminated `echo`/`ls`
    and over-rejected `&& true` chains."""
    if "||" in command:
        return False
    command = _truncate_after_first_exit(command)
    groups = [g.strip() for g in command.split(";") if g.strip()]
    if not groups:
        return False
    last_group_segments = [s.strip() for s in groups[-1].split("&&") if s.strip()]
    if not last_group_segments:
        return False
    return any(_is_task_specific(seg) for seg in last_group_segments)


def waiver_of(task: dict) -> str:
    return str(task.get("done_check", {}).get("waiver") or "").strip()


def test_no_pending_task_has_a_done_check_that_cannot_fail() -> None:
    """The AT-100 shape. `{"cmd": "true"}` was the first instance; `uv run
    autotester doctor` on a governance task is the same defect wearing a
    plausible command; `pytest tests/` is it wearing a path.

    A task whose check genuinely cannot be made specific may carry
    `done_check.waiver: "<why>"`. That is the point of an allowlist: the
    escape hatch is a sentence someone wrote and can be grepped for, not a
    command shape nobody noticed."""
    offenders = offenders_in(tasks())
    assert offenders == [], (
        "these done_checks pass on a clean repo whether or not their task was "
        f"started, and carry no waiver: {offenders}")


def _waiver_offenders(rows: list[dict]) -> list[str]:
    return [r["id"] for r in rows
            if r.get("done_check", {}).get("waiver") is not None
            and len(waiver_of(r)) < 20]


def test_no_task_on_disk_carries_an_empty_waiver() -> None:
    """A waiver is a written decision, so an empty or placeholder one is worse
    than none — it silences the guard while recording nothing."""
    assert _waiver_offenders(tasks()) == []


def test_the_waiver_rule_actually_rejects_a_hollow_waiver() -> None:
    """Sabotaging the waiver length check was INCONCLUSIVE — zero failures,
    because no task on disk carries a waiver at all, so the rule had no data
    to bite on (C7's new clause caught exactly that). A guard that is only
    ever asked about an empty set has not been shown to work, so it is asked
    here about rows that would break it."""
    hollow = [
        {"id": "T-x", "status": "pending", "done_check": {"cmd": "true", "waiver": ""}},
        {"id": "T-y", "status": "pending", "done_check": {"cmd": "true", "waiver": "wip"}},
    ]
    real = [{"id": "T-z", "status": "pending", "done_check": {
        "cmd": "true",
        "waiver": "no deliverable exists until the ERP credentials are entered"}}]
    assert _waiver_offenders(hollow) == ["T-x", "T-y"]
    assert _waiver_offenders(real) == []


def offenders_in(rows: list[dict]) -> list[str]:
    """The exact rule `test_no_pending_task_...` applies, extracted so it can
    be asserted on rows that do not exist on disk (AT-160)."""
    return [r["id"] for r in rows
            if r["status"] != "done" and r.get("done_check", {}).get("cmd")
            and not is_capable_of_failing(r["done_check"]["cmd"])
            and not waiver_of(r)]


def test_a_waived_task_is_exempt_and_an_unwaived_one_is_not() -> None:
    """AT-160: the previous version asserted the two helpers SEPARATELY and
    never their composition, so deleting `and not waiver_of(t)` from the
    offenders rule left the suite green — an unguarded exemption clause, which
    is C7's own INCONCLUSIVE class inside a test written to close it.
    This asserts the rule itself, on rows chosen so a broken composition cannot
    pass: one waived and one not, both otherwise identical."""
    waived = {"id": "T-w", "status": "pending", "done_check": {
        "cmd": "uv run autotester doctor",
        "waiver": "governance-only task with no artifact to assert on"}}
    unwaived = {"id": "T-u", "status": "pending",
                "done_check": {"cmd": "uv run autotester doctor"}}
    assert offenders_in([waived, unwaived]) == ["T-u"], (
        "the waiver must exempt exactly its own task and nothing else")
    assert offenders_in([waived]) == []
    assert offenders_in([unwaived]) == ["T-u"]


def test_every_pending_task_actually_has_a_done_check() -> None:
    """A missing check is the same defect as an unfailable one, minus the
    pretence."""
    missing = [t["id"] for t in tasks()
               if t["status"] != "done" and not t.get("done_check", {}).get("cmd")]
    assert missing == [], f"pending tasks with no done_check: {missing}"


def test_check_deliverable_reports_an_unreadable_path_instead_of_crashing() -> None:
    """AT-157. Sabotaging this was INCONCLUSIVE — nothing exercised it. The old
    code raised an unhandled traceback on a directory: still non-zero, so never
    unsafe, but a `done_check` that dies with a stack trace tells its reader
    nothing about what is missing, which is its whole job."""
    from check_deliverable import main
    assert main(["--contains", "src", "needle"]) == 1
    assert main(["--exists", "src/autotester/cli.py"]) == 0
    assert main([]) == 2, "a check with no assertion must not be able to pass"


def test_revised_goal_contract_is_registered() -> None:
    data = json.loads(GOAL.read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in data["tasks"]}
    tests = "tests/"
    expected = {
        "T-160": (["T-134"], tests + "test_goal_done_checks.py::"
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
        "T-171": (["T-165"], tests + "test_permission_surface.py"),
        "T-172": (["T-163"], tests + "test_run_trace.py"),
        "T-173": (["T-163"], tests + "test_parallel_run.py"),
        "T-174": (["T-125"], tests + "test_cli_mcp.py"),
        "T-175": ([], tests + "test_prompt_skills.py"),
        "T-176": (["T-165"], tests + "test_script_replay.py"),
        "T-177": (["T-176"], tests + "test_agent_fallback.py"),
        "T-178": (["T-125"], tests + "test_failure_bundle.py"),
        "T-167": (["T-166", "T-110"], tests + "test_regression_trigger.py"),
        "T-168": (["T-155", "T-164", "T-165", "T-167"], tests + "test_unified_report.py"),
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
    assert progress["total"] == len(data["tasks"]) == 70
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
