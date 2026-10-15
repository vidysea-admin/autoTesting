"""Reuse supplied audio transcripts first, otherwise use the guarded Gemini audio seam.

No automatic local ASR or model downloads. Provider failures remain explicit missing
narration. Actual Gemini SDK delivery stays withheld until its bounded-media transport
capability is available; injected Providers let offline tests verify transcription policy.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from autotester.core.paths import RepoDocs
from autotester.core.redact import Redactor, assert_no_raw_secrets
from autotester.media.transcribe import find_sidecar
from autotester.providers.base import Provider, ProviderError
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.transcription import (
    AudioTransportCapability,
    GeminiSegment,
    GeminiTranscription,
)

__all__ = ["AUDIO_SUFFIXES", "GeminiSegment", "GeminiTranscription",
           "TranscriptionOutcome", "transcribe_audio"]

AUDIO_SUFFIXES = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".opus"})

TRANSCRIBE_PROMPT = (RepoDocs().prompts_dir / "transcribe_audio_v1.md").read_text(encoding="utf-8")
MAX_AUDIO_BYTES = 128 * 1024 * 1024



class TranscriptionOutcome(NamedTuple):
    """Transcript or explicit value-free missing-narration diagnostic for source registration."""

    transcript: Transcript | None
    note: str | None


def transcribe_audio(
    path: Path,
    source_id: str,
    *,
    provider: Provider | None,
    secrets: Iterable[str] = (),
) -> TranscriptionOutcome:
    """Supplied transcript first; guarded audio transcription or explicit incomplete state.

    `secrets` gates the model call (SA3): a raw secret value present in the
    prompt raises before anything is sent to Gemini -- the same discipline
    `browser/secrets.py::assert_no_raw_secrets` applies before typing into a
    page.
    """
    if sidecar := find_sidecar(path):
        transcript = Transcript.read_sidecar(sidecar, source_id)
        note = ("extraction_error: supplied transcript unreadable"
                if transcript.engine == "unreadable" else None)
        return TranscriptionOutcome(transcript, note)
    if not path.is_file() or path.stat().st_size > MAX_AUDIO_BYTES:
        return TranscriptionOutcome(
            None, "extraction_error: audio unavailable or exceeds byte limit")
    if provider is None or not provider.available():
        return TranscriptionOutcome(
            None, "extraction_error: Gemini audio provider unavailable; narration incomplete")
    if not audio_delivery_ready(provider):
        return TranscriptionOutcome(
            None, "extraction_error: guarded Gemini media transport unavailable")
    try:
        return _via_gemini(path, source_id, provider, tuple(secrets))
    except ProviderError:
        return TranscriptionOutcome(
            None, "extraction_error: Gemini audio transcription failed; narration incomplete")


def audio_delivery_ready(provider: Provider) -> bool:
    """Mocks are offline; real transports must carry typed, earned safety capabilities."""
    if provider.id == "mock":
        return True
    capability = getattr(provider, "audio_transport_capability", None)
    return (isinstance(capability, AudioTransportCapability) and capability.shared_deadline
            and capability.physical_attempt_accounting and capability.audio_only)



def _via_gemini(
    path: Path, source_id: str, provider: Provider, secrets: Iterable[str]
) -> TranscriptionOutcome:
    """The clean path: one Gemini call over the whole file (no chunking, see
    the module docstring), validated against `assert_no_raw_secrets` first."""
    assert_no_raw_secrets(TRANSCRIBE_PROMPT, secrets)
    result = provider.see_video(path, TRANSCRIBE_PROMPT, GeminiTranscription)
    redactor = Redactor({str(i): value for i, value in enumerate(secrets)})
    segments = [TranscriptSegment(start=s.start, end=s.end, text=redactor.scrub(s.text))
                for s in result.segments]
    transcript = Transcript(
        source_id=source_id,
        segments=segments,
        engine=f"gemini:{provider.label}",
        speech_seconds=round(sum(s.end - s.start for s in segments), 2),
    )
    return TranscriptionOutcome(transcript, None)
