"""Crawl → FlowSpec merge (Track B5). Contract: qa/contracts/explore.md +
qa/contracts/coverage.md. The merge must never rewrite what a human approved,
never silently pick a winner, and never leave a changed spec looking reviewed.
"""

from __future__ import annotations

from autotester.schema.enums import ReviewStatus
from autotester.schema.flowspec import FlowSpec, Review, Screen
from autotester.schema.screen_graph import ElementRef, ScreenNode
from autotester.stages.explore_merge import merge_screens, screen_from


def make_node(
    *, url: str = "https://app.test/students/7", template: str = "app.test/students/{id}",
    signature: str = "sig_a", name: str = "Students", elements: list[ElementRef] | None = None,
    crawl_id: str = "crawl_1",
) -> ScreenNode:
    return ScreenNode(
        crawl_id=crawl_id, project="erp", url_template=template, url_example=url,
        signature=signature, name=name, title=name, elements=elements or [],
    )


def el(role: str, name: str, *, in_row: bool = False, visible: bool = True) -> ElementRef:
    return ElementRef(role=role, name=name, selector=f"#{name}", in_row=in_row, visible=visible)


# -- screen_from: what a crawled node becomes --------------------------------

def test_url_pattern_is_a_hostless_path_not_the_node_template() -> None:
    """`Screen.url_pattern` is compared against run URLs by `coverage.py`, which
    works in paths. Copying `node.url_template` verbatim would put a host into
    the pattern and every coverage diff would then miss."""
    screen = screen_from(make_node())
    assert screen.url_pattern == "/students/{id}"


def test_screen_keeps_the_node_id_so_a_re_merge_is_a_no_op() -> None:
    node = make_node()
    assert screen_from(node).id == node.id


def test_row_content_is_excluded_from_signals() -> None:
    node = make_node(elements=[
        el("button", "Filters"), el("link", "Ada Lovelace", in_row=True),
        el("link", "Alan Turing", in_row=True),
    ])
    signals = screen_from(node).signals
    assert "Filters" in signals
    assert "Ada Lovelace" not in signals


def test_inputs_become_fields_and_are_never_marked_secret() -> None:
    """A field is a secret because a human declared a `SecretRef`, never
    because a crawler guessed from a role."""
    node = make_node(elements=[el("textbox", "Email"), el("combobox", "Course")])
    fields = screen_from(node).fields
    assert [(f.name, f.type) for f in fields] == [("Email", "text"), ("Course", "select")]
    assert all(f.secret_key is None for f in fields)


# -- merge_screens -----------------------------------------------------------

def test_new_screens_are_added_and_review_resets_to_draft() -> None:
    spec = FlowSpec(project="erp", review=Review(status=ReviewStatus.APPROVED, by="umesh"))
    merged = merge_screens(spec, [make_node()], "erp", crawl_id="crawl_1")

    assert len(merged.screens) == 1
    assert merged.review.status is ReviewStatus.DRAFT
    assert merged.version == spec.version + 1
    assert "crawl_1" in merged.source_ids


def test_merging_the_same_crawl_twice_changes_nothing() -> None:
    nodes = [make_node()]
    once = merge_screens(FlowSpec(project="erp"), nodes, "erp", crawl_id="crawl_1")
    twice = merge_screens(once, nodes, "erp", crawl_id="crawl_1")

    assert twice.version == once.version
    assert len(twice.screens) == 1
    assert twice.fingerprint == once.fingerprint


def test_an_existing_screen_is_never_rewritten() -> None:
    node = make_node()
    existing = Screen(id=node.id, name="Human-named students page", url_pattern="/students/{id}")
    spec = FlowSpec(project="erp", screens=[existing],
                    review=Review(status=ReviewStatus.APPROVED))

    merged = merge_screens(spec, [node], "erp", crawl_id="crawl_1")

    assert merged.screen(node.id).name == "Human-named students page"
    assert merged.review.status is ReviewStatus.APPROVED  # nothing changed, no reset


def test_a_name_clash_on_the_same_url_keeps_both_and_records_a_conflict() -> None:
    """Two screens claiming one url_pattern under different names is a real
    disagreement — the crawl may have found an SPA state the spec models as one
    page. Picking a winner silently is how a product map stops matching."""
    spec = FlowSpec(project="erp", screens=[
        Screen(id="scr_human", name="Student list", url_pattern="/students/{id}"),
    ])
    merged = merge_screens(spec, [make_node(name="Student detail")], "erp", crawl_id="crawl_1")

    assert len(merged.screens) == 2
    assert len(merged.conflicts) == 1
    conflict = merged.conflicts[0]
    assert conflict.subject == "/students/{id}"
    assert any("Student list" in c for c in conflict.claims)
    assert any("Student detail" in c for c in conflict.claims)


