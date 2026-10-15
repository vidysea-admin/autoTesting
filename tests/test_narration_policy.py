"""Offline narration bounds, source precedence and audio-only transport."""

import subprocess
from pathlib import Path

import pytest

from autotester.media import narration, transcribe
from autotester.providers.mock import MockProvider
from autotester.schema.enums import SourceKind
from autotester.schema.media import Transcript
from autotester.schema.project import Project, Source
from autotester.schema.transcription import GeminiSegment, GeminiTranscription
from autotester.stages import media_prep
from autotester.store.project_store import ProjectStore


def _setup(tmp_path):
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test"))
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    source = Source(project="demo", kind=SourceKind.VIDEO, path=str(video))
    return store, source, video


def test_default_transcribe_never_launches_local_asr(tmp_path, monkeypatch):
    monkeypatch.setattr(transcribe, "whisper_available", lambda: True)
    monkeypatch.setattr(transcribe, "transcribe_subprocess", lambda *_: pytest.fail("local ASR"))
    assert transcribe.transcribe(tmp_path / "video.mp4", "src").engine == "none"


def test_persisted_empty_transcript_reused_byte_for_byte(tmp_path, monkeypatch):
    store, source, _ = _setup(tmp_path)
    supplied = Transcript(source_id=source.id, engine="sidecar", segments=[])
    store.save_transcript(supplied)
    monkeypatch.setattr(narration, "_transcribe_video_audio", lambda *_: pytest.fail("provider"))
    assert narration.ensure_narration(store, source) == supplied
    monkeypatch.setattr(transcribe, "transcribe", lambda *_args, **_kwargs: pytest.fail("ASR"))
    monkeypatch.setattr(media_prep.probe_mod, "ffmpeg_available", lambda: False)
    media_prep.prepare(store, source, use_whisper=True)
    assert store.load_transcript(source.id) == supplied


def test_video_sends_only_extracted_audio_and_cleans_scratch(tmp_path, monkeypatch):
    store, source, _ = _setup(tmp_path)
    seen = []
    class AudioProvider(MockProvider):
        def see_video(self, path, prompt, schema, options=None):
            assert path.suffix == ".wav" and path.read_bytes() == b"audio"
            seen.append(path)
            return GeminiTranscription(segments=[GeminiSegment(start=0, end=1, text="hello")])
    monkeypatch.setattr(narration, "_extract_audio", lambda _, output: output.write_bytes(b"audio"))
    transcript = narration.ensure_narration(store, source, provider=AudioProvider())
    assert transcript.segments[0].text == "hello"
    assert len(seen) == 1 and not seen[0].exists()


def test_extraction_bounds_reject_duration_and_truncated_output(tmp_path, monkeypatch):
    _, _, video = _setup(tmp_path)
    monkeypatch.setattr(narration.shutil, "which", lambda _: "ffmpeg")
    monkeypatch.setattr(narration, "probe", lambda _: (float("inf"), 0, 0))
    with pytest.raises(ValueError, match="duration"):
        narration._extract_audio(video, tmp_path / "audio.wav")
    monkeypatch.setattr(narration, "probe", lambda _: (1, 0, 0))
    monkeypatch.setattr(narration, "MAX_AUDIO_BYTES", 3)
    def run(args, **kwargs):
        assert kwargs["timeout"] == narration.EXTRACT_TIMEOUT_S
        assert "-vn" in args and "-fs" in args and "-nostdin" in args
        Path(args[-1]).write_bytes(b"abc")
    monkeypatch.setattr(narration.subprocess, "run", run)
    with pytest.raises(ValueError, match="byte limit"):
        narration._extract_audio(video, tmp_path / "audio.wav")


def test_extraction_failure_stays_explicit_and_cleans_scratch(tmp_path, monkeypatch):
    store, source, _ = _setup(tmp_path)
    paths = []
    def fail(_, output):
        paths.append(output)
        raise subprocess.TimeoutExpired("private input", 1)
    monkeypatch.setattr(narration, "_extract_audio", fail)
    result = narration.ensure_narration(store, source, provider=MockProvider())
    assert result.engine == "none" and "incomplete" in result.unreadable_reason
    assert "private" not in result.unreadable_reason
    assert not paths[0].parent.exists()


def test_media_prep_calls_narration_by_default(tmp_path, monkeypatch):
    store, source, _ = _setup(tmp_path)
    calls = []
    def ensured(store, source, **kwargs):
        calls.append(source.id)
        return Transcript(source_id=source.id, engine="none")
    monkeypatch.setattr(media_prep, "ensure_narration", ensured)
    monkeypatch.setattr(media_prep.probe_mod, "ffmpeg_available", lambda: False)
    media_prep.prepare(store, source)
    assert calls == [source.id]


def test_real_transport_requires_typed_safety_capabilities(tmp_path):
    from autotester.sources.audio import transcribe_audio
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    provider = MockProvider()
    provider.id = "gemini"
    provider.bounded_audio = True  # an untyped truthy promise cannot enable delivery
    outcome = transcribe_audio(audio, "src", provider=provider)
    assert outcome.transcript is None and "guarded" in outcome.note
    assert provider.prompts == []


def test_audio_byte_limit_and_output_secret_scrubbing(tmp_path, monkeypatch):
    from autotester.sources import audio as module
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    provider = MockProvider(responses={"vision": [GeminiTranscription(
        segments=[GeminiSegment(start=0, end=1, text="SECRET-123")])]})
    monkeypatch.setattr(module, "MAX_AUDIO_BYTES", 2)
    assert module.transcribe_audio(audio, "src", provider=provider).transcript is None
    assert provider.prompts == []
    monkeypatch.setattr(module, "MAX_AUDIO_BYTES", 128)
    outcome = module.transcribe_audio(audio, "src", provider=provider, secrets=["SECRET-123"])
    assert "SECRET-123" not in outcome.transcript.model_dump_json()


def test_cli_prep_does_not_opt_in_local_asr(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from autotester import cli_video
    from autotester.schema.media import MediaPrep
    _, source, _ = _setup(tmp_path)
    calls = []
    monkeypatch.setattr(cli_video, "_require_source", lambda *_: source)
    def prepare(*args, **kwargs):
        calls.append(kwargs)
        return MediaPrep(source_id=source.id)
    monkeypatch.setattr(media_prep, "prepare", prepare)
    result = CliRunner().invoke(cli_video.app, ["prep", "demo", source.id])
    assert result.exit_code == 0, result.output
    assert calls[0]["use_whisper"] is False
    assert calls[0]["transcribe_missing"] is True
