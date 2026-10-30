"""Resolve supplied narration before bounded audio-only extraction and Gemini transcription."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from autotester.browser.secrets import SecretStore
from autotester.media.probe import probe
from autotester.media.transcribe import find_sidecar
from autotester.providers.base import Provider
from autotester.schema.media import Transcript
from autotester.schema.project import Source
from autotester.sources.audio import MAX_AUDIO_BYTES, audio_delivery_ready, transcribe_audio
from autotester.store.project_store import ProjectStore
from autotester.store.run_store import local_blob

MAX_AUDIO_DURATION_S = 3600.0
EXTRACT_TIMEOUT_S = 120.0


def _extract_audio(video: Path, audio: Path) -> None:
    """Refuse oversized-duration media; never silently truncate a recording."""
    executable = shutil.which("ffmpeg")
    duration, _, _ = probe(video)
    if not executable or not math.isfinite(duration) or not 0 < duration <= MAX_AUDIO_DURATION_S:
        raise ValueError("audio extraction unavailable or duration exceeds limit")
    subprocess.run([executable, "-nostdin", "-v", "error", "-i", str(video.resolve()),
                    "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "pcm_s16le", "-fs", str(MAX_AUDIO_BYTES), "-y", str(audio)],
                   check=True, timeout=EXTRACT_TIMEOUT_S,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not audio.is_file() or not 0 < audio.stat().st_size < MAX_AUDIO_BYTES:
        raise ValueError("audio extraction missing or byte limit reached")


def ensure_narration(store: ProjectStore, source: Source, *,
                     provider: Provider | None = None,
                     secrets: SecretStore | None = None) -> Transcript:
    """Run BEFORE teaching-input freeze; supplied empty/unreadable narration is authoritative.

    Missing narration is recorded explicitly. Never send raw video or invoke local ASR.
    Existing successful/supplied transcripts are returned without rewriting their bytes.
    """
    prior = store.load_transcript(source.id)
    if prior is not None and prior.engine != "none":
        return prior
    logical = Path(source.path) if source.path else None  # the sidecar sits beside THIS path
    video = local_blob(logical) if logical else None  # M51: GridFS-backed bytes
    if logical is not None and (sidecar := find_sidecar(logical)):
        transcript = Transcript.read_sidecar(sidecar, source.id)
    elif video is None or not video.is_file():
        transcript = _missing_narration(source.id, "source media unavailable")
    else:
        transcript = _transcribe_video_audio(video, source.id, provider, secrets)
    store.save_transcript(transcript)
    return transcript


def _missing_narration(source_id: str, reason: str) -> Transcript:
    return Transcript(source_id=source_id, engine="none", unreadable_reason=reason)


def _transcribe_video_audio(video: Path, source_id: str, provider: Provider | None,
                            secrets: SecretStore | None) -> Transcript:
    if provider is None:
        from autotester.providers import get

        provider = get("gemini")
    if not provider.available() or not audio_delivery_ready(provider):
        return _missing_narration(source_id, "guarded Gemini audio provider unavailable")
    try:
        with TemporaryDirectory(prefix="narration-") as temporary:
            audio = Path(temporary) / "narration.wav"
            _extract_audio(video, audio)
            values = tuple(secrets.scrub_values().values()) if secrets else ()
            outcome = transcribe_audio(audio, source_id, provider=provider, secrets=values)
            return outcome.transcript or _missing_narration(
                source_id, outcome.note or "narration incomplete")
    except (OSError, ValueError, subprocess.SubprocessError):
        return _missing_narration(
            source_id, "bounded audio extraction failed; narration incomplete")
