"""`stages/screen_identity.py`: structural signature and `ScreenNode` identity.
Pure — no browser. Contract: qa/contracts/explore.md X3 (lands at T-143).
"""

from __future__ import annotations

from autotester.schema.screen_graph import ElementRef, PageObservation
from autotester.stages.screen_identity import node_from, structural_signature


def el(role: str, name: str, *, in_row: bool = False, visible: bool = True) -> ElementRef:
    return ElementRef(role=role, name=name, selector=f"#{role}-{name}", in_row=in_row,
                       visible=visible)


def test_two_list_rows_with_different_data_share_a_signature() -> None:
    """Row/list-item elements are excluded — the whole point of `in_row`."""
    page_a = [el("button", "Edit", in_row=False), el("link", "Row 1", in_row=True)]
    page_b = [el("button", "Edit", in_row=False), el("link", "Row 2", in_row=True)]
    assert structural_signature(page_a) == structural_signature(page_b)


def test_adding_a_new_non_row_control_changes_the_signature() -> None:
    base = [el("button", "Edit")]
    with_filter = [el("button", "Edit"), el("button", "Open filters")]
    assert structural_signature(base) != structural_signature(with_filter)


def test_invisible_elements_do_not_affect_the_signature() -> None:
    visible_only = [el("button", "Edit")]
    with_hidden = [el("button", "Edit"), el("button", "Hidden", visible=False)]
    assert structural_signature(visible_only) == structural_signature(with_hidden)


def test_digit_runs_in_names_are_normalised_together() -> None:
    """"Delete row 42" and "Delete row 17" contribute the same token."""
    page_a = [el("button", "Delete row 42")]
    page_b = [el("button", "Delete row 17")]
    assert structural_signature(page_a) == structural_signature(page_b)


def test_node_id_is_stable_across_element_order() -> None:
    elements = [el("button", "Save"), el("link", "Home")]
    obs_a = PageObservation(url="https://app.test/dashboard", elements=elements)
    obs_b = PageObservation(url="https://app.test/dashboard", elements=list(reversed(elements)))

    node_a = node_from(obs_a, "crawl_1", "erp", depth=0)
    node_b = node_from(obs_b, "crawl_1", "erp", depth=0)

    assert node_a.id == node_b.id


def test_two_ids_collapse_to_one_node_identity() -> None:
    """The B2 promise: /students/1 and /students/2 with identical controls
    are ONE screen identity, even though url_example differs."""
    elements = [el("button", "Edit"), el("link", "Back", in_row=False)]
    obs_1 = PageObservation(url="https://app.test/students/1", elements=elements)
    obs_2 = PageObservation(url="https://app.test/students/2", elements=elements)

    node_1 = node_from(obs_1, "crawl_1", "erp", depth=1)
    node_2 = node_from(obs_2, "crawl_1", "erp", depth=1)

    assert node_1.id == node_2.id
    assert node_1.url_template == node_2.url_template == "/students/{id}"


def test_different_controls_at_the_same_url_are_different_nodes() -> None:
    """A same-URL SPA toggle (e.g. a filter panel opening) with genuinely
    different controls must NOT collapse — the prior attempt's failure mode
    was the opposite direction (URL-only identity hid real differences)."""
    obs_closed = PageObservation(
        url="https://app.test/dashboard", elements=[el("button", "Open filters")]
    )
    obs_open = PageObservation(
        url="https://app.test/dashboard",
        elements=[el("button", "Open filters"), el("checkbox", "Show archived")],
    )

    node_closed = node_from(obs_closed, "crawl_1", "erp", depth=0)
    node_open = node_from(obs_open, "crawl_1", "erp", depth=0)

    assert node_closed.id != node_open.id


def test_index_html_and_directory_root_collapse_to_one_node_identity() -> None:
    """AT-334, reproduced at the unit that actually filed it: a real crawl of
    tests/fixtures/modal_site measured six nodes for a three-page site because
    "/" and "/index.html" (same page, same veiled state, identical reachable
    controls) got different url_templates and therefore different node ids.
    Pinned here at the node-identity boundary so the fix is verified without a
    browser."""
    elements = [el("button", "Excited"), el("button", "Focused"), el("button", "Tired"),
                el("link", "Skip for now")]
    obs_root = PageObservation(url="https://app.test/", elements=elements)
    obs_index = PageObservation(url="https://app.test/index.html", elements=elements)

    node_root = node_from(obs_root, "crawl_1", "modal_site", depth=0)
    node_index = node_from(obs_index, "crawl_1", "modal_site", depth=0)

    assert node_root.id == node_index.id
    assert node_root.url_template == node_index.url_template == "/"


def test_node_extra_field_rejected() -> None:
    import pytest
    from pydantic import ValidationError

    from autotester.schema.screen_graph import ScreenNode

    with pytest.raises(ValidationError):
        ScreenNode(
            crawl_id="c1", project="erp", url_template="/x", url_example="https://app.test/x",
            signature="abc", bogus_field=True,
        )
