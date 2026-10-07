"""Build the model prompt for one batch of frames, and say what narration there is (TV5, TV6).

The template is a file (`prompts/video_review_v1.md`) that carries its placeholders; a template
that loses one ships a blind prompt (the I8 lesson), so `build_review_prompt` refuses it. Free
text from a pointer or a transcript is scrubbed before it can leave the machine (TV8).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from autotester.core.paths import RepoDocs
from autotester.schema.media import Transcript
from autotester.schema.video_pointer import PointerParse
from autotester.schema.video_review import NarrationState, RedactionWindow

PROMPT_FILE = "video_review_v1.md"
PLACEHOLDERS = ("{{SOURCE_ID}}", "{{DURATION}}", "{{FRAME_TIMES}}", "{{POINTERS}}",
                "{{NARRATION}}", "{{MAX_ITEMS}}")
NARRATION_PAD_S = 15.0
"""Narration is shown a little beyond the first and last frame of a call: a frame stands for
the stretch up to the next one."""
NARRATION_NOTES: dict[str, str] = {
    "none": "no narration on record",
    "unreadable": "narration unreadable",
    "speech": "narration on record",
}


def load_template(prompts_dir: Path | None = None) -> str:
    return ((prompts_dir or RepoDocs().prompts_dir) / PROMPT_FILE).read_text(encoding="utf-8")


def narration_state(transcript: Transcript | None) -> NarrationState:
    """`none` (nobody transcribed, or no speech), `unreadable` (a sidecar that would not parse)
    or `speech`. Never conflated: silence is not verification (AT-134)."""
    if transcript is not None and transcript.engine == "unreadable":
        return "unreadable"
    if transcript is not None and transcript.segments:
        return "speech"
    return "none"


def visible_transcript(transcript: Transcript | None,
                       windows: Sequence[RedactionWindow]) -> Transcript | None:
    """The transcript minus every segment that touches a redaction window (TV7.3).

    Speech spoken while a screen is blacked out may read that screen out loud, so the WHOLE
    segment is dropped (clipping text by time would guess where the words fall)."""
    if transcript is None or not windows:
        return transcript
    kept = [s for s in transcript.segments
            if not any(s.end >= w.start_s and s.start <= w.end_s for w in windows)]
    return transcript.model_copy(update={"segments": kept})


def clock(seconds: float) -> str:
    s = round(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def review_narration(transcript: Transcript | None, lo: float, hi: float,
                    scrub: Callable[[str], str]) -> str:
    """Absolute-second narration lines overlapping `[lo, hi]`, three states kept apart."""
    state = narration_state(transcript)
    if state == "unreadable":
        return ("(a transcript exists but could not be read -- do NOT assume the recording is "
                "silent, and do not invent dialogue)")
    if state == "none" or transcript is None:
        return "(no narration on record -- do not invent dialogue)"
    lines = [f"[{clock(s.start)}-{clock(s.end)}] {scrub(s.text)}"
             for s in transcript.segments if s.end >= lo and s.start <= hi]
    return "\n".join(lines) or "(no narration at these moments -- do not invent dialogue)"


def pointer_block(parse: PointerParse, scrub: Callable[[str], str]) -> str:
    if not parse.parsed:
        return "(none -- the reviewer gave no pointers)"
    rows = []
    for p in parse.parsed:
        when = ("whole recording" if p.start_s is None else
                clock(p.start_s) if p.end_s is None else f"{clock(p.start_s)}-{clock(p.end_s)}")
        approx = " (approximate)" if p.approx else ""
        note = f" -- {scrub(p.text)}" if p.text else ""
        rows.append(f"line {p.line_no}: {when}{approx}{note}")
    return "\n".join(rows)


def build_review_prompt(template: str, *, source_id: str, duration_s: float, times: list[float],
                 parse: PointerParse, transcript: Transcript | None,
                 scrub: Callable[[str], str], max_items: int) -> str:
    missing = [p for p in PLACEHOLDERS if p not in template]
    if missing:
        raise ValueError(f"prompt template lost placeholders {missing}: refusing a blind prompt")
    lo, hi = 0.0, duration_s
    if times:
        lo, hi = max(0.0, min(times) - NARRATION_PAD_S), max(times) + NARRATION_PAD_S
    values = {
        "{{SOURCE_ID}}": source_id, "{{DURATION}}": f"{duration_s:g}",
        "{{FRAME_TIMES}}": ", ".join(f"{t:g}" for t in times),
        "{{POINTERS}}": pointer_block(parse, scrub),
        "{{NARRATION}}": review_narration(transcript, lo, hi, scrub),
        "{{MAX_ITEMS}}": str(max_items),
    }
    out = template
    for key, val in values.items():
        out = out.replace(key, val)
    return out
