"""ANALYZE: run the ensemble over a prepared recording, then adjudicate.

Contract: qa/contracts/video-learning.md VL2/VL3. This is the only stage in
Track A that spends money, and the one rule that shapes it is:

    **a cached observation is never re-requested.**

Every (source, model, prompt, chunk) answer is written to disk the moment it
arrives. A second `analyze` over the same recording makes **zero** provider
calls and produces the same analysis — which is what makes it safe to re-run
after a crash, after a code change, or just to look again. `--force` is the
only way past it, and it says so.

Two models and two prompts per chunk is a deliberate cost: agreement between
independent readings is the strongest signal this pipeline can produce without
a human, and `adjudicate` can only count agreement it was given.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider, ProviderError, load_skill_prompt
from autotester.schema.analysis import VideoAnalysis
from autotester.schema.media import MediaChunk, Transcript
from autotester.schema.observation import ModelObservation, VideoObservation, VisionOptions
from autotester.schema.project import Source
from autotester.stages.adjudicate import adjudicate
from autotester.stages.ingest import load_sidecar, narration_block
from autotester.stages.media_prep import require_prepared
from autotester.store.project_store import ProjectStore

PROMPT_NAMES = ("ingest_video_v1.md", "video_issues_v1.md")
"""Two passes with different questions. One asks what the product IS; the other
asks what is WRONG with it. Asking both in a single prompt produced answers that
were worse at each — a model told to map and criticise at once does neither
carefully.

