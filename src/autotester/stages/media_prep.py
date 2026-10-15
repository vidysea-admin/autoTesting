"""MEDIA PREP: make a recording readable — probe it, cut it, transcribe it.

Contract: qa/contracts/video-learning.md VL1. Runs on the HOST, never in the
container: the container has no ffmpeg and no GPU, and the 9GB corpus is never
mounted into it. The chunks land under `projects/<slug>/sources/<id>/` which the
container sees through the existing bind mount, so the two halves meet on disk
and nowhere else.

VL1 degrades explicitly. Supplied narration is reused before optional guarded Gemini
audio transcription. Unavailable narration is recorded as missing, never inferred silence.
Local ASR requires explicit opt-in; default preparation never downloads model weights.
"""

from __future__ import annotations

from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.media import chunks as chunk_mod
from autotester.media import frames as frame_mod
from autotester.media import probe as probe_mod
from autotester.media import transcribe as transcribe_mod
from autotester.media.narration import ensure_narration
from autotester.schema.analysis import VideoAnalysis
from autotester.schema.media import MediaChunk, MediaPrep
from autotester.schema.project import Source
from autotester.store.project_store import ProjectStore

PREP_COMMAND = "autotester ingest prep"
"""The registered command, in one place (AT-163).

The refusal used to say `autotester media prep`, which does not exist — the
commands live under `ingest`. It is the message meant to rescue an operator who
cannot run prep where they are, and it sent them to a dead end; my own test
pinned the substring "media prep", so a passing test protected it."""


class SourceNotPrepared(RuntimeError):
    """Raised when a stage needs `media.json` and there is none."""


class UnreadableRecording(RuntimeError):
    """ffmpeg is present and still could not make sense of the file."""


def prepare(store: ProjectStore, source: Source, *,
            chunk_minutes: float = 3.0, overlap_s: float = chunk_mod.DEFAULT_OVERLAP_S,
            use_whisper: bool = False, transcribe_missing: bool = True) -> MediaPrep:
    """Probe, chunk and transcribe `source`, persisting all three.

    Idempotent on the transcript: `transcribe` reuses an existing sidecar
    byte-for-byte rather than regenerating it, so running prep twice cannot
    change what a tester is recorded as having said."""
    if source.path is None:
        raise ValueError(f"source {source.id} has no path to prepare")
    video = Path(source.path)
    if not video.is_file():
        raise FileNotFoundError(f"{source.id} points at {video}, which is not a readable file")

    transcript = _prepare_narration(store, source, video, use_whisper, transcribe_missing)

    if not probe_mod.ffmpeg_available():
        prep = _unchunked(source, video, transcript.source_id)
    else:
        duration_s, width, height = probe_mod.probe(video)
        plan = chunk_mod.plan_chunks(duration_s, chunk_s=chunk_minutes * 60.0,
                                     overlap_s=overlap_s)
        if not plan:
            # AT-164: ffmpeg is HERE and could not read this file. Persisting
            # zero chunks let the CLI print a green success line for a source
            # nothing can ever watch -- the precise shape `_unchunked` exists
            # to prevent, arrived at through the other branch.
            raise UnreadableRecording(
                f"{source.id}: ffmpeg is installed but read no duration from {video.name} "
                f"— the file is empty or not a video this ffmpeg understands")
        out_dir = store.paths.source_chunks_dir(source.id)
        try:
            cut = chunk_mod.encode_chunks(video, out_dir, plan)
        except Exception as exc:
            # AT-166: a failed cut escaped as a raw traceback. A partial chunk
            # set is worse than none: it looks like a complete plan.
            raise UnreadableRecording(
                f"{source.id}: ffmpeg could not cut {video.name} "
                f"({type(exc).__name__}) — no media.json written") from exc
        prep = MediaPrep(
            source_id=source.id, duration_s=duration_s,
            width=width, height=height, chunks=cut,
            transcript_ref=transcript.source_id,
            ffmpeg_version=probe_mod.ffmpeg_version(),
        )
    store.save_media_prep(prep)
    return prep


def _prepare_narration(store: ProjectStore, source: Source, video: Path,
                       use_whisper: bool, transcribe_missing: bool):
    """Reuse supplied evidence; local ASR stays explicit and Gemini stays capability-gated."""
    prior = store.load_transcript(source.id)
    if prior is not None and prior.engine != "none":
        return prior
    if use_whisper or not transcribe_missing:
        transcript = transcribe_mod.transcribe(video, source.id, use_whisper=use_whisper)
        store.save_transcript(transcript)
    else:
        project = store.load_project()
        secrets = SecretStore.load(project, store.paths.env_file, strict=False) if project else None
        transcript = ensure_narration(store, source, secrets=secrets)

    return transcript


def _unchunked(source: Source, video: Path, transcript_ref: str) -> MediaPrep:
    """The no-ffmpeg shape: one chunk that IS the original file.

    Deliberately not an empty chunk list. A caller iterating `prep.chunks` then
    does the right thing on a host without ffmpeg instead of silently doing
    nothing, and the absent `ffmpeg_version` is what records why there is one
    chunk rather than twelve."""
    return MediaPrep(
        source_id=source.id,
        chunks=[MediaChunk(index=0, path=str(video), offset_s=0.0,
                           length_s=source.duration_s or 0.0)],
        transcript_ref=transcript_ref, ffmpeg_version=None,
    )


def extract_frames(store: ProjectStore, source: Source,
                   analysis: VideoAnalysis) -> list[Path]:
    """Pull the stills the vision pass named (`screenshot_ts`).

    Returns only the frames that actually landed. A missing still is a gap in
    the evidence, not a failed analysis — and `product_map` references a PNG
    only when it exists, so a half-extracted set degrades to fewer pictures
    rather than to broken links (A5)."""
    if source.path is None:
        raise ValueError(f"source {source.id} has no path")
    video = Path(source.path)
    if not video.is_file():
        # AT-173: without this, every extract failed quietly and the caller
        # reported "0 frames written" as a success -- indistinguishable from a
        # recording that genuinely had no stills to take.
        raise FileNotFoundError(
            f"{source.id} points at {video}, which is not a readable file — "
            f"no frames can be extracted")
    out_dir = store.paths.source_frames_dir(source.id)

    wanted = sorted({t for screen in analysis.screens for t in screen.screenshot_ts})
    written: list[Path] = []
    for t_s in wanted:
        png = out_dir / frame_mod.frame_name(t_s)
        # AT-165: `png.exists()` reused ANY file at the expected name, and
        # `st_size > 0` closed only the EMPTY half -- a 277KB frame truncated to
        # 92KB by a killed ffmpeg was still served as evidence, and cached
        # forever. The cache gates on a WHOLE png now.
        if frame_mod.is_complete_png(png):
            written.append(png)
            continue
        if frame_mod.extract_frame(video, t_s, png):
            written.append(png)
    return written


def require_prepared(store: ProjectStore, source_id: str) -> MediaPrep:
    """`media.json` or a refusal that names the host command that makes one.

    The analyze stage runs in the container, where prep cannot be performed at
    all, so "run it here" is not advice it can give — the message has to send
    the operator to the host (VL1)."""
    prep = store.load_media_prep(source_id)
    if prep is None:
        raise SourceNotPrepared(
            f"{source_id} has no media.json — run `{PREP_COMMAND} "
            f"{store.paths.slug} {source_id}` on the HOST first (the container "
            f"has no ffmpeg)")
    return prep
