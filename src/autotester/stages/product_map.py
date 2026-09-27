"""PRODUCT MAP: fold every recording analysis into one navigable screen map.

The merge is deterministic and reuses ``adjudicate.screen_key`` so the video
pipeline has one definition of screen identity. Disk is consulted only to
avoid publishing a screenshot reference until that PNG really exists.
"""

from __future__ import annotations

from autotester.core.ids import content_id
from autotester.core.urls import screen_url_pattern
from autotester.media.frames import frame_name, is_complete_png
from autotester.schema.analysis import AnalysedScreen
from autotester.schema.flowspec import FlowSpec
from autotester.schema.screenmap import Journey, MappedScreen, ScreenMap, ScreenVisit
from autotester.stages.adjudicate import screen_key
from autotester.store.project_store import ProjectStore


def _merge_unique(existing: list[str], incoming: list[str]) -> None:
    for value in incoming:
        if value not in existing:
            existing.append(value)


def _frame_ref(store: ProjectStore, source_id: str, screen: AnalysedScreen) -> str | None:
    for second in sorted(screen.screenshot_ts):
        name = frame_name(second)
        if is_complete_png(store.paths.source_frames_dir(source_id) / name):
            return f"sources/{source_id}/frames/{name}"
    return None


def _new_screen(store: ProjectStore, source_id: str, screen: AnalysedScreen) -> MappedScreen:
    key = screen_key(screen)
    return MappedScreen(
        id=content_id("screen", {"project": store.paths.slug, "key": key}),
        name=screen.name,
        purpose=screen.purpose,
        url_pattern=screen_url_pattern(screen.url),
        fields=list(screen.fields),
        ui_elements=list(screen.ui_elements),
        frame_ref=_frame_ref(store, source_id, screen),
        visits=[ScreenVisit(source_id=source_id, t_start=screen.t_start, t_end=screen.t_end)],
        models_agreeing=screen.models_agreeing,
    )


def _fold_screen(mapped: MappedScreen, source_id: str, screen: AnalysedScreen,
                 frame_ref: str | None) -> None:
    mapped.visits.append(
        ScreenVisit(source_id=source_id, t_start=screen.t_start, t_end=screen.t_end)
    )
    _merge_unique(mapped.fields, screen.fields)
    _merge_unique(mapped.ui_elements, screen.ui_elements)
    mapped.models_agreeing = max(mapped.models_agreeing, screen.models_agreeing)
    if not mapped.purpose and screen.purpose:
        mapped.purpose = screen.purpose
    if not mapped.url_pattern and screen.url:
        mapped.url_pattern = screen_url_pattern(screen.url)
    if not mapped.frame_ref and frame_ref:
        mapped.frame_ref = frame_ref


def build_screen_map(store: ProjectStore) -> ScreenMap:
    """Fold all persisted analyses, with one journey per analysed recording."""
    sources = {source.id: source for source in store.list_sources()}
    folded: dict[str, MappedScreen] = {}
    journeys: list[Journey] = []
    analysed_ids: list[str] = []
    for source_id in sorted(sources):
        analysis = store.load_analysis(source_id)
        if analysis is None:
            continue
        analysed_ids.append(source_id)
        source = sources[source_id]
        journeys.append(Journey(
            source_id=source_id,
            label=source.label or source_id,
            stops=list(analysis.journey),
        ))
        for screen in analysis.screens:
            key = screen_key(screen)
            frame_ref = _frame_ref(store, source_id, screen)
            if key not in folded:
                folded[key] = _new_screen(store, source_id, screen)
            else:
                _fold_screen(folded[key], source_id, screen, frame_ref)
    return ScreenMap(
        project=store.paths.slug,
        screens=[folded[key] for key in sorted(folded)],
        journeys=journeys,
        source_ids=analysed_ids,
    )


def attach_screenshots(spec: FlowSpec, screen_map: ScreenMap) -> FlowSpec:
    """Return a copy of ``spec`` with learned screenshot references attached."""
    result = spec.model_copy(deep=True)
    refs = {" ".join(screen.name.casefold().split()): screen.frame_ref
            for screen in screen_map.screens if screen.frame_ref}
    for screen in result.screens:
        if not screen.screenshot_ref:
            screen.screenshot_ref = refs.get(" ".join(screen.name.casefold().split()))
    return result
