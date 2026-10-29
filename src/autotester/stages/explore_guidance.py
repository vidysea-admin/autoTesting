"""Model-guided ORDER of one screen's controls, with bounds, fallback and KG reuse (D-118).

One job: own the single model call a guided crawl makes per screen (qa/contracts/crawl-guidance.md
G2-G10). This is the ONLY `stages/explore_*` module that touches the provider seam, and it imports
no vendor SDK (C8). The model sees the redacted text payload built in `explore_guidance_payload`
and returns indices only; everything it orders still passes the deny-list, the write matrix, the
typing gate, `allowed_domains`, the host re-check, the signed approval and every `CrawlBounds`
bound unchanged, because only the ORDER of an already-built list changes.

Every failure (unavailable, timeout, garbage, guard refusal, spent budget, open breaker) yields the
rule order for that screen with a recorded reason, never an exception. Three consecutive failures
switch guidance off for the rest of the crawl. A ranking is stored as an advisory annotation on the
screen's node in the persona knowledge graph, keyed by fingerprint + candidate hash + prompt
version + exact model tag, and replayed on a hit with zero calls (G7). Off is the default (G5).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from autotester.core.ids import content_hash
from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.availability import AvailabilityFailure
from autotester.providers.base import Provider, ProviderError, load_skill_prompt
from autotester.schema.crawl import CrawlBounds
from autotester.schema.crawl_guidance import (
    DEFAULT_MODEL_CALL_TIMEOUT_S,
    DEFAULT_MODEL_TOTAL_S,
    CrawlGuidance,
    GuidanceAnnotation,
    GuidanceFallback,
    NextActionRanking,
)
from autotester.schema.portal_persona import GraphNode, PortalPersona
from autotester.schema.project import Project
from autotester.schema.screen_graph import ElementRef, ScreenNode
from autotester.stages import explore_guidance_payload as pl

if TYPE_CHECKING:
    from autotester.stages.explore_runtime import ExploreRuntime

GUIDANCE_MODELS = ("ollama_chat/deepseek-v4.1-flash:1017", "ollama_chat/glm-5.3-flash")
"""G8: pinned, in this order. The untagged `deepseek-v4.1-flash` is an older snapshot; no Gemini."""
GUIDANCE_SPEC = "model-chain:" + ",".join(GUIDANCE_MODELS)
SKILL = "crawl-next-action"
STRIKES = 3
KEEP_PER_NODE = 5
REASON_CHARS = 200


def limits(bounds: CrawlBounds) -> tuple[int, float, float] | None:
    """(calls, per-call s, total s) when every guidance bound is on, else None (G5/G6)."""
    per = (DEFAULT_MODEL_CALL_TIMEOUT_S if bounds.model_call_timeout_s is None
           else bounds.model_call_timeout_s)
    total = DEFAULT_MODEL_TOTAL_S if bounds.model_total_s is None else bounds.model_total_s
    if not bounds.max_model_calls or not per or not total:
        return None
    return bounds.max_model_calls, per, total


def attach(guide: Guidance | None, project: Project, bounds: CrawlBounds) -> Guidance | None:
    """Guidance is active only when a guide was passed AND the project opted in AND the bounds
    are on. Anything else is today's behaviour exactly (G5)."""
    opted = project.crawl_guidance is not None and project.crawl_guidance.enabled
    return guide if guide is not None and opted and limits(bounds) is not None else None


def for_project(project: Project) -> Guidance | None:
    """The guide a caller passes to `run_crawl`: None unless the project opted in. The pinned
    chain is built here, lazily, so a crawl with guidance off imports no provider (G5)."""
    if project.crawl_guidance is None or not project.crawl_guidance.enabled:
        return None
    from autotester import providers  # lazy: only an opted-in project reaches a vendor

    provider_id, options = providers.parse_spec(GUIDANCE_SPEC)
    return Guidance(providers.get(provider_id, **options))


def crawl_fields(rt: ExploreRuntime) -> dict[str, Any]:
    """Extra `Crawl` fields for `_finish`: empty unless guidance was active (G5, G8)."""
    return rt.guidance.crawl_fields() if rt.guidance is not None else {}


