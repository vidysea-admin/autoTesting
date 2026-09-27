"""AT-550 — the requested vision ensemble survives on the artifact even when
credential availability shrinks it before a single provider call is made.

Contract: qa/contracts/video-learning.md VL3 ("an analysis says what it is
made of") extended to ensemble level. VL3 already covers a provider that was
CALLED and failed (`observations_used`/`observations_expected`); this file
covers the AT-542 ensemble being filtered down to `.available()` providers
in `ui/routes_sources.py` *before* `analyze` ever runs — a provider dropped
there leaves no trace in `observations_expected` at all, because `expected`
is computed from the already-shrunk list. A 2-provider config with one
missing credential used to persist a `VideoAnalysis` that read as a complete
2-model agreement (the exact F-039/AT-542 overstatement).

The fix threads the ORIGINALLY REQUESTED provider labels through
`analyze()` -> `adjudicate()` -> `VideoAnalysis.requested_providers`,
independent of `provider_labels` (who actually answered) and of
`observations_expected` (how many calls among the ready providers landed).
`VideoAnalysis.degraded_providers` is the two sets' difference.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from video_fakes import SpyProvider, prepared

from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider
from autotester.schema.media import MediaChunk, MediaPrep
from autotester.schema.observation import ObservedScreen, VideoObservation
from autotester.schema.project import Project, ProviderConfig
from autotester.stages.adjudicate import adjudicate
from autotester.stages.analyze_video import analyze
from autotester.stages.ingest import register_source
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

__all__ = ["prepared"]


# -- pure layer: adjudicate() records requested vs. answered -----------------

def test_adjudicate_records_the_requested_ensemble_separately_from_who_answered() -> None:
    """Two providers were requested; only one ever produced an observation
    (the other had no credential and was never called). The persisted
    artifact must say both things, not just the one that succeeded."""
    from video_fakes import obs, screen

    analysis = adjudicate(
        [obs("gemini", screens=[screen("Home", 1.0)])], "src_1",
        requested_providers=["gemini", "anthropic"],
    )

    assert analysis.provider_labels == ["gemini"]
    assert analysis.requested_providers == ["anthropic", "gemini"]
    assert analysis.degraded_providers == ["anthropic"], (
        "a requested provider that answered zero observations must show up "
        "as degraded, or a 1-model run reads as the full ensemble")


def test_adjudicate_without_requested_providers_reports_no_degradation() -> None:
    """A caller that never heard of AT-550 (every pre-existing caller) must
    see unchanged behaviour: no explicit requested set means 'no known
    degradation', not a false positive."""
    from video_fakes import obs, screen

    analysis = adjudicate([obs("gemini", screens=[screen("Home", 1.0)])], "src_1")

    assert analysis.requested_providers == analysis.provider_labels == ["gemini"]
    assert analysis.degraded_providers == []


# -- analyze() forwards the caller's real request -----------------------------

def test_analyze_forwards_the_full_requested_ensemble_when_the_caller_pre_filtered(
    prepared,
) -> None:
    """Mirrors `ui/routes_sources.py::analyze_source`: the caller only passes
    the PROVIDERS IT WILL ACTUALLY CALL (`ready`), but tells `analyze` what
    the full configured ensemble was."""
    store, source = prepared
    working = SpyProvider("spy:working")

    analysis = analyze(
        store, source, [working], docs=RepoDocs(),
        requested_providers=["spy:missing-credential", "spy:working"],
    )

    assert analysis.provider_labels == ["spy:working"]
    assert analysis.requested_providers == ["spy:missing-credential", "spy:working"]
    assert analysis.degraded_providers == ["spy:missing-credential"]
    persisted = store.load_analysis(source.id)
    assert persisted is not None and persisted.degraded_providers == ["spy:missing-credential"]


def test_analyze_default_matches_pre_at550_behaviour_for_callers_that_say_nothing(
    prepared,
) -> None:
    """The CLI path (`cli_video.py analyze_cmd`) already passes the FULL
    requested set as `providers` — it never pre-filters by availability, so
    it must keep reporting no degradation when it does not pass the new
    parameter at all."""
    store, source = prepared

    analysis = analyze(store, source, [SpyProvider("spy:pro")], docs=RepoDocs())

    assert analysis.requested_providers == analysis.provider_labels == ["spy:pro"]
    assert analysis.degraded_providers == []


# -- the falsifying case: the real route, a real missing credential ----------

class _NamedFakeProvider(Provider):
    """A provider identified purely by its configured name, with a
    controllable credential — the shape `providers.get(name)` returns in
    production, minus the network call."""

    def __init__(self, name: str, *, has_credential: bool) -> None:
        super().__init__()
        self.id = name
        self._has_credential = has_credential

    def available(self) -> bool:
        return self._has_credential

    def see_video(self, path: Path, prompt: str, schema, options=None, *,
                  prompt_file=None, fed_id=None):
        return VideoObservation(screens=[ObservedScreen(name="Login", t_start=0)])


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


