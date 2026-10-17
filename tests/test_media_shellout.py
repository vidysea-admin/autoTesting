"""What this stage hands to ffmpeg, and what it does when ffmpeg is not there.

AT-170: four behaviours the contract depends on had **no regression guard at
all**. A checker sabotaged each one and every sabotage produced **zero
failures** — reported INCONCLUSIVE per C7, which is exactly right and exactly
why they are still open: the behaviours are correct, and nothing would notice
if they stopped being.

They are grouped here rather than in `test_media.py` because they are one
responsibility: the boundary between this codebase and a program it does not
control. `subprocess.run` is intercepted, so nothing here needs ffmpeg — the
argv IS the artifact under test.

Contract: qa/contracts/video-learning.md VL1.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autotester.media import chunks as chunks_mod
from autotester.media import frames as frames_mod
from autotester.media import probe as probe_mod


class Recorder:
    """Stands in for `subprocess.run`, keeping every argv it was given."""

    def __init__(self, *, fail: set[str] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.fail = fail or set()

    def __call__(self, argv, *args, **kwargs):
        self.calls.append(list(argv))
        if argv[0] in self.fail:
            raise FileNotFoundError(argv[0])
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    def argv(self) -> list[str]:
        assert len(self.calls) == 1, f"expected one call, got {self.calls}"
        return self.calls[0]


def after(argv: list[str], flag: str) -> int:
    assert flag in argv, f"{flag} missing from {argv}"
    return argv.index(flag)


def is_ffmpeg(argv: list[str]) -> None:
    """AT-213: the ordering was asserted and the PROGRAM was not, so renaming
    the binary to `ffmpeg-x` failed nothing. A perfectly ordered argv handed to
    a program that does not exist is not a working call."""
    assert argv[0] == "ffmpeg", f"the tool invoked was {argv[0]!r}, not ffmpeg"


# -- -ss goes after -i, in both places that seek -----------------------------

def test_a_chunk_is_cut_with_the_seek_AFTER_the_input(monkeypatch, tmp_path: Path) -> None:
    """The ordering is the conservative one across ffmpeg builds, and the
    docstring in `encode_chunks` is careful to say the failure it once claimed
    for the other order does NOT happen on ffmpeg 8.1.1 (AT-168).

    It is still asserted, because every timestamp downstream is relative to a
    chunk offset: if a cut ever stopped landing where the plan says, every
    issue's reported second would move with it, and nothing else in the suite
    would say a word."""
    recorder = Recorder()
    monkeypatch.setattr(chunks_mod.subprocess, "run", recorder)

    chunks_mod.encode_chunks(tmp_path / "in.mp4", tmp_path / "out", [(30.0, 180.0)])

    argv = recorder.argv()
    is_ffmpeg(argv)
    assert after(argv, "-ss") > after(argv, "-i"), argv
    assert argv[after(argv, "-ss") + 1] == "30.0"
    assert argv[after(argv, "-t") + 1] == "180.0"


def test_a_frame_is_grabbed_with_the_seek_AFTER_the_input(monkeypatch, tmp_path: Path) -> None:
    """Same ordering, the other caller. A frame is shown to a human as
    evidence of a specific second, so a seek that lands elsewhere is a
    screenshot that quietly proves the wrong thing."""
    recorder = Recorder()
    monkeypatch.setattr(frames_mod.subprocess, "run", recorder)
    monkeypatch.setattr(frames_mod, "is_complete_png", lambda path: True)

    frames_mod.extract_frame(tmp_path / "in.mp4", 20.0, tmp_path / "f.png")

    argv = recorder.argv()
    is_ffmpeg(argv)
    assert after(argv, "-ss") > after(argv, "-i"), argv
    assert argv[after(argv, "-ss") + 1] == "20.0"


# -- both binaries, not either ----------------------------------------------

@pytest.mark.parametrize("missing", ["ffmpeg", "ffprobe"])
def test_one_binary_present_is_not_enough(monkeypatch, missing: str) -> None:
    """Chunking needs ffmpeg and probing needs ffprobe. A box with one and not
    the other would degrade **halfway through** rather than at the start, which
    is the worse place to find out — the whole reason `prepare` degrades rather
    than crashing."""
    monkeypatch.setattr(probe_mod.subprocess, "run", Recorder(fail={missing}))

    assert probe_mod.ffmpeg_available() is False


def test_both_present_is_enough(monkeypatch) -> None:
    """The other half: a guard that always says False guards nothing."""
    monkeypatch.setattr(probe_mod.subprocess, "run", Recorder())

    assert probe_mod.ffmpeg_available() is True


# -- an unreadable recording is a fact, not an exception ---------------------

def test_a_recording_that_cannot_be_probed_returns_zeros(monkeypatch, tmp_path: Path) -> None:
    """Zeros rather than an exception, because the caller's job is to record
    what is knowable about a source and "we could not read this" is knowable.

    `plan_chunks(0)` returns no chunks, so the zero propagates as "nothing to
    cut" rather than as a bad plan — the degrade path depends on this, and
    would turn into a traceback out of `prepare` if it ever raised."""
    recorder = Recorder(fail={"ffprobe"})
    monkeypatch.setattr(probe_mod.subprocess, "run", recorder)

    assert probe_mod.probe(tmp_path / "gone.mp4") == (0.0, 0, 0)
    assert recorder.calls[0][0] == "ffprobe", recorder.calls
    assert chunks_mod.plan_chunks(0.0) == []


def test_unreadable_json_from_ffprobe_is_the_same_fact(monkeypatch, tmp_path: Path) -> None:
    """A malformed answer and no answer are the same thing to a caller, and
    only one of the two was ever likely to be exercised by hand."""
    class Garbage(Recorder):
        def __call__(self, argv, *args, **kwargs):
            self.calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, stdout="not json", stderr="")

    monkeypatch.setattr(probe_mod.subprocess, "run", Garbage())

    assert probe_mod.probe(tmp_path / "x.mp4") == (0.0, 0, 0)


# -- AT-639: the cut is bounded, and a killed cut leaves no truncated chunk ---

def test_the_chunk_cut_asks_for_a_timeout(monkeypatch, tmp_path: Path) -> None:
    """AT-639: `encode_chunks` was the one unbounded shell-out of the three, so
    a wedged ffmpeg hung `prepare` forever -- and `media_prep` already catches
    every exception this call can raise, so the ONLY failure it could not
    degrade from was the one that never raises. The kwarg is asserted rather
    than the wall-clock because a test that actually hangs to prove a bound
    exists is a test nobody runs twice."""
    seen: dict[str, object] = {}

    def spy(argv, *args, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    monkeypatch.setattr(chunks_mod.subprocess, "run", spy)
    chunks_mod.encode_chunks(tmp_path / "in.mp4", tmp_path / "out", [(0.0, 180.0)])

    assert seen.get("timeout") == chunks_mod.CHUNK_TIMEOUT_S, (
        f"the cut ran with timeout={seen.get('timeout')!r} -- an unbounded "
        f"ffmpeg cannot be recovered from by any caller"
    )


def test_a_timed_out_cut_leaves_no_half_written_chunk(monkeypatch, tmp_path: Path) -> None:
    """A timeout kills ffmpeg mid-write, so the file on disk is a truncated clip
    that is indistinguishable from a real one. It must be gone, and the failure
    must still reach `media_prep` (AT-166) rather than be swallowed here."""
    out_dir = tmp_path / "out"

    def write_then_hang(argv, *args, **kwargs):
        Path(argv[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(argv[-1]).write_bytes(b"\x00truncated")
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))

    monkeypatch.setattr(chunks_mod.subprocess, "run", write_then_hang)

    with pytest.raises(subprocess.TimeoutExpired):
        chunks_mod.encode_chunks(tmp_path / "in.mp4", out_dir, [(0.0, 180.0)])

    leftovers = sorted(p.name for p in out_dir.glob("*.mp4"))
    assert leftovers == [], f"a truncated chunk survived the timeout: {leftovers}"


# -- ISS-at639-1: the per-chunk bound needs a whole-plan ceiling too ----------

def test_a_forty_minute_recording_whose_every_cut_is_slow_hits_a_total_deadline(
        monkeypatch, tmp_path: Path) -> None:
    """ISS-at639-1: `CHUNK_TIMEOUT_S` bounds ONE cut, but `prepare` loops
    `encode_chunks` over the whole plan, so a systemically sick ffmpeg (full
    disk, bad driver) where every cut takes just under the per-chunk bound
    still held INGEST for ~N x 900s -- 13 chunks of a 40 minute recording is
    ~3h. Every cut here "succeeds" after 800 fake seconds; none ever times out
    on its own, which is exactly why the per-chunk bound never fires."""
    plan = chunks_mod.plan_chunks(40 * 60.0)
    assert len(plan) >= 13, f"fixture must be a many-chunk plan, got {len(plan)}"
    now = [0.0]
    timeouts: list[float] = []

    def slow_cut(argv, *args, **kwargs):
        timeouts.append(kwargs["timeout"])
        now[0] += 800.0
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    clock = type("Clock", (), {"monotonic": staticmethod(lambda: now[0])})
    monkeypatch.setattr(chunks_mod, "time", clock)
    monkeypatch.setattr(chunks_mod.subprocess, "run", slow_cut)

    with pytest.raises(subprocess.TimeoutExpired):
        chunks_mod.encode_chunks(tmp_path / "in.mp4", tmp_path / "out", plan)

    assert now[0] <= chunks_mod.TOTAL_TIMEOUT_S + 800.0, (
        f"the plan ran {now[0]:.0f}s of cuts against a {chunks_mod.TOTAL_TIMEOUT_S:.0f}s "
        f"ceiling -- {len(timeouts)} of {len(plan)} chunks were cut")
    assert len(timeouts) < len(plan)
    assert max(timeouts) <= chunks_mod.CHUNK_TIMEOUT_S
