"""CR4 — new / changed / missing / broken, and CR5's honesty interaction.

Contract: qa/contracts/crawl-traversal.md CR4. `portal_persona.md` PP1-PP6 are
unamended: `_merge` is still add-only, nothing existing is dropped, blanked or
rewritten, and this unit only adds a CLASSIFICATION recorded on the dated
`PersonaRevision` (PP3) beside the prose summary PP3 already required.

The sharpest test here is the one that does NOT report a finding: a crawl
stopped by a bound never saw the whole frontier, so it may not call a screen
`missing`. Turning "we ran out of budget" into "the product lost a screen" is
the exact dishonesty CR5 exists to prevent.
"""

from __future__ import annotations

import pytest

from autotester.schema.enums import NodeStatus
from autotester.schema.portal_persona import (
    PersonaRevision,
    PersonaScreen,
    PortalPersona,
)
from autotester.schema.screen_graph import ScreenNode
from autotester.stages import persona_changes


def _node(template: str, signature: str, *, status: NodeStatus = NodeStatus.EXPLORED,
          name: str = "") -> ScreenNode:
    return ScreenNode(crawl_id="c", project="p", url_template=template, url_example=template,
                      signature=signature, name=name or template, status=status)


def _persona(*screens: tuple[str, str], history: list[PersonaRevision] | None = None
             ) -> PortalPersona:
    return PortalPersona(
        project="p",
        screens=[PersonaScreen(id=f"s{i}", name=t, url_template=t, signature=sig)
                 for i, (t, sig) in enumerate(screens)],
        history=history or [],
    )


def _classify(existing, nodes, *, exhausted: bool = True) -> dict[str, list[str]]:
    return persona_changes.classify(existing, nodes, frontier_exhausted=exhausted)


# --- the four categories ----------------------------------------------------


def test_a_screen_absent_from_the_stored_persona_is_new() -> None:
    diff = _classify(_persona(("/a", "sig-a")), [_node("/a", "sig-a"), _node("/b", "sig-b")])
    assert diff["new_screens"] == ["/b"]
    assert diff["changed_screens"] == []


def test_a_screen_whose_live_signature_differs_is_changed_and_is_named() -> None:
    """CR4's acceptance test (c), second half: a screen whose structure was
    edited between crawls produces exactly ONE `changed` entry, NAMING it."""
    diff = _classify(_persona(("/a", "sig-a"), ("/b", "sig-b")),
                     [_node("/a", "sig-a"), _node("/b", "sig-b-EDITED")])
    assert diff["changed_screens"] == ["/b"]
    assert diff["new_screens"] == []


def test_removing_a_screen_produces_exactly_one_missing_on_an_exhausted_frontier() -> None:
    """CR4's acceptance test (c), first half."""
    diff = _classify(_persona(("/a", "sig-a"), ("/gone", "sig-gone")), [_node("/a", "sig-a")])
    assert diff["missing_screens"] == ["/gone"]
    assert diff["missing_unjudged"] == []


def test_removing_nothing_produces_zero_missing() -> None:
    """CR4's acceptance test (c): the same two crawls with nothing removed
    produce ZERO `missing` entries — the control arm, without which the test
    above passes on a function that always reports everything missing."""
    diff = _classify(_persona(("/a", "sig-a"), ("/b", "sig-b")),
                     [_node("/a", "sig-a"), _node("/b", "sig-b")])
    assert diff["missing_screens"] == []
    assert diff["changed_screens"] == []
    assert diff["new_screens"] == []


def test_a_screen_reached_with_an_error_status_is_broken() -> None:
    diff = _classify(_persona(("/a", "sig-a")),
                     [_node("/a", "sig-a", status=NodeStatus.ABORTED_ERROR)])
    assert diff["broken_screens"] == ["/a"]


def test_a_screen_already_recorded_broken_is_not_re_reported() -> None:
    """CR4: `broken` means an error status *that the prior stored screen did not
    carry*. PP2 forbids rewriting a stored screen, so the prior state is read
    from the append-only revision history instead."""
    prior = PersonaRevision(at="2026-09-01T00:00:00", summary="screens 1 broken",
                            broken_screens=["/a"])
    diff = _classify(_persona(("/a", "sig-a"), history=[prior]),
                     [_node("/a", "sig-a", status=NodeStatus.ABORTED_ERROR)])
    assert diff["broken_screens"] == []


def test_a_screen_broken_across_an_unrelated_intervening_revision_is_not_re_reported() -> None:
    """ISS-t165-crawl-traversal-4: `_previously_broken` read only the most
    recent revision that classified ANYTHING. A screen broken in revision 1 and
    still broken now was re-flagged as newly broken whenever revision 2 recorded
    something unrelated, because revision 2's own `broken_screens` was empty.
    The history is append-only, so broken-ever is the union over all of it."""
    history = [
        PersonaRevision(at="2026-09-01T00:00:00", summary="1 broken", broken_screens=["/a"]),
        PersonaRevision(at="2026-09-02T00:00:00", summary="1 new", new_screens=["/b"]),
    ]
    diff = _classify(_persona(("/a", "sig-a"), ("/b", "sig-b"), history=history),
                     [_node("/a", "sig-a", status=NodeStatus.ABORTED_ERROR),
                      _node("/b", "sig-b")])
    assert diff["broken_screens"] == []


