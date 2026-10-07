"""INGEST: turn a video Source into a FlowSpec, provenance-tracked to the second.

Contract: qa/contracts/ingest.md I1-I5. Every `Step` this stage produces carries
a `SourceRef` back to the exact video timestamp it was read from, so a human
reviewing the resulting `FlowSpec` can jump straight to the second the system
learned a given action — the same discipline `stages/execute.py`/`grade.py`
apply to their own evidence.
"""

from __future__ import annotations

from pathlib import Path

from autotester.browser.secrets import SecretStore
from autotester.core.ids import content_id, file_sha256
from autotester.core.paths import RepoDocs
from autotester.core.redact import Redactor
from autotester.core.urls import screen_url_pattern
from autotester.providers.base import Provider, load_skill_prompt
from autotester.schema.base import Provenance
from autotester.schema.enums import ReviewStatus, SourceKind
from autotester.schema.flowspec import Flow, FlowSpec, InputField, Screen, SourceRef, Step, StepRef
from autotester.schema.media import Transcript
from autotester.schema.observation import (
    ObservedFlow,
    ObservedScreen,
    ObservedStep,
    VideoObservation,
    VisionOptions,
)
from autotester.schema.project import Source
from autotester.stages.reconcile import verify_narration
from autotester.store.project_store import ProjectStore

SKILL_NAME = "ingest-video"  # skills/ingest-video/SKILL.md (T-175, was prompts/ingest_video_v1.md)
UNREADABLE = "unreadable"
"""`Transcript.engine` for a sidecar that exists and could not be parsed — the
one state that must never be reported to the model as silence (AT-134)."""


class FlowSpecApproved(RuntimeError):
    """Raised rather than overwriting a FlowSpec a human already approved (I6)."""


def build_ingest_prompt(source: Source, docs: RepoDocs,
                        transcript: Transcript | None = None) -> str:
    """The prompt, with the human's own narration injected as GROUND TRUTH.

    A tester saying "this should be X" is the highest-value signal in a recording. The
    model is told to ALIGN to the transcript, not re-transcribe: asked to do both, it
    paraphrases speech into something plausible, and a paraphrased complaint is a
    fabricated one."""
    template = load_skill_prompt(SKILL_NAME, skills_dir=docs.skills_dir)
    return (template
            .replace("{{SOURCE_LABEL}}", source.label or source.id)
            .replace("{{NARRATION}}", narration_block(transcript)))


def narration_block(transcript: Transcript | None) -> str:
    """What the prompt says about speech — three states, never conflated (AT-134).

    Telling a model "no speech detected" about a recording that HAS speech is
    not a missing feature, it is a false statement in a block the prompt itself
    labels ground truth. An unreadable sidecar is a different fact from silence
    and has to read as one, or the model confidently reports a silent video."""
    if transcript is not None and transcript.segments:
        return transcript.slice(0.0, transcript.segments[-1].end)
    if transcript is not None and transcript.engine == UNREADABLE:
        return ("(a transcript file exists beside this recording but could not be read — "
                "do NOT assume the recording is silent, and do not invent dialogue)")
    return "(no speech detected — do not invent dialogue)"


RECORDING_SUFFIXES = frozenset({".avi", ".mkv", ".mov", ".mp4", ".webm"})
"""What a recording source may be. The ONE definition: the upload route and this
function both read it, so they cannot drift (AT-433)."""


class NotARecording(ValueError):
    """A path or upload that is not a recording by suffix. Its message never
    repeats the submitted name — a credential pasted into the box must not echo."""


def require_recording_suffix(name: str) -> str:
    """The lower-cased suffix, or `NotARecording` (AT-433).

    Before this, a source registered by path was checked only for existing, and
    an upload with an unknown suffix was silently renamed `.video`. Live
    validation registered `C:\\Windows\\win.ini` and the repo's own `.env`
    credential file as VIDEO sources, each shown with its full path and an
    Analyze button. A `.env` is refused here too: for a dotfile
    `Path(".env").suffix` is `""`, which is not a recording suffix."""
    suffix = Path(name).suffix.lower()
    if suffix not in RECORDING_SUFFIXES:
        raise NotARecording(
            "that is not a recording — add a video file ending in "
            + ", ".join(sorted(RECORDING_SUFFIXES)))
    return suffix


