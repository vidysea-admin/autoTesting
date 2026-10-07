"""Host-side media preparation artifacts: transcripts and chunk manifests.

`stages/media_prep.py` (host CLI, needs ffmpeg/faster-whisper) writes these;
the container only ever reads them back through `ProjectStore`, never runs
ffmpeg itself (A3 — the container has neither ffmpeg nor a GPU).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from autotester.schema.base import Artifact


def _reason(exc: Exception) -> str:
    """Why a sidecar is unreadable, never what it says (AT-468). Pydantic's own message
    quotes the offending input, and a segment's input is narration text; so a validation
    failure keeps only each error's location and kind. An unknown key is itself sidecar
    content, so it is named only as a kind. The other causes (JSON position, undecodable
    byte, a missing segments list, a non-mapping segment) quote no text."""
    if not isinstance(exc, ValidationError):
        return f"{type(exc).__name__}: {exc}"
    parts = ["unknown field" if e["type"] == "extra_forbidden"
             else f"{'.'.join(str(x) for x in e['loc'])}: {e['type']}" for e in exc.errors()]
    return f"ValidationError: {'; '.join(parts)}"


class TranscriptSegment(BaseModel):
    """One spoken utterance, absolute seconds into the source video."""

    model_config = ConfigDict(extra="forbid")

    start: float
    end: float
    text: str


class Transcript(Artifact):
    """A video's narration. `from_sidecar` loads the exact shape the existing
    `erp*.transcript.json` files already use — those are reused byte-for-byte,
    never re-transcribed."""

    source_id: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    speech_seconds: float = 0.0
    engine: str = "none"
    unreadable_reason: str | None = Field(
        default=None, description='why engine="unreadable": the parse error, never the file')

    @classmethod
    def from_sidecar(cls, path: Path, source_id: str) -> Transcript:
        """Load `{"segments": [{start,end,text}], "speech_seconds": N}` — the
        shape every existing `*.transcript.json` sidecar already has. A file with
        no segments LIST asserts nothing, so it raises rather than reading as
        silence (AT-466: `{}` loaded as a sidecar with no speech)."""
        import json

        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("segments"), list):
            raise ValueError("sidecar has no segments list")
        segments = [TranscriptSegment(**seg) for seg in raw["segments"]]
        return cls(
            source_id=source_id,
            segments=segments,
            speech_seconds=raw.get("speech_seconds", 0.0),
            engine="sidecar",
        )

    @classmethod
    def read_sidecar(cls, path: Path, source_id: str) -> Transcript:
        """The one best-effort sidecar reader (media prep and ingest both use it).
        A sidecar that cannot be read is VL1's third state, `engine="unreadable"`,
        and it keeps its cause instead of discarding it (AT-466)."""
        try:
            return cls.from_sidecar(path, source_id)
        except Exception as exc:  # any malformed shape at all: best-effort by contract
            return cls(source_id=source_id, engine="unreadable",
                       unreadable_reason=_reason(exc)[:300])

    def slice(self, offset_s: float, length_s: float) -> str:
        """Clip-relative narration lines for the window `[offset_s, offset_s+length_s)`,
        as `[MM:SS-MM:SS] text` — injected into the ingest prompt as ground truth
        so the model aligns speech to screen instead of re-transcribing (I8)."""
        end = offset_s + length_s
        lines = []
        for seg in self.segments:
            if seg.end <= offset_s or seg.start >= end:
                continue
            rel_start = max(seg.start, offset_s) - offset_s
            rel_end = min(seg.end, end) - offset_s
            lines.append(f"[{_fmt(rel_start)}-{_fmt(rel_end)}] {seg.text}")
        return "\n".join(lines)

    def quotes(self, text: str, *, scrub: Callable[[str], str] | None = None) -> bool:
        """True when `text` is said verbatim here (whitespace-normalised, case-folded) --
        a quote, not a paraphrase (reconcile RC3). `scrub` also accepts the redacted
        spelling, so a quote stored scrubbed still verifies on the next run."""
        def norm(s: str) -> str:
            return " ".join(s.casefold().split())
        spoken = " ".join(seg.text for seg in self.segments)
        heard = {norm(spoken), norm(scrub(spoken)) if scrub else norm(spoken)}
        return bool(norm(text)) and any(norm(text) in h for h in heard)


def _fmt(seconds: float) -> str:
    m, s = divmod(round(seconds), 60)
    return f"{m:02d}:{s:02d}"


class MediaChunk(BaseModel):
    """One re-encoded chunk of a longer video."""

    model_config = ConfigDict(extra="forbid")

    index: int
    path: str = Field(description="project-relative path under sources/<id>/chunks/")
    offset_s: float
    length_s: float


class MediaPrep(Artifact):
    """Probe + chunk manifest for one `Source`. Degrades gracefully (VL1):
    without ffmpeg, a single chunk pointing at the original path;
    `transcript_ref` names the sibling `Transcript` when one exists."""

    source_id: str
    duration_s: float = 0.0
    width: int = 0
    height: int = 0
    chunks: list[MediaChunk] = Field(default_factory=list)
    transcript_ref: str | None = None
    ffmpeg_version: str | None = None
