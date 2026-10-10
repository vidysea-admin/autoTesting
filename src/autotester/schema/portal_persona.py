"""The durable Portal Persona — what AutoTester knows about one product, kept
across runs instead of scoped to a single crawl (T-164, contract portal-persona.md).

One `PortalPersona` model, persisted at `projects/<slug>/portal_persona.json`
via the filestore; `knowledge.md` is a regenerated VIEW of it, never a second
source of truth. Auth is described by field/domain SHAPE only — a `SecretRef`
key, never a value (PP5). `history` is a dated, append-only trail of what each
update changed (PP3). The knowledge graph (T-166, EC1) is this same persona's typed
nodes and edges (`graph`) — JSON on the filestore, no graph database, no second schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autotester.schema.base import Artifact


class PersonaProfile(BaseModel):
    """What the product is, at a glance — the durable header of the persona."""

    model_config = ConfigDict(extra="forbid")

    name: str = ""
    base_url: str = ""
    overview: str | None = Field(
        default=None, description="the product's own summary, from a reviewed FlowSpec"
    )


class AuthField(BaseModel):
    """One credential input the login SHAPE has. Carries the SecretRef KEY, never
    a value (PP5) — the value lives only in the repo-root `.env` (C5)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str = "text"
    secret_key: str | None = Field(
        default=None, description="the declared SecretRef key (e.g. DEMO_PASSWORD), never a value"
    )


class AuthShape(BaseModel):
    """How the product authenticates, described by shape alone (PP5): which
    screen, which fields, which domains a credential is scoped to. No values."""

    model_config = ConfigDict(extra="forbid")

    required: bool = False
    login_screen: str | None = None
    fields: list[AuthField] = Field(default_factory=list)
    domains: list[str] = Field(
        default_factory=list, description="hosts a credential is scoped to (from SecretRef.domains)"
    )


class PersonaScreen(BaseModel):
    """One distinct screen the product has. Accumulated across runs (PP2)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    url_template: str | None = None
    signature: str | None = Field(
        default=None, description="structural signature when a crawl supplied one"
    )
    purpose: str | None = None
    controls: list[str] = Field(default_factory=list, description="named interactive controls")
    screenshot_ref: str | None = Field(
        default=None, description="a MASKED screenshot (PP5); secret inputs are masked at capture"
    )

    def key(self) -> str:
        """Cross-run identity: the templated URL when known, else the folded name.
        Two runs naming the same screen must land on one entry (PP2).

        Deliberately signature-free, and it must stay so: CR4's `changed` is
        defined as *the same key with a different signature*, so folding the
        signature in here would turn every edited screen into a new screen and
        destroy change tracking. `ident()` is what distinguishes two screens
        that merely share a URL."""
        return self.url_template or " ".join(self.name.casefold().split())

    def ident(self) -> tuple[str, str | None]:
        """Distinct-SCREEN identity: the cross-run `key()` plus the structural
        signature (`ISS-t165-crawl-traversal-2`).

        `key()` alone is `url_template`-only, so two structurally distinct
        screens sharing a URL — an SPA state toggle, the shape X3/X14 document
        as real — collided onto one entry and the second was dropped before it
        was ever stored or classified. Storage dedupes on this; the diff still
        groups by `key()`, because that is what `changed` compares within."""
        return (self.key(), self.signature)


class PersonaTransition(BaseModel):
    """One learned move between screens — what control takes you where."""

    model_config = ConfigDict(extra="forbid")

    from_screen: str
    to_screen: str | None = None
    action: str = "click"
    control: str = ""

    def key(self) -> str:
        return f"{self.from_screen}|{self.action}|{self.control}|{self.to_screen or ''}"


class FlowRunRef(BaseModel):
    """A stable, runnable reference a Quick Re-Run resolves to re-exercise a
    taught flow without re-teaching it (PP6): the project, the flow id, and the
    screen the flow enters at."""

    model_config = ConfigDict(extra="forbid")

    project: str
    flow_id: str
    entry_screen: str


class TaughtFlow(BaseModel):
    """An end-to-end journey the product supports, carried durably with a stable
    runnable reference (PP6)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    entry_screen: str
    exit_screen: str | None = None
    requires_auth: bool = False
    run_ref: FlowRunRef


class Gotcha(BaseModel):
    """One thing that bit us — a quirk of this product worth remembering."""

    model_config = ConfigDict(extra="forbid")

    note: str
    screen: str | None = None

    def key(self) -> str:
        return f"{self.screen or ''}|{self.note}"


