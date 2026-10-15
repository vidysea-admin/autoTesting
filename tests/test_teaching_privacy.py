"""Video narration availability and both teaching privacy boundaries stay explicit."""

import pytest
from teaching_helpers import (
    MixedTeacherFake,
    add_local,
    run_teaching,
)

from autotester.schema.enums import SourceKind
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore


@pytest.fixture
def _privacy_store(tmp_path):
    store = ProjectStore("demo", root=tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://example.test"))
    return store

@pytest.mark.parametrize("side", ["input", "output"])
def test_video_prompt_and_returned_artifact_cross_privacy_guard(_privacy_store, side):
    store, provider = _privacy_store, MixedTeacherFake()
    store.paths.env_file.write_text("PASSWORD=sensitive-fixture\n", encoding="utf-8")
    source = add_local(store, "video", SourceKind.VIDEO, "screen.mp4")
    store.paths.sources_index.write_text(
        source.model_copy(
            update={
                "label": "sensitive-fixture student@example.com" if side == "input" else "Video"
            }
        ).model_dump_json()
        + "\n"
    )
    store.save_transcript(
        Transcript(
            source_id=source.id,
            engine="sidecar",
            segments=[
                TranscriptSegment(
                    start=1, end=2, text="sensitive-fixture" if side == "input" else "Save"
                )
            ],
        )
    )
    provider.video_target = "sensitive-fixture student@example.com" if side == "output" else "Play"
    result = run_teaching(store, provider)
    assert result.is_complete and len(provider.videos) == 1
    assert "sensitive-fixture" not in provider.videos[0][1]
    assert "student@example.com" not in provider.videos[0][1]
    assert "sensitive-fixture" not in result.model_dump_json()
    assert "student@example.com" not in result.model_dump_json()


def test_video_without_supplied_narration_is_partial_without_transcription(_privacy_store):
    add_local(_privacy_store, "video", SourceKind.VIDEO, "screen.mp4")
    provider = MixedTeacherFake()
    result = run_teaching(_privacy_store, provider)
    assert not result.is_complete and result.outcomes[0].status == "partial"
    assert len(provider.videos) == 1 and not provider.text_prompts
    assert "no supplied transcript" in provider.videos[0][1]
    assert "no speech detected" not in provider.videos[0][1]
