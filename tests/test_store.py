"""Generic file persistence + the per-project facade. Contract: core-invariants.md C6."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from autotester.schema.case import Case, CaseProposal
from autotester.schema.enums import Action, CaseClass, CaseKind, SourceKind
from autotester.schema.flowspec import ExpectedState, Flow, FlowSpec, Screen, Step
from autotester.schema.project import Project, Source
from autotester.store import (
    ProjectStore,
    append_jsonl,
    read_json,
    read_jsonl,
    upsert_jsonl,
    write_json,
)


def make_project(slug: str = "pathlynks") -> Project:
    return Project(slug=slug, name="Pathlynks", base_url="https://app.pathlynks.test",
                    allowed_domains=["pathlynks.test"])


def make_step() -> Step:
    return Step(order=1, action=Action.NAVIGATE, target="/dashboard",
                expected=ExpectedState(visible_text=["Dashboard"]))


def make_case(project: str = "pathlynks", flow_id: str = "flow-login") -> Case:
    return Case(project=project, flow_id=flow_id, kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title="login works", steps=[make_step()])


# -- generic primitives ------------------------------------------------------

def test_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    write_json(path, make_project())
    loaded = read_json(path, Project)
    assert loaded is not None and loaded.slug == "pathlynks"


def test_read_json_missing_file_is_none_not_an_error(tmp_path: Path) -> None:
    assert read_json(tmp_path / "absent.json", Project) is None


def test_read_json_malformed_names_the_path(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    path.write_text('{"slug": "bad slug with spaces"}', encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(str(path))):
        read_json(path, Project)


def test_write_json_is_atomic_and_leaves_no_tmp_files(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "project.json"
    write_json(path, make_project())
    leftovers = list((tmp_path / "sub").glob(".tmp-*"))
    assert leftovers == [] and path.exists()


def test_jsonl_append_and_read_preserve_order(tmp_path: Path) -> None:
    path = tmp_path / "sources.jsonl"
    for i in range(3):
        append_jsonl(path, Source(project="p", kind=SourceKind.TEXT, text=f"note {i}"))
    rows = read_jsonl(path, Source)
    assert [r.text for r in rows] == ["note 0", "note 1", "note 2"]


def test_jsonl_malformed_row_names_its_line(tmp_path: Path) -> None:
    path = tmp_path / "sources.jsonl"
    append_jsonl(path, Source(project="p", kind=SourceKind.TEXT, text="ok"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json}\n")
    with pytest.raises(ValueError, match=re.escape(f"{path}:2")):
        read_jsonl(path, Source)


def test_upsert_replaces_matching_id_in_place_and_appends_new_ids(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    a, b = make_case(flow_id="flow-a"), make_case(flow_id="flow-b")
    upsert_jsonl(path, a, Case)
    upsert_jsonl(path, b, Case)
    updated_a = a.model_copy(update={"title": "login works, edited"})
    upsert_jsonl(path, updated_a, Case)
    rows = read_jsonl(path, Case)
    assert [r.id for r in rows] == [a.id, b.id]  # order preserved, no duplicate
    assert rows[0].title == "login works, edited"


# -- ProjectStore facade -----------------------------------------------------

def test_project_roundtrip(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    assert store.load_project() is None
    store.save_project(make_project())
    loaded = store.load_project()
    assert loaded is not None and loaded.name == "Pathlynks"


def test_add_source_is_idempotent_on_content_address(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    source = Source(project="pathlynks", kind=SourceKind.TEXT, text="how login works")
    store.add_source(source)
    store.add_source(source)  # identical content -> no duplicate
    assert len(store.list_sources()) == 1


def test_flowspec_roundtrip(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    spec = FlowSpec(
        project="pathlynks",
        screens=[Screen(id="dashboard", name="Dashboard")],
        flows=[Flow(id="flow-login", name="Login", steps=[make_step()],
                    entry_screen="login", exit_screen="dashboard")],
    )
    store.save_flowspec(spec)
    loaded = store.load_flowspec()
    assert loaded is not None and loaded.flows[0].id == "flow-login"


def test_add_case_is_idempotent_when_a_flowspec_regenerates(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    case = make_case()
    store.add_case(case)
    store.add_case(Case(**{**case.model_dump(exclude={"id", "created_at"}), "id": ""}))
    assert len(store.list_cases()) == 1


def test_add_case_does_not_rescan_the_file_on_every_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AT-024: add_case used to call list_cases() (a full JSONL read) before
    every single append -- O(n) per add. The id cache means only the FIRST
    add in a store's lifetime reads the file; every later add in the same
    instance is an in-memory set check."""
    import autotester.store.project_store as project_store_module

    store = ProjectStore("pathlynks", tmp_path)
    calls = []
    real_read_jsonl = project_store_module.read_jsonl

    def counting_read_jsonl(path, model):
        calls.append(path)
        return real_read_jsonl(path, model)

    monkeypatch.setattr(project_store_module, "read_jsonl", counting_read_jsonl)

    for i in range(5):
        store.add_case(Case(**{**make_case().model_dump(exclude={"id", "created_at"}),
                                "flow_id": f"flow-{i}", "id": ""}))  # flow_id feeds compute_id

    assert len(calls) == 1  # only the first add's cache-population read
    assert len(store.list_cases()) == 5  # list_cases() itself always reads fresh


