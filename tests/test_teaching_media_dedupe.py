"""Media content dedupe ignores transcript envelopes while preserving the taught source."""

import pytest
from teaching_helpers import MixedTeacherFake, add_local, add_supplied_transcript, run_teaching

from autotester.schema.enums import SourceKind
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore


@pytest.mark.parametrize("kind", [SourceKind.AUDIO, SourceKind.VIDEO])
def test_duplicate_media_uses_transcript_content_not_its_envelope(tmp_path, kind):
    store = ProjectStore("demo", root=tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://example.test"))
    suffix = ".wav" if kind is SourceKind.AUDIO else ".mp4"
    for source_id in ["a", "b"]:
        source = add_local(store, source_id, kind, source_id + suffix)
        add_supplied_transcript(store, source.id, "Same supplied narration")
    provider = MixedTeacherFake()
    result = run_teaching(store, provider)
    assert result.is_complete and len(result.outcomes) == 2
    assert len(provider.text_prompts) + len(provider.videos) == 1
    assert result.outcomes[1].status == "duplicate" and result.outcomes[1].duplicate_of == "a"
    assert {flow.source_id for flow in result.proposal.flows} == {"a"}