def test_a_same_named_rediscovery_merges_instead_of_duplicating() -> None:
    """AT-102: a non-structural screen re-discovered at the SAME url_pattern
    under the SAME name is the crawl finding what the spec already knows
    (under a fresh node id, so it can't be caught by the known-ids check
    alone) — not a new screen, and not a disagreement either."""
    spec = FlowSpec(project="erp", screens=[
        Screen(id="scr_old", name="Students", url_pattern="/students/{id}"),
    ])
    merged = merge_screens(spec, [make_node(name="Students")], "erp", crawl_id="crawl_1")

    assert len(merged.screens) == 1
    assert merged.screens[0].id == "scr_old"
    assert merged.conflicts == []


def test_the_same_conflict_is_not_recorded_twice_on_re_merge() -> None:
    spec = FlowSpec(project="erp", screens=[
        Screen(id="scr_human", name="Student list", url_pattern="/students/{id}"),
    ])
    nodes = [make_node(name="Student detail")]
    once = merge_screens(spec, nodes, "erp", crawl_id="crawl_1")
    twice = merge_screens(once, nodes, "erp", crawl_id="crawl_1")

    assert len(twice.conflicts) == 1


def test_merging_into_no_flowspec_creates_a_draft_one() -> None:
    merged = merge_screens(None, [make_node()], "erp", crawl_id="crawl_1")
    assert merged.project == "erp"
    assert merged.review.status is ReviewStatus.DRAFT


def test_two_spa_states_at_one_url_are_two_screens_not_a_conflict() -> None:
    """Found running a real crawl: the fixture's index page has a filter toggle,
    so one URL yields two structurally distinct screens (explore.md X3 requires
    exactly that). Treating a shared `url_pattern` as a disagreement would file
    a false conflict on every SPA. A conflict is for two SOURCES disagreeing
    about one screen, not for one crawl correctly finding two."""
    nodes = [
        make_node(url="https://app.test/", template="app.test/", signature="sig_plain",
                  name="Home"),
        make_node(url="https://app.test/", template="app.test/", signature="sig_filters",
                  name="Home with filters open"),
    ]
    merged = merge_screens(None, nodes, "erp", crawl_id="crawl_1")

    assert len(merged.screens) == 2
    assert merged.conflicts == []


def test_a_real_screen_node_id_carries_the_structural_prefix() -> None:
    """Pins the coupling `_is_structural` depends on: `ScreenNode` builds its id
    with `content_id("node", ...)`. If that prefix ever changes, this fails here
    rather than silently turning every structural screen into a conflict."""
    from autotester.stages.explore_merge import _STRUCTURAL_ID_PREFIX

    assert make_node().id.startswith(_STRUCTURAL_ID_PREFIX)


def test_spa_states_found_by_two_separate_crawls_still_do_not_conflict() -> None:
    """AT-103 (checker-found): the same-URL exemption was scoped to one CRAWL,
    not to identity — so merging one SPA state from crawl 1 and the other from
    crawl 2 filed a false Conflict, and the UI has an "Explore again" button
    that makes re-crawling the intended workflow. Both claims come from the
    crawler and neither disagrees with the other."""
    plain = make_node(url="https://app.test/", template="app.test/",
                      signature="sig_plain", name="Home", crawl_id="crawl_1")
    filtered = make_node(url="https://app.test/", template="app.test/",
                         signature="sig_filters", name="Home with filters open",
                         crawl_id="crawl_2")

    after_first = merge_screens(None, [plain], "erp", crawl_id="crawl_1")
    after_second = merge_screens(after_first, [filtered], "erp", crawl_id="crawl_2")

    assert len(after_second.screens) == 2
    assert after_second.conflicts == []


def test_an_index_html_rediscovery_merges_with_a_slash_screen_instead_of_duplicating() -> None:
    """AT-618: `merge_screens`'s own-pattern dedupe (`by_pattern`) is a literal
    dict lookup on `Screen.url_pattern`, never routed through
    `stages/coverage.py::_path_of` — so `screen_from` itself must store the
    FOLDED pattern, or a screen first crawled at '/' and rediscovered at
    '/index.html' (same page, same name) is filed as a brand-new Screen
    instead of the rediscovery `_is_rediscovery` exists to catch."""
    spec = FlowSpec(project="erp", screens=[
        Screen(id="scr_old", name="Home", url_pattern="/"),
    ])
    index_node = make_node(url="https://app.test/index.html", template="app.test/",
                           name="Home")

    merged = merge_screens(spec, [index_node], "erp", crawl_id="crawl_1")

    assert len(merged.screens) == 1
    assert merged.screens[0].id == "scr_old"
    assert merged.conflicts == []


def test_a_human_authored_claim_is_still_contradicted_by_a_crawl() -> None:
    """The other direction, and the reason the rule is about identity rather
    than about suppressing conflicts: a screen with no structural identity
    asserts a URL and nothing more, so a crawl CAN disagree with it."""
    spec = FlowSpec(project="erp", screens=[
        Screen(id="scr_human", name="Student list", url_pattern="/students/{id}"),
    ])
    merged = merge_screens(spec, [make_node(name="Student detail")], "erp", crawl_id="crawl_9")

    assert len(merged.conflicts) == 1