def test_analyze_route_records_the_shrink_when_one_configured_provider_has_no_credential(
    client: TestClient, scratch_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE isolating case from the AT-550 brief: config requests 2 providers
    ("gemini,anthropic"), only "gemini" has a credential. The route must
    still run (degrade, never die — AT-542's policy, unchanged) but the
    persisted analysis must show requested=2, ran=1, never a silent
    full-ensemble claim."""
    store = ProjectStore("demo", scratch_root)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test",
        allowed_domains=["demo.test"],
        providers=ProviderConfig(vision="gemini,anthropic"),
    ))
    recording = tmp_path / "prepared.mp4"
    recording.write_bytes(b"video")
    source = register_source(store, recording, label="Prepared")
    store.save_media_prep(MediaPrep(
        source_id=source.id,
        chunks=[MediaChunk(index=0, path=str(recording), offset_s=0, length_s=3)],
    ))
    fakes = {
        "gemini": _NamedFakeProvider("gemini", has_credential=True),
        "anthropic": _NamedFakeProvider("anthropic", has_credential=False),
    }
    monkeypatch.setattr("autotester.ui.routes_sources.providers.get", lambda name: fakes[name])

    response = client.post(
        f"/projects/demo/sources/{source.id}/analyze", follow_redirects=False)

    assert response.status_code == 303, "a partial ensemble must still degrade, not die"
    analysis = store.load_analysis(source.id)
    assert analysis is not None
    assert analysis.provider_labels == ["gemini"], (
        "only the credentialed provider actually ran")
    assert analysis.requested_providers == ["anthropic", "gemini"], (
        "the artifact must record the FULL configured ensemble, not just "
        "who was ready — this is the field the pre-AT-550 route never wrote")
    assert analysis.degraded_providers == ["anthropic"], (
        "AT-550: a 1-model run must never be indistinguishable from the "
        "2-model agreement F-039/AT-542 advertises")


def test_analyze_route_records_no_degradation_when_the_full_ensemble_has_credentials(
    client: TestClient, scratch_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mirror case: nothing missing, so `requested_providers` and
    `provider_labels` must agree and `degraded_providers` must be empty —
    the honest degradation signal must not fire when nothing degraded."""
    store = ProjectStore("demo", scratch_root)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test",
        allowed_domains=["demo.test"],
        providers=ProviderConfig(vision="gemini,anthropic"),
    ))
    recording = tmp_path / "prepared.mp4"
    recording.write_bytes(b"video")
    source = register_source(store, recording, label="Prepared")
    store.save_media_prep(MediaPrep(
        source_id=source.id,
        chunks=[MediaChunk(index=0, path=str(recording), offset_s=0, length_s=3)],
    ))
    fakes = {
        "gemini": _NamedFakeProvider("gemini", has_credential=True),
        "anthropic": _NamedFakeProvider("anthropic", has_credential=True),
    }
    monkeypatch.setattr("autotester.ui.routes_sources.providers.get", lambda name: fakes[name])

    response = client.post(
        f"/projects/demo/sources/{source.id}/analyze", follow_redirects=False)

    assert response.status_code == 303
    analysis = store.load_analysis(source.id)
    assert analysis is not None
    assert analysis.provider_labels == ["anthropic", "gemini"]
    assert analysis.requested_providers == ["anthropic", "gemini"]
    assert analysis.degraded_providers == []


# -- the second AT-550 gap: an EMPTY vision config silently defaults --------

def test_analyze_route_records_the_default_when_vision_config_is_empty(
    client: TestClient, scratch_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AT-550 remainder: `ProviderConfig.vision_ensemble()` substitutes
    `DEFAULT_VISION_PROVIDER` for an empty config instead of refusing (the
    single-credential-must-still-work policy, unchanged). That substitution
    must be OBSERVABLE on the persisted artifact — not indistinguishable from
    an operator who explicitly typed "gemini". This is the falsifying case:
    it goes RED against the pre-fix `return seen or ["gemini"]`, which had no
    way for a caller to tell the two apart."""
    store = ProjectStore("demo", scratch_root)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test",
        allowed_domains=["demo.test"],
        providers=ProviderConfig(vision=""),
    ))
    recording = tmp_path / "prepared.mp4"
    recording.write_bytes(b"video")
    source = register_source(store, recording, label="Prepared")
    store.save_media_prep(MediaPrep(
        source_id=source.id,
        chunks=[MediaChunk(index=0, path=str(recording), offset_s=0, length_s=3)],
    ))
    fakes = {"gemini": _NamedFakeProvider("gemini", has_credential=True)}
    monkeypatch.setattr("autotester.ui.routes_sources.providers.get", lambda name: fakes[name])

    response = client.post(
        f"/projects/demo/sources/{source.id}/analyze", follow_redirects=False)

    assert response.status_code == 303
    analysis = store.load_analysis(source.id)
    assert analysis is not None
    assert analysis.requested_providers == ["gemini"]
    assert analysis.vision_config_defaulted is True, (
        "an empty vision config that fell back to the default must be "
        "recorded as defaulted, not silently identical to an explicit choice")


def test_analyze_route_records_no_default_when_vision_is_explicitly_gemini(
    client: TestClient, scratch_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mirror case: an operator who explicitly configured `vision="gemini"`
    must NOT be reported as having received a default — same resulting
    ensemble (`["gemini"]`) as the empty-config case above, opposite
    `vision_config_defaulted`."""
    store = ProjectStore("demo", scratch_root)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test",
        allowed_domains=["demo.test"],
        providers=ProviderConfig(vision="gemini"),
    ))
    recording = tmp_path / "prepared.mp4"
    recording.write_bytes(b"video")
    source = register_source(store, recording, label="Prepared")
    store.save_media_prep(MediaPrep(
        source_id=source.id,
        chunks=[MediaChunk(index=0, path=str(recording), offset_s=0, length_s=3)],
    ))
    fakes = {"gemini": _NamedFakeProvider("gemini", has_credential=True)}
    monkeypatch.setattr("autotester.ui.routes_sources.providers.get", lambda name: fakes[name])

    response = client.post(
        f"/projects/demo/sources/{source.id}/analyze", follow_redirects=False)

    assert response.status_code == 303
    analysis = store.load_analysis(source.id)
    assert analysis is not None
    assert analysis.requested_providers == ["gemini"]
    assert analysis.vision_config_defaulted is False