class PersonaRevision(BaseModel):
    """One dated entry in the persona's history: when it was updated and a
    non-empty summary naming what changed (PP3).

    CR4 adds the four change-tracking categories as MACHINE-CHECKABLE counts plus
    the keys behind each, rather than only the prose `summary` PP3 already had: a
    sentence cannot be diffed, and T-168 needs to read what moved. `missing_unjudged`
    is the honesty field — a bound-truncated frontier cannot tell a genuinely absent
    screen from one it simply never reached (CR5), so those are counted here and
    NEVER as `missing`."""

    model_config = ConfigDict(extra="forbid")

    at: str = Field(description="ISO-8601 UTC timestamp of the update")
    summary: str = Field(description="what this update changed — never blank (PP3)")
    new_screens: list[str] = Field(default_factory=list, description="CR4: keys first seen")
    changed_screens: list[str] = Field(
        default_factory=list, description="CR4: keys whose live signature differs from the stored")
    missing_screens: list[str] = Field(
        default_factory=list, description="CR4: stored keys an EXHAUSTED frontier did not reach")
    broken_screens: list[str] = Field(
        default_factory=list, description="CR4: keys reached with an error/off-domain status")
    missing_unjudged: list[str] = Field(
        default_factory=list,
        description="CR5: stored keys not reached by a BOUND-TRUNCATED crawl — unknown, never "
                    "reported as missing. A non-empty list means this diff is incomplete.")
    healthy_screens: list[str] = Field(
        default_factory=list,
        description="NOT a sixth CR4 category and NOT in `counts()` — provenance: keys a PRIOR "
                    "revision recorded broken that this crawl VISITED and found not broken. "
                    "Without it, 'the prior stored status' cannot distinguish 'never re-observed' "
                    "from 'observed healthy', so a screen that broke, healed, then relapsed could "
                    "never be reported broken again (ISS-t165-crawl-traversal-4). A skipped node "
                    "is not an observation and never lands here. Defaulted, so personas written "
                    "before this field still load.")

    def counts(self) -> dict[str, int]:
        """CR4: the count per named category — what a surface renders and a test asserts."""
        return {"new": len(self.new_screens), "changed": len(self.changed_screens),
                "missing": len(self.missing_screens), "broken": len(self.broken_screens),
                "missing_unjudged": len(self.missing_unjudged)}

    @field_validator("summary")
    @classmethod
    def _reject_blank_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("a revision must name what changed; summary may not be blank")
        return value


NodeKind = Literal["screen", "control", "flow", "scenario", "case", "verdict", "api", "release"]
EdgeKind = Literal["has_control", "leads_to", "visits", "calls", "variant_of", "traces_to",
                   "targets", "verdict_of"]


class GraphNode(BaseModel):
    """One typed node of the knowledge graph (EC1). `id` is `<kind>:<ref>`."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: NodeKind
    label: str = ""

    @classmethod
    def make(cls, kind: NodeKind, ref: str, label: str = "") -> GraphNode:
        return cls(id=f"{kind}:{ref}", kind=kind, label=label or ref)


class GraphEdge(BaseModel):
    """One typed edge `src -> dst`; `label` tells parallel edges apart (e.g. the control)."""

    model_config = ConfigDict(extra="forbid")

    kind: EdgeKind
    src: str
    dst: str
    label: str = ""


class KnowledgeGraph(BaseModel):
    """Screen, control, flow, scenario, case, verdict, API and release nodes with typed
    edges between them (D-041). Every edge endpoint is a node: a dangling edge is refused."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _edges_resolve(self) -> KnowledgeGraph:
        ids = [n.id for n in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate node id in knowledge graph")
        missing = {end for e in self.edges for end in (e.src, e.dst)} - set(ids)
        if missing:
            raise ValueError(f"edge endpoint is not a node: {sorted(missing)}")
        return self

    def node(self, node_id: str) -> GraphNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def add_node(self, node: GraphNode) -> None:
        if self.node(node.id) is None:
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        for end in (edge.src, edge.dst):
            if self.node(end) is None:
                raise ValueError(f"edge endpoint is not a node: {end}")
        if edge not in self.edges:
            self.edges.append(edge)

    def out(self, node_id: str, kind: EdgeKind | None = None) -> list[GraphNode]:
        ends = [e.dst for e in self.edges if e.src == node_id and kind in (None, e.kind)]
        return [n for n in (self.node(i) for i in ends) if n is not None]


class PortalPersona(Artifact):
    """The durable, cross-run model of one product under test (PP1). A single
    artifact — `knowledge.md` is a regenerated view of it, not a second store."""

    project: str
    profile: PersonaProfile = Field(default_factory=PersonaProfile)
    auth: AuthShape = Field(default_factory=AuthShape)
    screens: list[PersonaScreen] = Field(default_factory=list)
    transitions: list[PersonaTransition] = Field(default_factory=list)
    taught_flows: list[TaughtFlow] = Field(default_factory=list)
    gotchas: list[Gotcha] = Field(default_factory=list)
    screenshot_refs: list[str] = Field(default_factory=list)
    history: list[PersonaRevision] = Field(default_factory=list)
    graph: KnowledgeGraph = Field(default_factory=KnowledgeGraph)

    def screen(self, screen_id: str) -> PersonaScreen | None:
        return next((s for s in self.screens if s.id == screen_id), None)

    def taught_flow(self, flow_id: str) -> TaughtFlow | None:
        return next((f for f in self.taught_flows if f.id == flow_id), None)

    def resolve_run(self, ref: FlowRunRef) -> TaughtFlow | None:
        """Resolve a Quick Re-Run reference back to the flow it names (PP6).
        A reference the persona cannot resolve is not runnable, and returns None."""
        if ref.project != self.project:
            return None
        flow = self.taught_flow(ref.flow_id)
        if flow is None or flow.entry_screen != ref.entry_screen:
            return None
        return flow