def test_a_screen_that_healed_and_then_relapsed_is_reported_broken_again() -> None:
    """The other half of ISS-t165-crawl-traversal-4, and the review finding the
    first cycle-2 attempt earned: a PLAIN union over the history can never
    un-remember, so a screen that broke, was observed HEALTHY, then genuinely
    relapsed would be silently suppressed forever. The issue's `expected` asks
    for the union minus any later revision that observed the screen not-broken,
    so `healthy_screens` (recorded by `classify` on the healing crawl) subtracts."""
    heal = _classify(_persona(("/a", "sig-a"), history=[
        PersonaRevision(at="2026-09-01T00:00:00", summary="1 broken", broken_screens=["/a"])]),
        [_node("/a", "sig-a")])
    assert heal["healthy_screens"] == ["/a"], "the healing crawl did not record the observation"
    assert heal["broken_screens"] == []

    history = [
        PersonaRevision(at="2026-09-01T00:00:00", summary="1 broken", broken_screens=["/a"]),
        PersonaRevision(at="2026-09-02T00:00:00", summary="1 recovered",
                        healthy_screens=heal["healthy_screens"]),
    ]
    relapse = _classify(_persona(("/a", "sig-a"), history=history),
                        [_node("/a", "sig-a", status=NodeStatus.ABORTED_ERROR)])
    assert relapse["broken_screens"] == ["/a"], (
        "a genuine relapse after an observed recovery was suppressed")


def test_a_skipped_screen_is_not_an_observation_of_health() -> None:
    """A CR3 skip never visited the screen, so it may not clear a broken record
    any more than it may support a `missing` claim (`_judged_exhausted`)."""
    diff = _classify(_persona(("/a", "sig-a"), history=[
        PersonaRevision(at="2026-09-01T00:00:00", summary="1 broken", broken_screens=["/a"])]),
        [_node("/a", "sig-a", status=NodeStatus.SKIPPED_UNCHANGED)])
    assert diff["healthy_screens"] == []


# --- ISS-2: two distinct screens that merely share a URL ---------------------


def test_a_second_screen_at_a_known_url_is_classified_not_silently_dropped() -> None:
    """ISS-t165-crawl-traversal-2: `PersonaScreen.key()` is `url_template`-only,
    so an SPA state toggle (X3/X14's documented shape) puts two structurally
    distinct screens on one key. `_reached` kept the FIRST and the second was
    invisible to every category — not miscategorized, never considered. The key
    now carries every node reached at it, so a new state at a known URL reads as
    `changed` rather than as nothing at all."""
    diff = _classify(_persona(("/", "sig-base")),
                     [_node("/", "sig-base"), _node("/", "sig-panel-open")])
    assert diff["changed_screens"] == ["/"]
    assert diff["missing_screens"] == []


def test_a_broken_second_state_at_a_known_url_is_still_reported_broken() -> None:
    """The same collision on the `broken` category: the healthy state was first
    in crawl order, so first-wins hid the state that actually errored."""
    diff = _classify(_persona(("/", "sig-base")),
                     [_node("/", "sig-base"),
                      _node("/", "sig-modal", status=NodeStatus.ABORTED_ERROR)])
    assert diff["broken_screens"] == ["/"]


def test_a_persona_written_before_this_unit_still_loads_and_classifies() -> None:
    """The ISS-2 fix adds `PersonaScreen.ident()` — a METHOD, not a field — so
    nothing stored changes shape. A persona file written before T-165 (no
    revision categories, no signature on some screens) must still validate and
    still diff. `extra="forbid"` only rejects unknown keys that are PRESENT."""
    old = PortalPersona.model_validate({
        "project": "p",
        "screens": [{"id": "s0", "name": "Home", "url_template": "/", "signature": "sig-a"},
                    {"id": "s1", "name": "Taught", "url_template": "/taught"}],
        "history": [{"at": "2026-08-01T00:00:00", "summary": "initial persona"}],
    })
    assert old.screens[0].ident() == ("/", "sig-a")
    assert old.screens[1].ident() == ("/taught", None)
    assert old.history[0].counts() == {"new": 0, "changed": 0, "missing": 0,
                                       "broken": 0, "missing_unjudged": 0}
    # The review fix added `healthy_screens`; a revision written before it must
    # still validate, and default to "recorded no observation" rather than
    # "observed everything healthy" -- the latter would clear real broken records.
    assert old.history[0].healthy_screens == []
    diff = _classify(old, [_node("/", "sig-a-EDITED")])
    assert diff["changed_screens"] == ["/"] and diff["missing_screens"] == []


# --- CR5's interaction: a bound-truncated frontier may not claim `missing` ---


