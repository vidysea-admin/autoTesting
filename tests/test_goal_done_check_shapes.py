"""`is_capable_of_failing`'s own shape-recognition, driven directly with
constructed commands — not through `.goal/goal.json`. Contract: C9 (a
declared control value is honoured or rejected, never silently ignored).

Split from test_goal_done_checks.py once that file passed doctor's
300-line cap — the goal.json-scanning integration tests stay there; the
guard's own predicate correctness lives here.
"""

from __future__ import annotations

from test_goal_done_checks import is_capable_of_failing, tasks


def test_the_guard_recognises_the_shapes_it_exists_to_catch() -> None:
    """A guard whose own predicate is wrong protects nothing. Every command
    below was measured by the checker against the real repo (AT-154/AT-155);
    each REJECTED one exits 0 today regardless of any task's state."""
    rejected = [
        "true",                                        # AT-100's original
        "uv run autotester doctor",                    # T-126, T-150
        "uv run pytest -q && uv run autotester doctor",  # T-135
        "uv run pytest tests/ -q",                     # AT-154: the whole suite as a path
        "uv run pytest tests",
        "uv run pytest -q tests/",
        "uv run pytest --collect-only tests/test_x.py",  # collects, never runs
        "echo done",
        'uv run python -c "pass"',
        "test -f README.md",
        "ls src/autotester/stages/merge_flowspec.py || true",   # `||` neuters anything
        "uv run pytest tests/test_explore.py -q || exit 0",
        "true # tests/test_x.py",
        # AT-158 -- four families the first allowlist still admitted, all from
        # one cause: it matched program names against ANY token instead of the
        # program position.
        "uv run pytest --co tests/test_x.py",          # --co IS --collect-only
        "uv run pytest tests/test_x.py | true",        # `|` was not `||`
        "uv run pytest tests/test_x.py |& true",
        "echo pytest tests/test_x.py",                 # the word, not the program
        "true # pytest tests/test_x.py",               # a comment containing it
        # AT-161 -- an ALWAYS_TRUE segment as the LAST `;`-group decides the
        # exit code, which a plain `any(_is_task_specific(seg))` over a
        # flattened split never saw.
        "uv run pytest tests/test_x.py; true",
        "uv run pytest tests/test_x.py; :",
        "uv run pytest tests/test_x.py; exit 0",
        # AT-359 -- the same `;` shape, but the trailing no-op is not one of
        # the three ALWAYS_TRUE literals: any always-succeeding command
        # (echo, a bare ls in an existing repo) as the LAST `;`-segment
        # equally masks the real segment's exit code.
        "uv run pytest tests/test_x.py; echo done",
        "uv run pytest tests/test_x.py; ls",
        # AT-359 cycle 2 (checker FAIL) -- `exit` terminates the shell
        # immediately; a LEADING `exit 0` hides a task-specific segment
        # behind it just as effectively as `|| true` does, across both
        # separators. A TRAILING `exit 0` (below, in `accepted`) is fine --
        # nothing follows it to hide.
        "exit 0 && uv run pytest tests/test_x.py",
        "exit 0; uv run pytest tests/test_x.py",
    ]
    for command in rejected:
        assert not is_capable_of_failing(command), f"accepted an unfailable check: {command!r}"
    accepted = [
        "uv run pytest tests/test_explore.py -q",
        "uv run pytest tests/test_explore.py::test_one",
        "uv run python scripts/check_crawl_approval.py erp",
        "uv run python scripts/check_deliverable.py --exists qa/contracts/ai-target.md "
        "&& uv run autotester doctor",
        # AT-159 -- rejected by recognition bugs, not by policy. Both are the
        # same shape the branch exists for: an interpreter running a repo
        # script. Waiving them would have waived a typo.
        "python3 scripts/check_crawl_approval.py erp",
        "uv run python src/autotester/tools/verify.py",
        "uv run pytest tests/test_a.py tests/test_b.py",
        "uv run python -m pytest tests/test_x.py",
        # AT-359 -- `&&` propagates the FIRST failure, so a trailing
        # ALWAYS_TRUE segment can never mask an earlier task-specific
        # segment's failure the way a trailing `;`-segment can. These two
        # were wrongly rejected under AT-161's flattened ;/&& split; real
        # shell semantics accepts them.
        "uv run pytest tests/test_x.py && true",
        "uv run pytest tests/test_x.py && exit 0",
    ]
    for command in accepted:
        assert is_capable_of_failing(command), f"rejected a legitimate check: {command!r}"


def test_the_three_known_offenders_are_actually_fixed() -> None:
    """AT-115 recorded two; measuring found three. Named individually so a
    regression on any one of them fails loudly rather than being absorbed into
    the aggregate above."""
    by_id = {t["id"]: t for t in tasks()}
    for task_id in ("T-126", "T-135", "T-150"):
        cmd = by_id[task_id]["done_check"]["cmd"]
        assert is_capable_of_failing(cmd), f"{task_id} regressed to {cmd!r}"
