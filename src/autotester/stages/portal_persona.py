"""PORTAL PERSONA: promote per-crawl knowledge into the durable, cross-run
product model (T-164, contract portal-persona.md).

`build_portal_persona` reads a crawl's screen graph and the reviewed FlowSpec, MERGES them into the
existing `projects/<slug>/portal_persona.json` (never dropping or blanking a known screen/flow —
PP2), records a dated `PersonaRevision` when and only when something changed (PP3), and regenerates
`knowledge.md` as a view of the JSON (PP4). The persona is the single store; `knowledge.md` is never
a second source of truth (PP1). It alone grafts guidance (D-119).

Credentials never enter it: auth is carried by SHAPE only (a `SecretRef` key,
never a value), every free-text field is scrubbed through the project
`Redactor`, and nothing is persisted while a raw secret value survives —
the `assert_no_raw_secrets` invariant, applied before any write (PP5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from autotester.core.redact import Redactor
from autotester.schema.base import utc_now
from autotester.schema.enums import CrawlStatus, EdgeOutcome, IssueKind
from autotester.schema.portal_persona import (
    AuthField,
    AuthShape,
    FlowRunRef,
    Gotcha,
    PersonaProfile,
    PersonaRevision,
    PersonaScreen,
    PersonaTransition,
    PortalPersona,
    TaughtFlow,
)
from autotester.stages import explore_guidance, persona_changes
from autotester.store.filestore import write_text

if TYPE_CHECKING:  # a stage names the store only in a signature (execute.py's convention)
    from autotester.schema.crawl import CrawlIssue
    from autotester.schema.flowspec import FlowSpec, Screen
    from autotester.schema.project import Project
    from autotester.schema.screen_graph import ScreenEdge, ScreenNode
    from autotester.store.project_store import ProjectStore

_SECRETISH_TYPES = ("password", "email")


def _now() -> str:
    return utc_now().isoformat()


def _union(existing: list[str], incoming: list[str]) -> list[str]:
    out = list(existing)
    for value in incoming:
        if value not in out:
            out.append(value)
    return out


def _add_new(existing: list, incoming: list, key: Callable) -> tuple[list, list]:
    """Keep every existing entry; append only genuinely new ones (PP2)."""
    seen = {key(x) for x in existing}
    added = [x for x in incoming if key(x) not in seen]
    return [*existing, *added], added


def _screen_from_flowspec(screen: Screen) -> PersonaScreen:
    return PersonaScreen(
        id=screen.id, name=screen.name, url_template=screen.url_pattern,
        controls=[f.name for f in screen.fields], screenshot_ref=screen.screenshot_ref,
    )


def _screen_from_node(node: ScreenNode) -> PersonaScreen:
    return PersonaScreen(
        id=node.id, name=node.name or node.title or node.url_template,
        url_template=node.url_template, signature=node.signature,
        controls=[e.name for e in node.elements if e.name], screenshot_ref=node.screenshot_ref,
    )


def _incoming_screens(flowspec: FlowSpec | None, nodes: list[ScreenNode]) -> list[PersonaScreen]:
    """Every distinct screen this update contributes, deduped on
    `PersonaScreen.ident()` — key AND signature — not `key()` alone
    (`ISS-t165-crawl-traversal-2`): two crawled nodes at one `url_template` with
    different signatures are two screens, and the second used to be dropped here
    before the merge or the CR4 diff saw it. Add-only either way (PP2)."""
    screens = [_screen_from_flowspec(s) for s in (flowspec.screens if flowspec else [])]
    seen = {s.ident() for s in screens}
    for node in nodes:
        persona_screen = _screen_from_node(node)
        if persona_screen.ident() not in seen:
            screens.append(persona_screen)
            seen.add(persona_screen.ident())
    return screens


def _incoming_transitions(
    edges: list[ScreenEdge], name_by_node: dict[str, str]
) -> list[PersonaTransition]:
    out: list[PersonaTransition] = []
    for edge in edges:
        if edge.outcome is not EdgeOutcome.NAVIGATED or not edge.to_node:
            continue
        out.append(PersonaTransition(
            from_screen=name_by_node.get(edge.from_node, edge.from_node),
            to_screen=name_by_node.get(edge.to_node, edge.to_node),
            action=edge.action.value, control=edge.name or edge.target,
        ))
    return out


def _incoming_flows(slug: str, flowspec: FlowSpec | None) -> list[TaughtFlow]:
    return [
        TaughtFlow(
            id=flow.id, name=flow.name, entry_screen=flow.entry_screen,
            exit_screen=flow.exit_screen, requires_auth=flow.requires_auth,
            run_ref=FlowRunRef(project=slug, flow_id=flow.id, entry_screen=flow.entry_screen),
        )
        for flow in (flowspec.flows if flowspec else [])
    ]


def _incoming_auth(project: Project | None, flowspec: FlowSpec | None) -> AuthShape:
    fields: list[AuthField] = []
    login_screen: str | None = None
    for screen in (flowspec.screens if flowspec else []):
        secretish = [f for f in screen.fields if f.secret_key or f.type in _SECRETISH_TYPES]
        if secretish and login_screen is None:
            login_screen = screen.name
        fields += [AuthField(name=f.name, type=f.type, secret_key=f.secret_key) for f in secretish]
    required = bool(project and project.login_case_id) or any(
        f.requires_auth for f in (flowspec.flows if flowspec else [])
    )
    domains = sorted({d for sec in (project.secrets if project else []) for d in sec.domains})
    return AuthShape(required=required or bool(fields), login_screen=login_screen,
                     fields=fields, domains=domains)


def _incoming_gotchas(issues: list[CrawlIssue], name_by_node: dict[str, str]) -> list[Gotcha]:
    return [
        Gotcha(screen=name_by_node.get(issue.node_id, issue.node_id),
               note=f"{issue.kind.value}: {issue.detail}")
        for issue in issues if issue.kind is not IssueKind.EVIDENCE
    ]


def _build_incoming(store: ProjectStore, project: Project | None,
                    crawl_id: str | None) -> PortalPersona:
    flowspec = store.load_flowspec()
    nodes = store.list_nodes(crawl_id) if crawl_id else []
    edges = store.list_edges(crawl_id) if crawl_id else []
    issues = store.list_crawl_issues(crawl_id) if crawl_id else []
    name_by_node = {n.id: (n.name or n.title or n.url_template) for n in nodes}
    screens = _incoming_screens(flowspec, nodes)
    slug = store.paths.slug
    return PortalPersona(
        project=slug,
        profile=PersonaProfile(
            name=(project.name if project else slug),
            base_url=(project.base_url if project else ""),
            overview=(flowspec.app_overview if flowspec else None)),
        auth=_incoming_auth(project, flowspec),
        screens=screens,
        transitions=_incoming_transitions(edges, name_by_node),
        taught_flows=_incoming_flows(slug, flowspec),
        gotchas=_incoming_gotchas(issues, name_by_node),
        screenshot_refs=[s.screenshot_ref for s in screens if s.screenshot_ref],
    )


def _initial_summary(persona: PortalPersona) -> str:
    return (f"initial persona: {len(persona.screens)} screen(s), "
            f"{len(persona.taught_flows)} flow(s), {len(persona.transitions)} transition(s)")


def _summary(new_screens: list, new_flows: list, new_trans: list, new_gotchas: list,
             new_shots: int, auth_changed: bool, overview_changed: bool) -> str | None:
    """Name what changed, or None when nothing did — the gate on appending a
    revision (PP3): an identical re-run must not fabricate one."""
    parts: list[str] = []
    if new_screens:
        parts.append(f"{len(new_screens)} screen(s): " + ", ".join(s.name for s in new_screens))
    if new_flows:
        parts.append(f"{len(new_flows)} flow(s): " + ", ".join(f.name for f in new_flows))
    if new_trans:
        parts.append(f"{len(new_trans)} transition(s)")
    if new_gotchas:
        parts.append(f"{len(new_gotchas)} gotcha(s)")
    if new_shots > 0:
        parts.append(f"{new_shots} screenshot(s)")
    if auth_changed:
        parts.append("auth shape")
    if overview_changed:
        parts.append("overview")
    return "added " + "; ".join(parts) if parts else None


def _merge_auth(existing: AuthShape, incoming: AuthShape) -> tuple[AuthShape, bool]:
    fields, new = _add_new(existing.fields, incoming.fields, key=lambda f: f.name)
    domains = _union(existing.domains, incoming.domains)
    required = existing.required or incoming.required
    login = existing.login_screen or incoming.login_screen
    changed = bool(new) or domains != existing.domains \
        or required != existing.required or login != existing.login_screen
    return AuthShape(required=required, login_screen=login, fields=fields, domains=domains), changed


def _merge(existing: PortalPersona | None,
           incoming: PortalPersona) -> tuple[PortalPersona, str | None]:
    """Fold `incoming` into `existing`, never rewriting known knowledge (PP2)."""
    if existing is None:
        return incoming, _initial_summary(incoming)
    # `ident()`, not `key()` (ISS-2): a 2nd distinct screen at a known URL is a
    # screen, not a duplicate -- see `PersonaScreen.ident`. Still add-only.
    screens, s_new = _add_new(existing.screens, incoming.screens, key=lambda s: s.ident())
    trans, t_new = _add_new(existing.transitions, incoming.transitions, key=lambda t: t.key())
    flows, f_new = _add_new(existing.taught_flows, incoming.taught_flows, key=lambda f: f.id)
    gotchas, g_new = _add_new(existing.gotchas, incoming.gotchas, key=lambda g: g.key())
    shots = _union(existing.screenshot_refs, incoming.screenshot_refs)
    auth, auth_changed = _merge_auth(existing.auth, incoming.auth)
    overview = existing.profile.overview or incoming.profile.overview
    overview_changed = overview != existing.profile.overview
    merged = existing.model_copy(update={
        "profile": existing.profile.model_copy(update={"overview": overview}),
        "auth": auth, "screens": screens, "transitions": trans,
        "taught_flows": flows, "gotchas": gotchas, "screenshot_refs": shots})
    summary = _summary(s_new, f_new, t_new, g_new,
                       len(shots) - len(existing.screenshot_refs), auth_changed, overview_changed)
    return merged, summary


def _scrub_persona(persona: PortalPersona, redactor: Redactor) -> PortalPersona:
    """Mask every known secret value out of every string in the persona (PP5)."""
    return PortalPersona.model_validate(redactor.scrub_obj(persona.model_dump(mode="json")))


def _guard_clean(redactor: Redactor | None, *texts: str) -> None:
    """The `assert_no_raw_secrets` gate applied to persona content before any
    write: refuse to persist while a raw secret value survives (PP5)."""
    if redactor is None:
        return
    if not all(redactor.is_clean(text) for text in texts):
        raise ValueError("refusing to persist portal persona: raw secret value present")


def _persist(store: ProjectStore, persona: PortalPersona,
             redactor: Redactor | None) -> PortalPersona:
    if redactor is not None:
        persona = _scrub_persona(persona, redactor)
    from autotester.stages.portal_persona_view import render_knowledge

    knowledge = render_knowledge(persona)
    _guard_clean(redactor, persona.model_dump_json(exclude_none=True), knowledge)
    store.save_portal_persona(persona)
    write_text(store.paths.knowledge, knowledge)
    return persona


def _frontier_exhausted(store: ProjectStore, crawl_id: str | None) -> bool:
    """CR5: may this crawl's evidence support a `missing` claim at all?

    Only a crawl that really drained its frontier can say a stored screen is
    gone. `COMPLETED` is exactly that judgement, already made by
    `explore_status.terminal_status` — every other status (a fired bound, a
    login wall, an abort) means the crawl never saw the whole product, so
    `persona_changes` records the absences as unjudged instead."""
    if crawl_id is None:
        return False
    crawl = store.load_crawl(crawl_id)
    return crawl is not None and crawl.status is CrawlStatus.COMPLETED


def build_portal_persona(
    store: ProjectStore, *, crawl_id: str | None = None, redactor: Redactor | None = None
) -> PortalPersona:
    """Build or update the durable persona from the crawl graph + reviewed
    FlowSpec, persist it, and regenerate `knowledge.md` (PP1-PP6).

    CR4: the merge itself stays PP2 add-only — nothing existing is dropped,
    blanked or rewritten. What is new is that the dated revision now also
    carries the machine-checkable new/changed/missing/broken classification, so
    a screen that DISAPPEARED is recorded even though an add-only merge has, by
    construction, nothing to add for it."""
    project = store.load_project()
    incoming = _build_incoming(store, project, crawl_id)
    existing = store.load_portal_persona()
    persona, summary = _merge(existing, incoming)
    persona = explore_guidance.graft(persona, store.list_nodes(crawl_id) if crawl_id else [])
    diff = persona_changes.classify(
        existing, store.list_nodes(crawl_id) if crawl_id else [],
        frontier_exhausted=_frontier_exhausted(store, crawl_id))
    note = persona_changes.describe(diff)
    summary = "; ".join(part for part in (summary, note) if part)
    if summary:
        persona = persona.model_copy(update={
            "history": [*persona.history,
                        PersonaRevision(at=_now(), summary=summary, **diff)]})
    return _persist(store, persona, redactor)