These stay their pre-T-175 string values on purpose: they are the cache key
(`ModelObservation.prompt_name`, persisted to disk), and an existing project's
cached observations must keep matching after this stage starts reading its
prompt text from `SKILL_NAMES` below instead of `prompts_dir`."""

SKILL_NAMES = {
    "ingest_video_v1.md": "ingest-video",
    "video_issues_v1.md": "video-issues",
}
"""Cache-key prompt name -> the SKILL.md folder that now holds its text (T-175)."""


class NoObservations(RuntimeError):
    """Every provider call failed, so there is nothing to adjudicate."""


class DuplicateProviders(ValueError):
    """Two providers share a `label`, which is the cache key.

    The second would read the first's cached answers, never be called, and
    `models_agreeing` would still say 1 — an ensemble of one wearing the shape
    of an ensemble of two. Agreement between independent readings is the whole
    reason this stage costs money, so a collapsed ensemble is refused loudly
    rather than reported quietly."""


def load_transcript(store: ProjectStore, source: Source) -> Transcript | None:
    """The narration for this recording, preferring what media prep persisted.

    Falls back to the sidecar beside the video so `analyze` still has ground
    truth if prep ran elsewhere — the container sees the bind-mounted project
    directory but not necessarily the corpus."""
    saved = store.load_transcript(source.id)
    if saved is not None:
        return saved
    # AT-216: a malformed sidecar is `engine="unreadable"` (VL1's third state), never
    # the None of a recording nobody transcribed. ingest owns the one sidecar loader.
    return load_sidecar(source)


def build_chunk_prompt(prompt_name: str, source: Source, docs: RepoDocs,
                 chunk: MediaChunk, transcript: Transcript | None) -> str:
    """One chunk's prompt, with only THIS chunk's narration in it.

    Slicing matters: handing a model the whole recording's transcript while it
    watches three minutes of it invites alignment to speech it cannot see, and
    a quote attached to the wrong screen is worse than no quote."""
    template = load_skill_prompt(SKILL_NAMES[prompt_name], skills_dir=docs.skills_dir)
    narration = narration_block(transcript)  # absent, or unreadable: never silence (AT-216)
    if transcript is not None and transcript.segments:
        sliced = transcript.slice(chunk.offset_s, chunk.length_s)
        narration = sliced or "(no speech in this section — do not invent dialogue)"
    return (template
            .replace("{{SOURCE_LABEL}}", source.label or source.id)
            .replace("{{NARRATION}}", narration))


def observe_chunk(store: ProjectStore, source: Source, provider: Provider,
                  prompt_name: str, chunk: MediaChunk, *,
                  docs: RepoDocs, transcript: Transcript | None,
                  options: VisionOptions, force: bool) -> ModelObservation | None:
    """One model's answer for one chunk under one prompt. Cached.

    Returns `None` when the call failed — a single failed chunk must not lose
    the eleven that succeeded, and `adjudicate` is happy with fewer inputs.

    The prompt is built before the cache is consulted because **the prompt text
    is part of the key**. Editing a prompt file leaves its name alone, so a
    name-keyed cache hands back the answer to the question you just stopped
    asking — the failure mode is invisible, and it is the one that makes people
    distrust a cache and disable it."""
    prompt = build_chunk_prompt(prompt_name, source, docs, chunk, transcript)
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    if not force:
        cached = _cached(store, source.id, provider.label, prompt_name,
                         chunk.index, digest)
        if cached is not None:
            return cached

    try:
        answer = provider.see_video(Path(chunk.path), prompt, VideoObservation, options,
                                    prompt_file=prompt_name, fed_id=source.id)
    except ProviderError:
        return None

    observation = ModelObservation(
        source_id=source.id, provider_label=provider.label, prompt_name=prompt_name,
        prompt_sha256=digest,
        chunk_index=chunk.index, offset_s=chunk.offset_s, length_s=chunk.length_s,
        observation=answer,
    )
    store.save_observation(observation)
    return observation


def _cached(store: ProjectStore, source_id: str, label: str, prompt_name: str,
            chunk_index: int, digest: str) -> ModelObservation | None:
    """A cached answer to THIS question, or nothing.

    Unreadable files are skipped rather than raised: a half-written observation
    is the crash this cache exists to survive, and letting it abort `analyze`
    (with `--force` unable to clear it) inverts the whole promise."""
    for observation in store.list_observations(source_id, skip_unreadable=True):
        if (observation.provider_label == label
                and observation.prompt_name == prompt_name
                and observation.chunk_index == chunk_index
                and observation.prompt_sha256 == digest):
            return observation
    return None


def analyze(store: ProjectStore, source: Source, providers: list[Provider], *,
            docs: RepoDocs | None = None, options: VisionOptions | None = None,
            force: bool = False, requested_providers: list[str] | None = None,
            vision_config_defaulted: bool = False) -> VideoAnalysis:
    """Every model, every prompt, every chunk -- adjudicated into one reading.

    Refuses without `media.json` rather than silently analysing an unprepared
    recording as a single blob — prep is where chunking and narration happen,
    and skipping it changes the answer without saying so.

    `requested_providers`/`vision_config_defaulted` (AT-550) let a caller that already
    filtered `providers` (e.g. by credential `.available()`, as the UI route does, or by
    substituting `ProviderConfig`'s empty-config default) still record what it originally
    asked for and whether that ask was itself defaulted — see `stages/adjudicate.py::adjudicate`
    for the full contract. Both default to "no known degradation" when a caller omits them
    (every pre-AT-550 caller, e.g. the CLI passing `providers` as the already-full set)."""
    labels = [p.label for p in providers]
    if len(set(labels)) != len(labels):
        raise DuplicateProviders(
            f"two providers share a label: {sorted(labels)} — the label is the cache key, "
            f"so the ensemble would silently collapse to one reading")

    prep = require_prepared(store, source.id)
    docs = docs or RepoDocs()
    options = options or VisionOptions()
    transcript = load_transcript(store, source)

    observations: list[ModelObservation] = []
    for provider in providers:
        for prompt_name in PROMPT_NAMES:
            for chunk in prep.chunks:
                observation = observe_chunk(
                    store, source, provider, prompt_name, chunk,
                    docs=docs, transcript=transcript, options=options, force=force)
                if observation is not None:
                    observations.append(observation)

    if not observations:
        raise NoObservations(
            f"{source.id}: every provider call failed — nothing to adjudicate. "
            f"Check `autotester providers` for credentials.")

    expected = len(providers) * len(PROMPT_NAMES) * len(prep.chunks)
    analysis = adjudicate(
        observations, source.id, expected=expected,
        requested_providers=requested_providers or [p.label for p in providers],
        vision_config_defaulted=vision_config_defaulted)
    store.save_analysis(analysis)
    return analysis
