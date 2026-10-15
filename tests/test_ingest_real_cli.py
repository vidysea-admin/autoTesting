"""What `autotester ingest run` ACTUALLY does — AT-125/AT-128/AT-129.

Every test here drives the real CLI. That is the whole point: T-131 shipped
with tests proving `VisionOptions` reached the provider *when passed*, while the
only shipped caller passed `None`. Proving a mechanism works is not proving the
product uses it, and this file exists because I kept making that exact mistake.

Contract: qa/contracts/ingest.md I7-I10.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester import providers
from autotester.cli import app
from autotester.providers.mock import MockProvider
from autotester.schema.observation import ObservedScreen, VideoObservation
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    return tmp_path


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> MockProvider:
    """A MockProvider the CLI will really construct, so we can read back what
    the shipped entry point handed it."""
    provider = MockProvider(responses={"vision": [
        VideoObservation(screens=[ObservedScreen(name="Home", t_start=1.0)])]})
    monkeypatch.setattr(providers, "get", lambda _id, **_kw: provider)
    return provider


def a_video(root: Path, body: bytes = b"fake-mp4") -> Path:
    path = root / "erp1.mp4"
    path.write_bytes(body)
    return path


def register(root: Path, path: Path) -> str:
    result = runner.invoke(app, ["ingest", "register", "demo", str(path)])
    assert result.exit_code == 0, result.output
    return ProjectStore("demo", root).list_sources()[-1].id


# -- AT-125: the options must reach the provider FROM THE SHIPPED PATH ------

def test_the_shipped_cli_passes_vision_options(root: Path, spy: MockProvider) -> None:
    """The checker measured `vision_options == [None]` through this exact
    command at 1c8c8e4, so HIGH media resolution never applied in production
    however well the unit test passed."""
    source_id = register(root, a_video(root))

    result = runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    assert result.exit_code == 0, result.output
    assert spy.vision_options and spy.vision_options[0] is not None, (
        "the only shipped entry point handed the provider no options at all")
    assert spy.vision_options[0].seed == 7


def test_the_shipped_cli_injects_the_sidecar_narration(root: Path,
                                                       spy: MockProvider) -> None:
    """The same defect one file over, found while fixing AT-125 and not filed by
    anyone: `build_ingest_prompt` took a transcript and no caller passed one, so
    `{{NARRATION}}` rendered "no speech detected" on every real ingest."""
    video = a_video(root)
    video.with_suffix(".transcript.json").write_text(json.dumps(
        {"segments": [{"start": 1.0, "end": 3.0, "text": "this should say Save"}],
         "speech_seconds": 2.0}), encoding="utf-8")
    source_id = register(root, video)

    runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    prompt = spy.prompts[-1][1] if spy.prompts else ""
    assert "this should say Save" in prompt, (
        "the tester's own words never reached the model")


def test_a_recording_with_no_sidecar_still_ingests(root: Path, spy: MockProvider) -> None:
    """Best-effort: a missing transcript is normal, not an error."""
    source_id = register(root, a_video(root))

    result = runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    assert result.exit_code == 0, result.output


# -- AT-129: the file on disk must still BE the registered recording --------

def test_ingesting_a_recording_that_changed_is_refused(root: Path,
                                                       spy: MockProvider) -> None:
    """Re-registering changed bytes mints a NEW source and leaves the old row
    intact -- right for provenance, wrong for reading. Watching the stale row
    reads the new video while stamping every SourceRef with the old id, which
    is provenance that looks precise and points at the wrong recording."""
    video = a_video(root, b"version-one")
    source_id = register(root, video)
    video.write_bytes(b"version-two-entirely-different")

    result = runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    assert result.exit_code == 2
    assert "has changed since" in result.output
    assert "ingest register" in result.output, "the refusal must say how to fix it"


def test_the_refusal_writes_no_flowspec(root: Path, spy: MockProvider) -> None:
    """A refused ingest leaves no trace -- the same property CN1 requires of a
    refused crawl."""
    video = a_video(root, b"version-one")
    source_id = register(root, video)
    video.write_bytes(b"version-two-entirely-different")

    runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    assert ProjectStore("demo", root).load_flowspec() is None


# -- AT-128: the upload cache must key on content, not on a colliding size --

def test_a_same_size_re_export_is_not_served_from_cache(tmp_path: Path) -> None:
    """The first key was `resolve()::st_size`. A recording re-exported in place
    at the same byte size was a cache HIT, so the model was handed the OLD
    video and produced a confident reading of footage nobody asked about --
    while `core.ids.file_sha256` sat two modules away."""
    from autotester.providers.gemini_files import upload_and_wait

    class Handle:
        def __init__(self, name: str) -> None:
            self.name = name
            self.state = "ACTIVE"

    class Client:
        def __init__(self) -> None:
            self.uploads = 0
            self.files = self

        def upload(self, file: str) -> Handle:
            self.uploads += 1
            return Handle(f"files/{self.uploads}")

        def get(self, name: str) -> Handle:
            return Handle(name)

    video = tmp_path / "v.mp4"
    video.write_bytes(b"A" * 100)
    cache = tmp_path / "uploads.json"
    client = Client()

    upload_and_wait(client, video, cache_path=cache)
    video.write_bytes(b"B" * 100)  # same size, entirely different footage
    upload_and_wait(client, video, cache_path=cache)

    assert client.uploads == 2, "the new recording was served from the old one's cache entry"


def test_the_same_bytes_are_uploaded_once(tmp_path: Path) -> None:
    """The cache must still do its job -- re-uploading a 200MB recording for
    every prompt in an ensemble is the most expensive avoidable thing here."""
    from autotester.providers.gemini_files import upload_and_wait

    class Handle:
        def __init__(self, name: str) -> None:
            self.name = name
            self.state = "ACTIVE"

    class Client:
        def __init__(self) -> None:
            self.uploads = 0
            self.files = self

        def upload(self, file: str) -> Handle:
            self.uploads += 1
            return Handle(f"files/{self.uploads}")

        def get(self, name: str) -> Handle:
            return Handle(name)

    video = tmp_path / "v.mp4"
    video.write_bytes(b"A" * 100)
    cache = tmp_path / "uploads.json"
    client = Client()

    upload_and_wait(client, video, cache_path=cache)
    upload_and_wait(client, video, cache_path=cache)

    assert client.uploads == 1


# -- AT-133/134/135: the fix for "declared but unapplied" had the same defect --

def _sidecar(root: Path, payload: str) -> Path:
    video = a_video(root)
    video.with_suffix(".transcript.json").write_text(payload, encoding="utf-8")
    return video


@pytest.mark.parametrize("payload", [
    "[1, 2, 3]",                                    # AttributeError on raw.get
    '{"segments": ["hi"]}',                         # TypeError on **seg
    "not json at all",                              # ValueError
    '{"segments": [{"start": 0, "end": 2, "text": "x", "confidence": 0.9}]}',  # extra="forbid"
], ids=["top-level-list", "segment-not-a-mapping", "not-json", "unknown-segment-field"])
def test_a_malformed_sidecar_never_stops_an_ingest(root: Path, spy: MockProvider,
                                                   payload: str) -> None:
    """AT-133: `load_sidecar` promised best-effort and caught only
    (OSError, ValueError), while `from_sidecar` raises AttributeError on a
    non-object top level and TypeError on non-mapping segments. The docstring
    said one thing and the code did another -- this unit's own thesis, inside
    the fix for it."""
    source_id = register(root, _sidecar(root, payload))

    result = runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("payload", [
    "[1, 2, 3]",
    '{"segments": [{"start": 0, "end": 2, "text": "real speech", "confidence": 0.9}]}',
])
def test_an_unreadable_sidecar_is_never_reported_as_silence(root: Path, spy: MockProvider,
                                                            payload: str) -> None:
    """AT-134: returning None for an unreadable sidecar made the prompt assert
    "no speech detected" about a recording that demonstrably HAS speech --
    a false statement inside the block the prompt itself labels ground truth.
    Silence is a fine fallback when it is neutral, a defect when it is an
    assertion the reader believes."""
    source_id = register(root, _sidecar(root, payload))

    runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    prompt = spy.prompts[-1][1] if spy.prompts else ""
    assert "no speech detected" not in prompt
    assert "could not be read" in prompt
    assert "do NOT assume the recording is silent" in prompt


def test_a_recording_without_a_sidecar_reports_unavailable_narration(
    root: Path, spy: MockProvider,
) -> None:
    """The other side of AT-134: absent is NOT the same fact as unreadable, and
    the honest line for a truly silent recording must survive the fix."""
    source_id = register(root, a_video(root))

    runner.invoke(app, ["ingest", "run", "demo", source_id, "--provider", "mock"])

    prompt = spy.prompts[-1][1] if spy.prompts else ""
    assert "no supplied transcript" in prompt
    assert "no speech detected" not in prompt


def test_a_source_pointing_at_a_directory_gets_a_typed_refusal(root: Path) -> None:
    """AT-135: `path.exists()` is true for a directory, so `file_sha256` raised
    a raw PermissionError out of the CLI instead of the typed SourceChanged the
    function exists to produce."""
    from autotester.schema.enums import SourceKind
    from autotester.schema.project import Source
    from autotester.stages.ingest import SourceChanged, verify_source_bytes

    folder = root / "not-a-video.mp4"
    folder.mkdir()
    source = Source(project="demo", kind=SourceKind.VIDEO, path=str(folder), sha256="deadbeef")

    with pytest.raises(SourceChanged, match="not a readable file"):
        verify_source_bytes(source)


def test_uploading_a_missing_file_is_a_provider_error(tmp_path: Path) -> None:
    """AT-135, second half: a bare FileNotFoundError escaped `upload_and_wait`,
    which exists precisely so callers see one typed failure."""
    from autotester.providers.base import ProviderError
    from autotester.providers.gemini_files import upload_and_wait

    with pytest.raises(ProviderError, match="not a readable file"):
        upload_and_wait(object(), tmp_path / "nope.mp4")

