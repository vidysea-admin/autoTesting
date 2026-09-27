"""Fold a crawl's screen graph into the reviewed FlowSpec (Track B5).

The crawl discovers screens the FlowSpec has never heard of. This stage is the
one place those become `Screen` rows a human can review — and it is deliberately
conservative: an existing screen is never rewritten, a disagreement becomes a
`Conflict` with both claims kept, and any real change sends the spec back to
DRAFT so the human gate is re-armed rather than bypassed.

Contract: qa/contracts/explore.md X12 amendment + qa/contracts/coverage.md V1.
"""

from __future__ import annotations

from autotester.core.urls import url_template
from autotester.schema.enums import ReviewStatus
from autotester.schema.flowspec import Conflict, FlowSpec, InputField, Review, Screen, SourceRef
from autotester.schema.screen_graph import ScreenNode

_FIELD_ROLES = {
    "textbox": "text", "searchbox": "text", "combobox": "select",
    "checkbox": "checkbox", "radio": "radio", "spinbutton": "number",
}
_MAX_SIGNALS = 8

# `ScreenNode.model_post_init` builds its id with `content_id("node", ...)`, so a
# Screen carrying a node id is one the crawler identified STRUCTURALLY. Pinned by
# `test_a_real_screen_node_id_carries_the_structural_prefix`.
_STRUCTURAL_ID_PREFIX = "node_"


def _is_structural(screen: Screen) -> bool:
    """Whether this screen's identity came from a structural signature rather
    than from a human or an ingested video merely claiming a URL."""
    return screen.id.startswith(_STRUCTURAL_ID_PREFIX)


def _signals(node: ScreenNode) -> list[str]:
    """The screen's identifying cues: its title plus the names of its stable
    (non-row) controls. Row content is excluded for the same reason it is
    excluded from the structural signature — it is data, not identity."""
    names = [el.name for el in node.elements if el.visible and el.name and not el.in_row]
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return ([node.title] if node.title else []) + seen[:_MAX_SIGNALS]


def _fields(node: ScreenNode) -> list[InputField]:
    """Inputs the crawl saw. `secret_key` is deliberately never inferred — a
    field is only a secret because a human declared a `SecretRef` for it."""
    fields: list[InputField] = []
    for el in node.elements:
        kind = _FIELD_ROLES.get(el.role)
        if kind is None or not el.visible:
            continue
        fields.append(InputField(name=el.name or el.selector, label=el.name or None, type=kind))
    return fields


def screen_from(node: ScreenNode) -> Screen:
    """One crawled node as a FlowSpec `Screen`, keeping the node's own id so a
    re-merge of the same crawl is a no-op rather than a duplicate.

    `url_pattern` is derived host-lessly from `url_example` rather than reused
    from `node.url_template`: the node template carries a host (it is a browsing
    identity), while a `Screen.url_pattern` is a path pattern — that is what
    `stages/coverage.py` and `stages/ingest.py` both compare against.

    `fold_index=True` (AT-618): `node.id` was already built from a folded
    `url_template` (`screen_identity.node_from`) — deriving `url_pattern`
    unfolded here would let a merged Screen disagree with the very node it came
    from, exactly the coverage.md V1 seam AT-618 found open.
    """
    return Screen(
        id=node.id,
        name=node.name or node.title or node.url_template,
        url_pattern=url_template(node.url_example, keep_host=False, fold_index=True),
        signals=_signals(node),
        fields=_fields(node),
        screenshot_ref=node.screenshot_ref,
        source_ref=SourceRef(source_id=node.crawl_id, locator=node.url_example),
    )


def _conflict_for(existing: Screen, incoming: Screen, source_id: str) -> Conflict:
    return Conflict(
        subject=incoming.url_pattern or incoming.id,
        claims=[
            f"existing screen '{existing.name}' ({existing.id})",
            f"crawled screen '{incoming.name}' ({incoming.id})",
        ],
        source_refs=[
            existing.source_ref or SourceRef(source_id="unknown"),
            SourceRef(source_id=source_id, locator=incoming.url_pattern),
        ],
    )


def disagreement(clash: Screen | None, incoming: Screen, source_id: str) -> Conflict | None:
    """Whether an existing screen at the same `url_pattern` actually disagrees.

    **A conflict means two SOURCES disagree, not that two patterns collide**
    (AT-103). Two screens that both carry a structural identity are, by
    definition, structurally different screens at one URL — an SPA, which X3
    requires to be two screens — so they never conflict with each other however
    many crawls found them. Only a claim with NO structural identity (a human's
    or an ingested video's screen, which asserts a URL and nothing more) can be
    contradicted by a crawl.

    Scoping this to one crawl instead of to identity is what made a project that
    pressed "Explore again" accumulate a false conflict per SPA state on every
    re-crawl.
    """
    if clash is None or clash.name == incoming.name or _is_structural(clash):
        return None
    return _conflict_for(clash, incoming, source_id)


def _is_rediscovery(clash: Screen | None, incoming: Screen) -> bool:
    """AT-102: a non-structural screen re-discovered at the SAME pattern under
    the SAME name is not a new screen and not a disagreement either — it is
    the crawl finding what the spec already knows, under a fresh node id.
    Recording it as an addition gave the spec two identically-named screens
    on one pattern with nothing (no conflict) explaining why."""
    return clash is not None and clash.name == incoming.name and not _is_structural(clash)


def merge_screens(
    spec: FlowSpec | None, nodes: list[ScreenNode], project: str, *, crawl_id: str
) -> FlowSpec:
    """Add every crawled screen the spec does not already have.

    Never rewrites an existing screen. When a crawled screen claims a
    `url_pattern` an existing screen already claims under a different name, both
    are kept and a `Conflict` records the disagreement for the human — silently
    picking a winner is how a product map stops matching the product.

    See `disagreement` for when a shared `url_pattern` is a conflict and when
    it is simply an SPA, and `_is_rediscovery` for when it is neither.

    Idempotent: merging the same crawl twice changes nothing, so the version is
    not bumped and the review is not reset a second time.
    """
    spec = spec or FlowSpec(project=project)
    known_ids = {s.id for s in spec.screens}
    by_pattern = {s.url_pattern: s for s in spec.screens if s.url_pattern}

    added: list[Screen] = []
    conflicts: list[Conflict] = []
    for node in nodes:
        incoming = screen_from(node)
        if incoming.id in known_ids:
            continue
        clash = by_pattern.get(incoming.url_pattern)
        if _is_rediscovery(clash, incoming):
            continue
        conflict = disagreement(clash, incoming, crawl_id)
        if conflict is not None:
            conflicts.append(conflict)
        added.append(incoming)
        known_ids.add(incoming.id)

    if not added:
        return spec

    known_conflicts = {(c.subject, tuple(c.claims)) for c in spec.conflicts}
    new_conflicts = [c for c in conflicts if (c.subject, tuple(c.claims)) not in known_conflicts]
    return spec.model_copy(update={
        "screens": [*spec.screens, *added],
        "conflicts": [*spec.conflicts, *new_conflicts],
        "source_ids": sorted({*spec.source_ids, crawl_id}),
        "version": spec.version + 1,
        "review": Review(
            status=ReviewStatus.DRAFT,
            note=f"{len(added)} screen(s) added by crawl {crawl_id} — needs review",
        ),
    })