def test_add_case_cache_does_not_hide_a_case_added_by_another_process(tmp_path: Path) -> None:
    """The id cache is populated lazily per-instance -- a second ProjectStore
    pointed at the same directory always sees what's actually on disk."""
    first = ProjectStore("pathlynks", tmp_path)
    case_a = make_case()
    first.add_case(case_a)  # populates first's cache with {case_a.id}

    second = ProjectStore("pathlynks", tmp_path)
    case_b = Case(**{**case_a.model_dump(exclude={"id", "created_at"}),
                      "flow_id": "flow-other", "id": ""})
    second.add_case(case_b)

    assert len(first.list_cases()) == 2
    assert len(second.list_cases()) == 2


def test_a_human_can_hand_edit_an_artifact_and_the_store_still_loads(tmp_path: Path) -> None:
    """C6: artifacts are files a human can open, edit, or delete."""
    store = ProjectStore("pathlynks", tmp_path)
    store.save_project(make_project())
    new_name = "Pathlynks (renamed by hand)"
    text = store.paths.config.read_text(encoding="utf-8")
    text = text.replace('"name": "Pathlynks"', f'"name": "{new_name}"')
    store.paths.config.write_text(text, encoding="utf-8")
    assert store.load_project().name == new_name


def test_delete_case_clears_the_id_cache_within_one_store_instance(tmp_path: Path) -> None:
    """AT-066: the UI-level delete-then-re-add test cannot prove this — a fresh
    `ProjectStore` is built per request, so it would stay green even if
    `delete_case` never called `discard`. Exercised here against ONE instance,
    which is the only place the cache is observable."""
    store = ProjectStore("pathlynks", tmp_path)
    case = make_case()
    store.add_case(case)
    assert store.has_case(case.id)

    assert store.delete_case(case.id) is True

    assert not store.has_case(case.id)      # the cache, not just the file
    assert store.list_cases() == []
    store.add_case(case)                     # the re-add the stale cache would swallow
    assert [c.id for c in store.list_cases()] == [case.id]


def test_delete_case_returns_false_for_an_unknown_id(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    store.add_case(make_case())

    assert store.delete_case("case_nope") is False
    assert len(store.list_cases()) == 1


def test_update_case_keeps_the_id_cached_and_replaces_in_place(tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path)
    case = store.add_case(make_case())

    store.update_case(case.model_copy(update={"title": "renamed"}))

    assert store.has_case(case.id)
    cases = store.list_cases()
    assert len(cases) == 1                   # replaced, never appended twice
    assert cases[0].title == "renamed"
    assert cases[0].id == case.id


def test_priority_selection_adds_pinned_p0_once_and_preserves_default_order(tmp_path) -> None:
    from autotester.store.project_store import PinnedCaseError

    store = ProjectStore("pathlynks", tmp_path)
    cases = [make_case(flow_id=f"f-{priority}").model_copy(update={"priority": priority})
             for priority in ["p0", "p1", "p2", "p3"]]
    for case in cases:
        store.add_case(case)
    pinned = Case.model_validate({**make_case(flow_id="bug").model_dump(),
                                 "pinned": True, "pinned_issue_id": "issue_1"})
    store.add_case(pinned)
    assert [c.id for c in store.list_cases()] == [c.id for c in cases] + [pinned.id]
    assert [c.id for c in store.list_cases(["p0"])] == [cases[0].id, pinned.id]
    assert [c.id for c in store.list_cases(["p1"])] == [cases[1].id, pinned.id]
    assert len(store.list_cases(["p0", "p0"])) == 2
    with pytest.raises(PinnedCaseError):
        store.delete_case(pinned.id)
    assert store.delete_case(cases[0].id)  # ordinary p0 is not newly pinned


def test_proposal_restage_preserves_only_exact_identity_and_content(tmp_path) -> None:
    from autotester.stages.expand import propose_cases
    from autotester.stages.review import approve

    spec = approve(FlowSpec(project="pathlynks", flows=[Flow(
        id="flow", name="Browse", entry_screen="home", steps=[make_step()],
    )]), "tester")
    store = ProjectStore("pathlynks", tmp_path)
    store.save_flowspec(spec)
    original = propose_cases(spec)
    store.stage_case_proposals(original)
    happy = original[0]
    approved = store.review_case_proposal(happy.id, "tester", True)
    store.stage_case_proposals(original)
    assert store.list_case_proposals()[0] == approved
    changed = CaseProposal.model_validate({**happy.model_dump(), "id": "", "title": "Changed"})
    store.stage_case_proposals([changed])
    current = store.list_case_proposals()[0]
    assert current.id != happy.id and current.status == "proposed"
    assert current.reviewed_by is None and current.reviewed_at is None
    with pytest.raises(ValueError, match="HAPPY"):
        store.preflight_case_proposals(spec)
    with pytest.raises(ValueError, match="no current"):
        store.review_case_proposal(happy.id, "tester", True)
    assert store.list_cases() == []