class Guidance:
    """One crawl's guidance state. Build a fresh one per `run_crawl`."""

    def __init__(self, provider: Provider, *, models: tuple[str, ...] = GUIDANCE_MODELS,
                 skills_dir: Path | None = None) -> None:
        self.provider = provider
        self.models = models
        self._skills = skills_dir or Path(__file__).resolve().parents[1] / "skills"
        self._skill: tuple[str, str] | None = None
        self._kg: PortalPersona | bool | None = False  # False = not loaded yet
        self.calls = self.ok_calls = self.hits = self.strikes = 0
        self.model_s = 0.0
        self.stopped: str | None = None
        self.served: list[str] = []
        self.fallbacks: dict[str, int] = {}
        self._usage0 = self._tokens()

    # -- the one entry point ---------------------------------------------------------------
    def order(self, rt: ExploreRuntime, node: ScreenNode,
              cands: list[ElementRef]) -> list[ElementRef]:
        """`cands` (ordinary, pressable controls) in the model's order; always a permutation."""
        head, tail = cands[:pl.MAX_CANDIDATES], cands[pl.MAX_CANDIDATES:]
        if len(head) < 2:
            return cands
        try:
            got = self._ranked(rt, node, head)
        except Exception as exc:  # G4: a model-side failure never reaches the crawl
            self._fell_back(_reason_for(exc), strike=True)
            got = None
        return [*(pl.reorder(head, got) if got is not None else head), *tail]

    def _ranked(self, rt: ExploreRuntime, node: ScreenNode,
                head: list[ElementRef]) -> list[int] | None:
        body, version = self._load_skill()
        key = pl.candidate_hash(head)
        hit = self._reuse(rt, node, key, version, len(head))
        if hit is not None:
            return hit
        blocked = self._blocked(rt)
        if blocked:
            return self._fell_back(blocked)
        scrub = rt.session.secrets.scrub_optional
        known = [n.url_template for n in rt.nodes.values() if n.id != node.id]
        prompt = pl.render_prompt(body, pl.build_payload(node, head, known, scrub))
        try:
            rt.session.secrets.guard_prompt(prompt)  # assert_no_raw_secrets, before EVERY call
            guard = getattr(self.provider, "guard_text", None)
            if guard is not None:
                guard(prompt)
        except (ValueError, ProviderError):
            return self._fell_back("prompt guard refused (a credential value reached it)")
        raw = self._call(rt, node, prompt)
        usable = pl.parse_ranking(raw, len(head))
        if usable is None:
            return self._fell_back("unparseable, empty or out-of-range answer", strike=True)
        order = pl.complete_order(usable, len(head))
        self.ok_calls, self.strikes = self.ok_calls + 1, 0
        tag = _tag(self.provider)
        self._note_served(tag)
        reason = scrub(_reason_text(raw)) or ""
        self._remember(rt, node, GuidanceAnnotation(
            candidate_hash=key, prompt_version=version, model=tag, ranking=order,
            reason=reason[:REASON_CHARS]))
        return order

    # -- bounded call ----------------------------------------------------------------------
    def _call(self, rt: ExploreRuntime, node: ScreenNode, prompt: str) -> Any:
        """G6: one try plus the provider's one repair, hard-capped; model seconds are read off
        the crawl's own clock so they count toward its wall-clock bound, never beside it."""
        lim = limits(rt.bounds)
        assert lim is not None  # `_blocked` ran first
        cap = min(lim[1], lim[2] - self.model_s)
        started = rt.clock()
        self.calls += 1
        try:
            with attempt_budget(2, wall_clock_s=cap):
                return self.provider.act(prompt, NextActionRanking, prompt_file=SKILL,
                                         fed_id=node.id)
        finally:
            self.model_s += rt.clock() - started

    def _blocked(self, rt: ExploreRuntime) -> str | None:
        lim = limits(rt.bounds)
        if lim is None:
            return "guidance bounds are off"
        reason = None
        if self.strikes >= STRIKES:
            reason = f"circuit breaker open ({STRIKES} consecutive failures)"
        elif self.calls >= lim[0]:
            reason = "max_model_calls reached"
        elif self.model_s >= lim[2]:
            reason = "model_total_s reached"
        if reason:
            self.stopped = self.stopped or reason
            return reason
        return None if self.provider.available() else "model unavailable (no credentials)"

    def _fell_back(self, reason: str, *, strike: bool = False) -> None:
        self.fallbacks[reason] = self.fallbacks.get(reason, 0) + 1
        if strike:
            self.strikes += 1

    # -- prompt ----------------------------------------------------------------------------
    def _load_skill(self) -> tuple[str, str]:
        """(body, version). Raises on a missing or malformed skill (G10); the caller records it."""
        if self._skill is None:
            body = load_skill_prompt(SKILL, skills_dir=self._skills)
            text = (self._skills / SKILL / "SKILL.md").read_text(encoding="utf-8")
            found = re.search(r"^version:\s*(\S+)\s*$", text, re.MULTILINE)
            self._skill = (body, f"{found.group(1) if found else '0'}:{content_hash(body)}")
        return self._skill

    # -- knowledge-graph reuse (G7) --------------------------------------------------------
    def _persona(self, rt: ExploreRuntime) -> PortalPersona | None:
        if self._kg is False:
            try:
                self._kg = rt.store.load_portal_persona() or PortalPersona(project=rt.project.slug)
            except Exception as exc:  # an unreadable graph costs reuse, never the crawl
                self._fell_back(f"knowledge graph unreadable ({type(exc).__name__})")
                self._kg = None
        return self._kg if isinstance(self._kg, PortalPersona) else None

    def _reuse(self, rt: ExploreRuntime, node: ScreenNode, key: str, version: str,
               n: int) -> list[int] | None:
        persona = self._persona(rt)
        stored = persona.graph.node(f"screen:{node.id}") if persona else None
        for note in reversed(stored.guidance or []) if stored else []:
            same = (note.candidate_hash, note.prompt_version) == (key, version)
            if same and note.model in self.models and sorted(note.ranking) == list(range(n)):
                self.hits += 1
                self._note_served(note.model)
                return note.ranking
        return None

    def _remember(self, rt: ExploreRuntime, node: ScreenNode, note: GuidanceAnnotation) -> None:
        persona = self._persona(rt)
        if persona is None:
            return
        stored = persona.graph.node(f"screen:{node.id}")
        if stored is None:
            label = rt.session.secrets.scrub_optional(pl.href_path(node.url_template) or "/")
            stored = GraphNode.make("screen", node.id, label or node.id)
            persona.graph.add_node(stored)
        same = (note.candidate_hash, note.prompt_version, note.model)
        kept = [a for a in stored.guidance or []
                if (a.candidate_hash, a.prompt_version, a.model) != same]
        stored.guidance = [*kept, note][-KEEP_PER_NODE:]
        try:
            rt.store.save_portal_persona(persona)
        except Exception as exc:
            self._fell_back(f"knowledge graph not saved ({type(exc).__name__})")

    # -- record ----------------------------------------------------------------------------
    def _note_served(self, tag: str) -> None:
        if tag not in self.served:
            self.served.append(tag)

    def _tokens(self) -> tuple[int | None, int | None]:
        usage = self.provider.usage
        total_in = (None if any(u.input_tokens is None for u in usage)
                    else sum(u.input_tokens or 0 for u in usage))
        total_out = (None if any(u.output_tokens is None for u in usage)
                     else sum(u.output_tokens or 0 for u in usage))
        return total_in, total_out

    def crawl_fields(self) -> dict[str, Any]:
        """G8: the `Crawl.guidance` summary, and `Crawl.provider` = the model that really served."""
        (in_now, out_now), (in_then, out_then) = self._tokens(), self._usage0
        summary = CrawlGuidance(
            mode="guided" if self.ok_calls + self.hits else "rule-only (model unavailable)",
            models_served=list(self.served), calls=self.calls, kg_hits=self.hits,
            fallbacks=[GuidanceFallback(reason=r, count=c)
                       for r, c in sorted(self.fallbacks.items())],
            model_seconds=round(self.model_s, 3),
            input_tokens=None if in_now is None or in_then is None else in_now - in_then,
            output_tokens=None if out_now is None or out_then is None else out_now - out_then,
            stopped=self.stopped)
        fields: dict[str, Any] = {"guidance": summary}
        if self.served:
            fields["provider"] = ",".join(self.served)
        return fields


def _reason_text(raw: Any) -> str:
    said = raw.get("reason") if isinstance(raw, dict) else getattr(raw, "reason", None)
    return said if isinstance(said, str) else ""


def _tag(provider: Provider) -> str:
    """The exact tag of the model that answered (`served` on a chain), else its label."""
    return (getattr(provider, "served", None) or provider.label).removeprefix("litellm:")


def _reason_for(exc: BaseException) -> str:
    if isinstance(exc, AttemptBudgetExhausted):
        return "timeout or attempt budget exhausted"
    if isinstance(exc, AvailabilityFailure):
        return "model unavailable (availability failure)"
    if isinstance(exc, ProviderError):
        return "model call failed (provider error)"
    if isinstance(exc, (FileNotFoundError, PermissionError)):
        return f"guidance prompt unavailable ({type(exc).__name__})"
    return f"schema or call error ({type(exc).__name__})"
