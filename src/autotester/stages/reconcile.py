"""RECONCILE: re-map what each video taught onto the product knowledge graph (D-070 part 2).

One job: take per-video FlowSpecs, the crawl's `ScreenNode`s and (optionally) the saved
FlowSpec, and produce one reconciled FlowSpec plus a `ReconcileReport` -- no human gate.
Screens on one templated route fold to one id (RC4); each video screen is scored against the
crawl and the spec on route, title and element labels with fixed bands (RC5); only ambiguous
rows reach the Provider judge, which cannot promote below the matched bar (RC6); every flow
is kept and classed `ideal | narrated | variant` (RC8-RC10). Pure apart from the judge call:
no disk, no clock, no review status read (contract qa/contracts/reconcile.md, D-073).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from autotester.core.redact import Redactor, assert_no_raw_secrets
from autotester.providers.base import Provider, ProviderError, load_skill_prompt
from autotester.schema.flowspec import (
    Band,
    Flow,
    FlowSpec,
    IdealBasis,
    Possibility,
    ReconcileReport,
    Screen,
    ScreenJudgement,
    ScreenMatch,
    Step,
    StepRef,
)
from autotester.schema.media import Transcript
from autotester.schema.screen_graph import ScreenNode
from autotester.stages.screen_identity import (
    element_labels,
    fold_routes,
    match_signals,
    rewrite_screen_refs,
    route_key,
    screen_labels,
)

MATCHED_AT = 0.8
"""A total (or a judge confidence) at or above this is `matched`. The ONE literal (RC5)."""
AMBIGUOUS_AT = 0.5
"""A total at or above this and below `MATCHED_AT` is `ambiguous`; below it, `new`."""
_WEIGHTS = (2 / 4, 1 / 4, 1 / 4)  # route, title, element labels -- fixed in code (RC5)
SKILL_NAME = "reconcile-screen"
Candidate = tuple[str, str, str | None, str, frozenset[str]]  # kind, id, route, title, labels


def band(total: float) -> Band:
    return "matched" if total >= MATCHED_AT else "ambiguous" if total >= AMBIGUOUS_AT else "new"


def combined_score(route: float, title: float, elements: float) -> float:
    """The pure combination of the three signals; rounded so bands are boundary-exact."""
    return round(sum(w * s for w, s in zip(_WEIGHTS, (route, title, elements), strict=True)), 4)


def _screen_rank(screen: Screen) -> tuple[str, float, str]:
    ref = screen.source_ref
    return (ref.source_id if ref else "", (ref.t_start or 0.0) if ref else 0.0, screen.id)


def _candidates(crawl: list[ScreenNode], screens: list[Screen],
                video_sources: set[str]) -> list[Candidate]:
    nodes = [("crawl", n.id, route_key(n.url_template), n.title or n.name,
              element_labels([e.name for e in n.elements if e.visible and not e.in_row]))
             for n in sorted(crawl, key=lambda n: n.id)]
    spec = [("spec", s.id, route_key(s.url_pattern), s.name, screen_labels(s)) for s in screens
            if not (s.source_ref and s.source_ref.source_id in video_sources)]
    return [*nodes, *spec]


def score_screen(screen: Screen, candidates: list[Candidate]) -> ScreenMatch:
    """RC5: the best candidate by total (ties by candidate id) and its rule band."""
    mine = (route_key(screen.url_pattern), screen.name, screen_labels(screen))
    best: ScreenMatch | None = None
    for kind, cid, c_route, c_title, c_labels in candidates:
        r, t, e = match_signals(*mine, c_route, c_title, c_labels)
        total = combined_score(r, t, e)
        row = ScreenMatch(screen_id=screen.id, candidate=cid, candidate_kind=kind,  # type: ignore[arg-type]
                          route=r, title=t, elements=e, total=total, band=band(total))
        if best is None or (-total, cid) < (-best.total, best.candidate or ""):
            best = row
    return best or ScreenMatch(screen_id=screen.id, band="new")


def build_judge_prompt(screen: Screen, flows: list[Flow], candidate: Candidate,
                       skills_dir: Path | None = None) -> str:
    """The judge sees descriptions only -- never a transcript, screenshot or file (RC12)."""
    actions = [{"action": str(s.action), "target": s.target, "value": s.value,
                "said": s.narration} for f in flows for s in f.steps if s.screen_id == screen.id]
    video = {"name": screen.name, "route": route_key(screen.url_pattern), "cues": screen.signals,
             "fields": [f.label or f.name for f in screen.fields], "actions": actions}
    kind, _, c_route, c_title, c_labels = candidate
    other = {"from": kind, "title": c_title, "route": c_route, "controls": sorted(c_labels)}
    template = load_skill_prompt(SKILL_NAME, skills_dir=skills_dir)
    return (template.replace("{{VIDEO_SCREEN}}", json.dumps(video, sort_keys=True, indent=1))
            .replace("{{CANDIDATE}}", json.dumps(other, sort_keys=True, indent=1)))


def _judged(row: ScreenMatch, prompt: str, provider: Provider | None,
            redactor: Redactor, secrets: list[str]) -> ScreenMatch:
    """RC6: an ambiguous row through the judge. Anything short of a confident answer --
    no judge, a refusal, an error, confidence under the bar -- leaves it ambiguous."""
    if provider is None:
        return row.model_copy(update={"note": "no_judge"})
    prompt = redactor.scrub(prompt)
    try:
        assert_no_raw_secrets(prompt, secrets)
    except ValueError:
        return row.model_copy(update={"note": "refused"})
    try:
        raw = provider.judge(prompt, ScreenJudgement, prompt_file=SKILL_NAME, fed_id=row.screen_id)
        answer = ScreenJudgement.model_validate(raw, from_attributes=True)
    except (ProviderError, ValueError):
        return row.model_copy(update={"note": "judge_error"})
    if answer.confidence < MATCHED_AT:
        return row.model_copy(update={"note": "low_confidence"})
    return row.model_copy(update={"band": "matched" if answer.same_screen else "new",
                                  "decided_by": "judge"})


def verify_narration(flow: Flow, transcripts: dict[str, Transcript],
                     redactor: Redactor) -> tuple[Flow, list[StepRef]]:
    """RC3: a narration stays only as a verbatim quote of its own recording's transcript,
    scrubbed; otherwise it is dropped from the step (the step stays) and reported."""
    steps, rejected = [], []
    for step in flow.steps:
        source = step.source_ref.source_id if step.source_ref else ""
        heard = transcripts.get(source)
        if step.narration and heard and heard.quotes(step.narration, scrub=redactor.scrub):
            step = step.model_copy(update={"narration": redactor.scrub(step.narration)})
        elif step.narration:
            rejected.append(StepRef(flow_id=flow.id, order=step.order, source_ref=step.source_ref,
                                    reason="narration_unverified"))
            step = step.model_copy(update={"narration": None})
        steps.append(step)
    return flow.model_copy(update={"steps": steps}), rejected


def narration_drop_report(dropped: list[StepRef]) -> str | None:
    """AT-785: count and step ids (`flow_id#order`) of dropped narrations, never the text."""
    steps = ", ".join(f"{r.flow_id}#{r.order}" for r in dropped)
    return f"{len(dropped)} narration(s) dropped as unverifiable: {steps}" if dropped else None


def _path(flow: Flow) -> tuple[str | None, ...]:
    return (flow.entry_screen, *(s.screen_id for s in flow.steps), flow.exit_screen)


def _divergence(flow: Flow, ideal: Flow) -> Step | None:
    """The first step where `flow` leaves the ideal path (its last if only the end differs)."""
    theirs = [s.screen_id for s in ideal.steps]
    if flow.entry_screen != ideal.entry_screen:
        return flow.steps[0] if flow.steps else None
    for i, step in enumerate(flow.steps):
        if i >= len(theirs) or step.screen_id != theirs[i]:
            return step
    return flow.steps[-1] if flow.steps else None


def _ideal(members: list[Flow], on_crawl: set[str]) -> tuple[Flow, IdealBasis]:
    """RC9: a flow that walks only crawl-matched screens; else the most common path, ties
    by earliest source id then flow id (`members` arrive in that order); `only` if one path."""
    for flow in members:
        refs = {ref for ref in _path(flow) if ref}
        if refs and refs <= on_crawl:
            return flow, "crawl"
    counts = Counter(_path(f) for f in members)
    if len(counts) == 1:
        return members[0], "only"
    return next(f for f in members if counts[_path(f)] == max(counts.values())), "modal"


def assign_kinds(flows: list[Flow], on_crawl: set[str]) -> tuple[list[Flow], list[Possibility]]:
    """RC9/RC10: per task (flows of one normalised name), one ideal; same path -> narrated;
    any other path -> a variant recorded as an "another possibility". Never a gate."""
    groups: dict[str, list[Flow]] = {}
    for flow in sorted(flows, key=lambda f: (f.source_id or "", f.id)):
        groups.setdefault(" ".join(flow.name.casefold().split()), []).append(flow)
    decided: dict[str, Flow] = {}
    possibilities: list[Possibility] = []
    for task in sorted(groups):
        ideal, basis = _ideal(groups[task], on_crawl)
        for flow in groups[task]:
            same = _path(flow) == _path(ideal)
            update: dict[str, Any] = {"ideal_basis": basis, "variant_of": None, "diverges_at": None,
                                      "kind": "ideal" if flow.id == ideal.id else
                                      "narrated" if same else "variant"}
            if update["kind"] == "variant":
                step = _divergence(flow, ideal)
                update |= {"variant_of": ideal.id, "diverges_at": step.order if step else None}
                possibilities.append(Possibility(
                    flow_id=flow.id, ideal_flow_id=ideal.id, diverges_at=update["diverges_at"],
                    source_ref=step.source_ref if step else None,
                    quote=step.narration if step else None))
            decided[flow.id] = flow.model_copy(update=update)
    return [decided[f.id] for f in flows], possibilities


def _union(existing: FlowSpec | None, videos: list[FlowSpec]) -> tuple[list[Screen], list[Flow]]:
    """Existing rows first, unchanged in order; new video rows after, in a fixed order."""
    screens = list(existing.screens) if existing else []
    flows = list(existing.flows) if existing else []
    seen_s, seen_f = {s.id for s in screens}, {f.id for f in flows}
    new_s = {s.id: s for v in videos for s in v.screens if s.id not in seen_s}
    new_f = {f.id: f for v in videos for f in v.flows if f.id not in seen_f}
    def flow_rank(f: Flow) -> tuple[str, float, str]:
        return (f.source_id or "", min((s.source_ref.t_start or 0.0 for s in f.steps
                                        if s.source_ref), default=0.0), f.id)
    return ([*screens, *sorted(new_s.values(), key=_screen_rank)],
            [*flows, *sorted(new_f.values(), key=flow_rank)])


def _verify_all(existing: FlowSpec | None, videos: list[FlowSpec], flows: list[Flow],
                transcripts: dict[str, Transcript], redactor: Redactor,
                ) -> tuple[list[Flow], list[StepRef]]:
    """RC3 over the kept flows; video inputs are checked too, so a rejection is reported
    on every run and not only the first (RC11)."""
    rejected: dict[tuple[str, int], StepRef] = {}
    kept = []
    for flow in flows:
        flow, rows = verify_narration(flow, transcripts, redactor)
        kept.append(flow)
        rejected.update({(r.flow_id, r.order): r for r in rows})
    for flow in (f for v in videos for f in v.flows):
        rejected.update({(r.flow_id, r.order): r for r in verify_narration(
            flow, transcripts, redactor)[1]})
    return kept, [rejected[k] for k in sorted(rejected)]


def _assemble(existing: FlowSpec | None, videos: list[FlowSpec], screens: list[Screen],
              flows: list[Flow], redactor: Redactor) -> FlowSpec:
    base = existing or FlowSpec(project=videos[0].project,
                                created_at=min(v.created_at for v in videos))
    sources = sorted({*base.source_ids, *(s for v in videos for s in v.source_ids)})
    overview = base.app_overview or next((v.app_overview for v in videos if v.app_overview), None)
    spec = FlowSpec.model_validate(redactor.scrub_obj(base.model_copy(update={
        "screens": screens, "flows": flows, "source_ids": sources, "app_overview": overview,
    }).model_dump(mode="json")))
    if existing is None:
        return spec
    if (spec.fingerprint, spec.source_ids, spec.app_overview) == (
            existing.fingerprint, existing.source_ids, existing.app_overview):
        return existing  # idempotent: no version bump, nothing re-ordered (RC11)
    return spec.model_copy(update={"version": existing.version + 1})


def reconcile(videos: list[FlowSpec], crawl: list[ScreenNode], provider: Provider | None = None,
              *, existing: FlowSpec | None = None, transcripts: dict[str, Transcript] | None = None,
              secrets: dict[str, str] | None = None, skills_dir: Path | None = None,
              ) -> tuple[FlowSpec, ReconcileReport]:
    """Reconcile per-video FlowSpecs into one FlowSpec and say what was decided."""
    if not videos and existing is None:
        raise ValueError("reconcile needs at least one video FlowSpec or an existing FlowSpec")
    redactor = Redactor(secrets or {})
    videos = sorted(videos, key=lambda v: (v.source_ids, v.fingerprint))
    video_sources = {s for v in videos for s in v.source_ids}
    screens, flows = _union(existing, videos)
    screens, alias = fold_routes(screens)
    flows, rejected = _verify_all(existing, videos, [rewrite_screen_refs(f, alias) for f in flows],
                                  transcripts or {}, redactor)
    candidates = _candidates(crawl, screens, video_sources)
    by_id = {c[1]: c for c in candidates}
    matches = []
    for screen in (s for s in screens if s.source_ref and s.source_ref.source_id in video_sources):
        row = score_screen(screen, candidates)
        if row.band == "ambiguous" and row.candidate:
            prompt = build_judge_prompt(screen, flows, by_id[row.candidate], skills_dir)
            row = _judged(row, prompt, provider, redactor, list((secrets or {}).values()))
        matches.append(row)
    decided = {m.screen_id: m.band for m in matches}
    screens = [s.model_copy(update={"video_only": decided[s.id] == "new"}) if s.id in decided
               else s for s in screens]
    on_crawl = {m.screen_id for m in matches if m.band == "matched" and m.candidate_kind == "crawl"}
    flows, possibilities = assign_kinds(flows, on_crawl)
    spec = _assemble(existing, videos, screens, flows, redactor)
    return spec, _report(spec, matches, alias, rejected, possibilities, len(flows))


def _report(spec: FlowSpec, matches: list[ScreenMatch], alias: dict[str, str],
            rejected: list[StepRef], possibilities: list[Possibility], flows_in: int,
            ) -> ReconcileReport:
    ids = {s.id for s in spec.screens}
    unresolved = [StepRef(flow_id=f.id, order=s.order, source_ref=s.source_ref,
                          reason="unresolved_screen")
                  for f in spec.flows for s in f.steps if not s.screen_id or s.screen_id not in ids]
    kinds = Counter(f.kind for f in spec.flows)
    return ReconcileReport(
        matches=matches, folded=dict(sorted(alias.items())), unresolved_steps=unresolved,
        narration_unverified=rejected, possibilities=possibilities,
        kinds={k: kinds.get(k, 0) for k in ("ideal", "narrated", "variant")},
        flows_in=flows_in, flows_out=len(spec.flows))