@pytest.mark.parametrize("status,exhausted", [
    (NodeStatus.EXPLORED, False), (NodeStatus.ABORTED_ERROR, True),
    (NodeStatus.ABORTED_DIALOG, True), (NodeStatus.SKIPPED_UNCHANGED, True),
])
def test_a_bound_truncated_crawl_never_reports_missing_only_unjudged(status, exhausted) -> None:
    """CR5/CR4: `missing` is "a genuine absence, NOT a bound-truncated frontier".
    A crawl that stopped early cannot tell a deleted screen from one it simply
    never got to, so it says so instead of inventing a finding."""
    diff = _classify(_persona(("/a", "sig-a"), ("/unreached", "sig-u")),
                     [_node("/a", "sig-a", status=status)], exhausted=exhausted)
    assert diff["missing_screens"] == []
    assert diff["missing_unjudged"] == ["/unreached"]
    assert ("not judged (a bound, skipped-unchanged screen, or abandoned visit "
            "left the crawl incomplete)") in persona_changes.describe(diff)


def test_a_skipped_screen_is_evidence_of_nothing() -> None:
    """CR5: a screen skipped as unchanged was not looked at. It is not broken
    (nobody tried it) and not missing (it was reached and matched)."""
    diff = _classify(_persona(("/a", "sig-a")),
                     [_node("/a", "sig-a", status=NodeStatus.SKIPPED_UNCHANGED)])
    assert diff == {"new_screens": [], "changed_screens": [], "missing_screens": [],
                    "broken_screens": [], "missing_unjudged": [], "healthy_screens": []}


def test_a_queued_never_visited_node_is_not_evidence_either() -> None:
    diff = _classify(_persona(("/a", "sig-a"), ("/b", "sig-b")),
                     [_node("/a", "sig-a"), _node("/b", "sig-b", status=NodeStatus.QUEUED)],
                     exhausted=False)
    assert diff["missing_unjudged"] == ["/b"]
    assert diff["missing_screens"] == []


def test_a_flowspec_sourced_screen_is_outside_the_crawl_sourced_diff() -> None:
    """CR4 is "scoped to crawl-sourced screen classification" (the contract's own
    words). A screen with no signature came from a reviewed FlowSpec; a crawl not
    reaching it is not evidence it is gone, so it is never reported missing."""
    persona = PortalPersona(project="p", screens=[
        PersonaScreen(id="s0", name="Taught only", url_template="/taught"),
        PersonaScreen(id="s1", name="Crawled", url_template="/a", signature="sig-a")])
    diff = _classify(persona, [_node("/a", "sig-a")])
    assert diff["missing_screens"] == []
    assert diff["missing_unjudged"] == []


# --- the machine-checkable record on the revision ---------------------------


def test_the_revision_carries_a_count_per_named_category() -> None:
    """CR4: a `PersonaRevision` records the counts of all four BY NAME — not
    merely a prose "what changed" sentence."""
    revision = PersonaRevision(at="2026-09-27T00:00:00", summary="screens 2 new, 1 missing",
                               new_screens=["/x", "/y"], missing_screens=["/z"])
    assert revision.counts() == {"new": 2, "changed": 0, "missing": 1,
                                 "broken": 0, "missing_unjudged": 0}


def test_classify_returns_exactly_the_revisions_own_field_names() -> None:
    """One concept, one place (C3): the schema defines the shape, `classify`
    returns values FOR it. A drifted key would silently drop a whole category."""
    diff = _classify(None, [_node("/a", "sig-a")])
    assert set(diff) == set(persona_changes.CATEGORIES) | set(persona_changes.PROVENANCE)
    PersonaRevision(at="2026-09-27T00:00:00", summary="s", **diff)  # must construct
    assert len(persona_changes.CATEGORIES) == 5, (
        "CR4/CR5 name five REPORTABLE categories; a sixth needs a contract amendment")
    assert set(persona_changes.CATEGORIES).isdisjoint(persona_changes.PROVENANCE)
    assert set(PersonaRevision(at="x", summary="s").counts()) == {
        "new", "changed", "missing", "broken", "missing_unjudged"}, (
        "provenance leaked into the counted surface")


def test_pp3_is_unchanged_a_blank_summary_is_still_refused() -> None:
    with pytest.raises(ValueError, match="may not be blank"):
        PersonaRevision(at="2026-09-27T00:00:00", summary="   ", new_screens=["/x"])


def test_the_classification_is_deterministic_and_sorted() -> None:
    """CR6: two runs over the same evidence produce byte-identical output."""
    nodes = [_node("/c", "s"), _node("/a", "s"), _node("/b", "s")]
    runs = [_classify(None, list(nodes)) for _ in range(5)]
    assert all(r == runs[0] for r in runs)
    assert runs[0]["new_screens"] == ["/a", "/b", "/c"]


def test_describe_says_nothing_when_nothing_moved() -> None:
    """PP3, unchanged: an identical re-run must not fabricate a revision."""
    assert persona_changes.describe(_classify(_persona(("/a", "s")), [_node("/a", "s")])) is None
