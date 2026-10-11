"""The test harness must not damage the repository it tests — AT-181 / AT-184.

Split from `test_cli_surface.py` at doctor's 300-line cap, by responsibility:
that file is about what the COMMANDS do, this one about what running them all
must never do.

The split earns itself. AT-181 was `uv run pytest` — this project's own verify
command — rewriting the git-tracked `docs/MAP.md` and `docs/SNAPSHOT.md` it
verifies, because the repo-level test took no temp root and `map`/`snapshot`
both write. AT-184 then arrived *from that fix*: a placeholder is not always an
input, so `report excel` created a file called `nonexistent` in the repo root.

Both were mine, and both are about the harness rather than the product.
Contract: `core-invariants.md` C4 (scratch belongs in `.work/`) and C7 (a check
someone else can re-run).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from cli_walk import invocation_for, shipped_commands
from typer.testing import CliRunner

from autotester.cli import app

runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


WATCHED_DIRS = ("docs", "src", "scripts", "projects")
"""Where a CLI command could plausibly write, and nowhere that a timer does.

AT-187: the first version watched `docs/` and the repo root only, while
`projects/<slug>/` is where the CLI actually writes.

AT-189, and it is an inconsistency inside one commit: I excluded `.goal/`
because the goal monitor rewrites it every few minutes, then added `qa/` — which
the maker-checker pair's own automation rewrites on the same kind of timer
(`.last-tick`, `issues.jsonl`, `verdicts/`, `.last-sweep`). 207 of the 1258
watched files were under `qa/`, **no CLI code writes there at all**, so it
bought nil detection and a real chance of this suite failing because a maker
tick landed mid-run. The rule I applied to `.goal/` and not to `qa/` is the
same rule; it is applied to both now."""


def test_server_smoke_refuses_an_argument_without_starting(root, monkeypatch):
    """The walker covers the server command without blocking in its valid loop."""
    from autotester import mcp_server

    def forbidden():
        pytest.fail("bad invocation entered the stdio server")

    monkeypatch.setattr(mcp_server, "serve", forbidden)
    result = runner.invoke(app, invocation_for("mcp", root))
    assert result.exit_code == 2
    assert "unexpected extra argument" in result.output.lower()


def _repo_fingerprint() -> dict[str, tuple[int, int, str]]:
    """`(mtime_ns, size, sha256)` per file — not the hash alone.

    AT-186, the sharpest finding on this file. A content hash detects a stray
    write only when the content DIFFERS. The checker sabotaged the PRODUCT
    rather than the test — removed the early `return` so `snapshot --print`
    echoes *and* writes — and the whole suite came back green, because
    `render_snapshot` reproduces the committed bytes exactly.

    A guard that fires only when the damage happens to be visible is not
    guarding what it was written for. The property is "nothing was WRITTEN";
    "nothing CHANGED" is a weaker claim that coincides with it most days.
    `mtime_ns` sees the write regardless of what was written.
    """
    repo = Path(__file__).resolve().parents[1]
    watched: list[Path] = [f for f in repo.iterdir() if f.is_file()]
    for name in WATCHED_DIRS:
        directory = repo / name
        if directory.is_dir():
            watched += [f for f in directory.rglob("*")
                        if f.is_file() and "__pycache__" not in f.parts]
    out: dict[str, tuple[int, int, str]] = {}
    for path in sorted(watched):
        try:
            stat = path.stat()
            out[str(path.relative_to(repo))] = (
                stat.st_mtime_ns, stat.st_size,
                hashlib.sha256(path.read_bytes()).hexdigest())
        except OSError:
            continue
    return out


def test_running_every_command_leaves_the_repository_untouched(root: Path) -> None:
    """AT-181 and AT-184, and both were mine.

    AT-181: the repo-level test took no `root` fixture, so it ran `map` and
    `snapshot` against the LIVE repo — and both write. `uv run pytest`, the
    adapter's own verify command, was rewriting the git-tracked `docs/MAP.md`
    and `docs/SNAPSHOT.md` it verifies. A verify step that mutates what it
    verifies is not a check anyone else can re-run, which is C7's sentence.

    AT-184 then arrived from AT-181's own fix: a placeholder is not always an
    INPUT. `report excel` takes an output PATH, so a bare "nonexistent" made
    the matrix create a file called `nonexistent` in the repo root.

    Sabotaging either came back INCONCLUSIVE until this existed — I had fixed
    both and pinned neither."""
    before = _repo_fingerprint()

    for command in shipped_commands():
        runner.invoke(app, invocation_for(command, root))
    for command in (["doctor"], ["providers"], ["snapshot", "--print"]):
        runner.invoke(app, command)

    after = _repo_fingerprint()
    changed = sorted(k for k in before if before[k] != after.get(k))
    created = sorted(set(after) - set(before))

    assert changed == [], f"running the CLI surface rewrote {changed}"
    assert created == [], f"running the CLI surface created {created} in the repo"


def test_snapshot_print_is_what_makes_the_repo_level_test_safe() -> None:
    """AT-181's fix rests on `--print`, so that is what gets pinned.

    The fingerprint test above cannot catch this: it sets a temp root, and the
    original bug was the ABSENCE of one — so reproducing it there is impossible
    by construction, and sabotaging it came back INCONCLUSIVE.

    This runs `snapshot --print` with NO temp root, deliberately, against the
    live repo — which is safe precisely because `--print` writes nothing. If
    that ever stops being true, the verify step starts rewriting the repository
    again and this fails."""
    before = _repo_fingerprint()

    result = runner.invoke(app, ["snapshot", "--print"])

    after = _repo_fingerprint()
    assert result.exit_code == 0, result.output
    assert len(result.output) > 200, "--print must actually print the snapshot"
    assert before == after, "snapshot --print wrote to the repository"


def test_map_has_no_read_only_mode_which_is_why_it_is_excluded() -> None:
    """The other half of AT-181's fix is an EXCLUSION, and an exclusion nobody
    justifies is one somebody quietly reverses. `map` is left out of the
    repo-level test because it can only write — if it ever gains a read-only
    flag, this fails and the exclusion should be revisited rather than
    inherited."""
    result = runner.invoke(app, ["map", "--help"])

    assert "--print" not in result.output and "--dry-run" not in result.output


def test_every_placeholder_stays_inside_the_temp_root(tmp_path: Path) -> None:
    """AT-184: a placeholder is not always an input. `report excel` takes an
    output PATH, so a bare "nonexistent" made the matrix create a file called
    `nonexistent` in the repo root — AT-181's shape, produced by AT-181's own
    fix.

    Asserted on the argv rather than on the filesystem, because the filesystem
    version needs the damage to happen first."""
    import click
    from typer.main import get_command

    from autotester.cli import app as cli_app

    root_cmd = get_command(cli_app)
    ctx = click.Context(root_cmd)

    for command in shipped_commands():
        argv = invocation_for(command, tmp_path)
        cmd: click.Command = root_cmd
        for part in command.split():
            cmd = cmd.get_command(ctx, part)  # type: ignore[union-attr]
        # A closed-vocabulary value is not a path and cannot become one, so it
        # is exempt (AT-185 supplies these so the last two commands reach their
        # own code). Everything else MUST be inside the temp root: the property
        # is that no placeholder a command might treat as a DESTINATION can
        # point at the repository.
        vocab = {str(v) for param in cmd.params
                 for v in (getattr(param.type, "choices", None) or ())}

        for token in argv[len(command.split()):]:
            if token.startswith("-") or token in vocab:
                continue
            assert token.startswith(str(tmp_path)), (
                f"`autotester {command}` gets placeholder {token!r}, which is "
                f"outside the temp root — a command treating it as a "
                f"destination would write into the repo")
