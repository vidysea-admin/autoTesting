"""Synthetic Provider and registered-source helpers for teaching tests."""

import json

from autotester.browser.secrets import SecretStore
from autotester.core.ids import file_sha256
from autotester.providers.base import Provider, ProviderError
from autotester.schema.document import DocumentPage, DocumentReading
from autotester.schema.media import Transcript, TranscriptSegment
from autotester.schema.observation import VideoObservation
from autotester.schema.project import Source
from autotester.stages.teach_sources import teach_registered_sources
from autotester.store.filestore import write_json


class MixedTeacherFake(Provider):
    """Observe actual stage routing and return cited synthetic knowledge."""

    def __init__(self):
        super().__init__()
        self.text_prompts = []
        self.videos = []
        self.fail = False
        self.requested = []
        self.video_target = "Play"

    def available(self):
        return True

    def act(self, prompt, schema=None, **kwargs):
        self.text_prompts.append(prompt)
        if self.fail:
            raise ProviderError("sensitive-fixture student@example.com")
        units = json.loads(prompt.split("Teaching units (JSON):\n", 1)[1])
        words = units[0]["text"].split("|")
        name = words[0] if len(words) == 2 else "Home"
        return schema.model_validate(
            {
                "screens": [
                    {
                        "name": name,
                        "locator": units[0]["locator"],
                        "url_pattern": words[1] if len(words) == 2 else None,
                    }
                ],
                "flows": [
                    {
                        "name": "Save",
                        "entry_screen": name,
                        "steps": [
                            {
                                "order": 1,
                                "action": "click",
                                "target": "Save",
                                "locator": units[0]["locator"],
                                "screen": name,
                            }
                        ],
                    }
                ],
            }
        )

    def see_video(self, path, prompt, schema, options=None, **kwargs):
        self.videos.append((path, prompt))
        assert schema is VideoObservation
        return schema.model_validate(
            {
                "screens": [{"name": "Video", "t_start": 2}],
                "flows": [
                    {
                        "name": "Video task",
                        "entry_screen": "Video",
                        "steps": [
                            {
                                "order": 1,
                                "action": "click",
                                "target": self.video_target,
                                "t_start": 3,
                            }
                        ],
                    }
                ],
            }
        )


def run_teaching(store, provider, run_id="mixed"):
    project = store.load_project()
    secrets = SecretStore.load(project, store.paths.env_file, strict=False)

    def resolve(kind):
        provider.requested.append(kind)
        return provider

    return teach_registered_sources(store, run_id, resolve, secrets=secrets)


def add_local(store, source_id, kind, name):
    path = store.paths.root / name
    path.write_bytes(b"synthetic local bytes")
    return store.add_source(
        Source(id=source_id, project="demo", kind=kind, path=str(path), sha256=file_sha256(path))
    )


def add_pdf_receipt(store, source, partial=False):
    pages = [DocumentPage(number=1, text="PDF page text", method="text")]
    if partial:
        pages.append(DocumentPage(number=2, method="unreadable", error="OCR unavailable"))
    reading = DocumentReading(
        source_id=source.id, pages=pages, error="partial extraction" if partial else None
    )
    write_json(store.paths.sources_dir / source.id / "document.json", reading)


def add_supplied_transcript(store, source_id, text, start=1, end=2):
    store.save_transcript(
        Transcript(
            source_id=source_id,
            engine="sidecar",
            segments=[TranscriptSegment(start=start, end=end, text=text)],
        )
    )