def register_source(store: ProjectStore, path: Path, *, label: str | None = None,
                    recorded_on: str | None = None, url: str | None = None,
                    provenance: Provenance | None = None) -> Source:
    """Record a video on disk as a `Source`. Idempotent on content: the same
    bytes registered twice return the existing row rather than a second id, so
    re-running a shell command never silently doubles the corpus.

    `url` and `provenance` are optional and default to `None` (every existing
    caller is unchanged): `register_drive` passes the Drive file id in `url` and
    a `Provenance` linking the recording to its Drive folder (SA4), so a video
    fetched from Drive goes through this ONE video adapter rather than a
    reimplementation (SA1)."""
    require_recording_suffix(path.name)
    if not path.exists():
        raise FileNotFoundError(f"no such recording: {path}")
    if not path.is_file():  # AT-446: `dir.mp4` passes the suffix rule and exists()
        raise NotARecording("that is a folder, not a recording file")
    digest = file_sha256(path)
    for existing in store.list_sources():
        if existing.sha256 == digest:
            return existing
    return store.add_source(Source(
        project=store.paths.slug, kind=SourceKind.VIDEO, path=str(path.resolve()),
        sha256=digest, label=label, recorded_on=recorded_on, url=url, provenance=provenance,
    ))


def _to_screen(observed: ObservedScreen, source_id: str) -> Screen:
    """One observed screen as a FlowSpec `Screen`.

    `url_pattern` is templated through the SAME `url_template` the crawler uses
    (I7), so a screen learned from a video and the same screen found by a crawl
    produce one row and not two. It is set only when a url was actually visible
    in the recording -- inventing one would make coverage report a gap closed
    that nothing has seen.

    `observed.fields` are the visible input LABELS (list[str]); FlowSpec wants
    `InputField`s, so each label becomes one (`name` and `label` both the label --
    the video shows no DOM name). Repeated labels are kept as seen, not deduped."""
    return Screen(
        id=content_id("scr", {"name": observed.name, "signals": sorted(observed.signals)}),
        name=observed.name,
        signals=observed.signals,
        url_pattern=screen_url_pattern(observed.url),
        fields=[InputField(name=label, label=label) for label in observed.fields],
        source_ref=SourceRef(source_id=source_id, t_start=observed.t_start,
                             t_end=observed.t_end),
    )


def flow_id(name: str, source_id: str) -> str:
    """A video flow's id: its name AND the recording it came from (reconcile RC8).
    Name-only ids made two recordings' "Login" flows one id, and `_new_flows`
    silently dropped the second."""
    return content_id("flow", {"name": name, "source": source_id})


def legacy_flow_id(name: str) -> str:
    """The pre-RC8 name-only id; saved specs keep it, `merge_flowspec` recognises it."""
    return content_id("flow", {"name": name})


def _to_step(s: ObservedStep, source_id: str, screen_ids: dict[str, str]) -> Step:
    """One observed action, keeping the evidence of intent (RC2): the presenter's
    words, the visible text, and the screen it happened on (RC1). A screen name no
    screen carries stays `None` -- reconcile reports it, nothing guesses it."""
    return Step(
        order=s.order, action=s.action, target=s.target, value=s.value,
        source_ref=SourceRef(source_id=source_id, t_start=s.t_start, t_end=s.t_end),
        screen_id=screen_ids.get(s.screen) if s.screen else None,
        narration=s.narration or None, on_screen_text=s.on_screen_text or None,
    )


def _to_flow(observed: ObservedFlow, source_id: str, screen_ids: dict[str, str]) -> Flow:
    exit_name = observed.exit_screen or None
    return Flow(
        id=flow_id(observed.name, source_id),
        name=observed.name,
        entry_screen=screen_ids.get(observed.entry_screen, observed.entry_screen),
        exit_screen=screen_ids.get(exit_name, exit_name) if exit_name else None,
        steps=[_to_step(s, source_id, screen_ids) for s in observed.steps],
    )


def load_sidecar(source: Source) -> Transcript | None:
    """The `<video>.transcript.json` sitting beside the recording, if there is one.

    Best-effort: a malformed sidecar must not stop an ingest (AT-125, AT-133). An absent
    sidecar asserts silence; a present-but-unreadable one says exactly that, because "no
    speech detected" about a recording that has speech is a false statement (AT-134).
    """
    if source.path is None:
        return None
    sidecar = Path(source.path).with_suffix(".transcript.json")
    if not sidecar.exists():
        return None
    return Transcript.read_sidecar(sidecar, source.id)  # unreadable keeps its cause (AT-466)


class SourceChanged(RuntimeError):
    """The file a Source names is no longer the file it was registered from."""


def verify_source_bytes(source: Source) -> None:
    """Refuse to watch a recording that is not the one this Source describes (AT-129).

    `register_source` is immutable by design: re-registering changed bytes
    mints a NEW source and leaves the old row intact. That is right for
    provenance and wrong for reading — the stale row still points at the same
    path, so ingesting it watches the new video while stamping every
    `SourceRef` with the old source's id. The result is provenance that reads
    as precise and points at the wrong recording, which is worse than an error
    because a human reviewing it has no reason to doubt it."""
    if source.path is None or source.sha256 is None:
        return
    path = Path(source.path)
    if not path.is_file():
        raise SourceChanged(
            f"{source.id} points at {path}, which is not a readable file any more — "
            f"re-register the recording.")
    try:
        actual = file_sha256(path)
    except OSError as exc:  # AT-135: a typed refusal, never a raw traceback out of the CLI
        raise SourceChanged(
            f"{source.id} points at {path}, which could not be read "
            f"({type(exc).__name__}: {exc}) — re-register the recording.") from exc
    if actual != source.sha256:
        raise SourceChanged(
            f"{path.name} has changed since {source.id} was registered "
            f"({source.sha256[:12]} -> {actual[:12]}). Re-register it: "
            f"`autotester ingest register {source.project} \"{path}\"` mints a new source "
            f"for the new bytes, and this one keeps describing the old recording.")


def persist_ingest(store: ProjectStore, spec: FlowSpec, *, replace: bool = False) -> FlowSpec:
    """Write the FlowSpec, refusing to discard an APPROVED one (I6).

    Persisting blindly would overwrite a spec a human reviewed and approved, throwing
    away the review, not just the data. `--replace` is how a human says they meant it."""
    existing = store.load_flowspec()
    if existing is not None and existing.review.status is ReviewStatus.APPROVED and not replace:
        raise FlowSpecApproved(
            f"{store.paths.slug}'s FlowSpec is APPROVED (v{existing.version}) — "
            f"ingesting would discard that review. Re-run with --replace to overwrite, "
            f"or merge instead once merge_flowspec exists.")
    store.save_flowspec(spec)
    return spec


def ingest_video(
    source: Source, project_slug: str, provider: Provider, docs: RepoDocs | None = None,
    *, transcript: Transcript | None = None, options: VisionOptions | None = None,
    redactor: Redactor | None = None, dropped: list[StepRef] | None = None,
) -> FlowSpec:
    """Watch `source` (a video `Source`) and produce a fresh `FlowSpec` for
    `project_slug`. Does not merge with an existing `FlowSpec` — a human reviews
    and merges via the review gate (T-065), which is a separate, later stage.
    AT-779 / RC3: a narration is saved only as a verbatim quote of `transcript`, scrubbed
    by `redactor` (default: the project's own secrets); one that is not is dropped
    and listed in `dropped` (AT-785)."""
    if source.path is None:
        raise ValueError(f"source {source.id} has no path to watch")
    verify_source_bytes(source)
    docs = docs or RepoDocs()
    prompt = build_ingest_prompt(source, docs, transcript)
    observation = provider.see_video(Path(source.path), prompt, VideoObservation, options,
                                      prompt_file=SKILL_NAME, fed_id=source.id)
    spec = flowspec_from_observation(observation, source.id, project_slug)
    heard = {source.id: transcript} if transcript else {}
    redactor = _project_redactor(project_slug) if redactor is None else redactor
    checked = [verify_narration(f, heard, redactor) for f in spec.flows]
    if dropped is not None:
        dropped.extend(ref for _, refs in checked for ref in refs)
    return spec.model_copy(update={"flows": [f for f, _ in checked]})


def _project_redactor(slug: str) -> Redactor:
    """The project's SecretStore redactor, or an empty one when it has no project yet."""
    store = ProjectStore(slug)
    project = store.load_project()
    if project is None:
        return Redactor({})
    return SecretStore.load(project, store.paths.env_file, strict=False).redactor()


def flowspec_from_observation(observation: VideoObservation, source_id: str,
                              project_slug: str) -> FlowSpec:
    """A vision reading as a fresh FlowSpec: ids minted, provenance attached. Pure --
    no provider, no disk -- so reconcile's frozen fixture runs the same mapping."""
    screen_ids: dict[str, str] = {}
    screens: list[Screen] = []
    for observed in observation.screens:
        screen = _to_screen(observed, source_id)
        screen_ids.setdefault(observed.name, screen.id)
        if screen.id not in {s.id for s in screens}:  # AT-034: same screen named twice -> one row
            screens.append(screen)
    flows = [_to_flow(f, source_id, screen_ids) for f in observation.flows]
    return FlowSpec(project=project_slug, screens=screens, flows=flows,
                    source_ids=[source_id], app_overview=observation.summary)
