"""mongo-store M15 (model round-trip), M14, M16, M17: the `Path` functions over every backend.

The public `filestore` functions are routed to the backend under test (`filestore._route` is the
one seam), so `dump -> store -> load == original` is proved per schema family on every backend in
`BACKEND_FACTORIES`. U4 extends `FAMILIES` with the rest of its route table. The last tests use the
real routing: a key inside the data root, one that tries to leave it, and a path outside it.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fake_mongo import FakeMongoServer, seams
from pydantic import BaseModel
from state_backends import BACKEND_FACTORIES

import autotester.store.filestore as filestore
import autotester.store.mongo_routes as routes
from autotester.core.safe_names import UnsafeName
from autotester.schema.case import Case, CaseProposal
from autotester.schema.enums import Action, CaseClass, CaseKind, SourceKind
from autotester.schema.flowspec import ExpectedState, Flow, FlowSpec, Step
from autotester.schema.issue import Issue
from autotester.schema.project import Project, Source
from autotester.stages.expand import propose_cases
from autotester.stages.review import approve
from autotester.store.mongo_backend import reset_default_backend


def _step() -> Step:
    return Step(order=1, action=Action.NAVIGATE, target="/dashboard",
                expected=ExpectedState(visible_text=["Dashboard"]))


def _spec() -> FlowSpec:
    flow = Flow(id="flow", name="Browse", entry_screen="home", steps=[_step()])
    return approve(FlowSpec(project="pathlynks", flows=[flow]), "tester")


def _case(title: str = "login works", flow: str = "flow-login") -> Case:
    return Case(project="pathlynks", flow_id=flow, kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title=title, steps=[_step()])


FAMILIES: dict[str, Callable[[], BaseModel]] = {
    "project": lambda: Project(slug="pathlynks", name="Pathlynks", base_url="https://a.test",
                               allowed_domains=["a.test"]),
    "source": lambda: Source(project="pathlynks", kind=SourceKind.TEXT, text="a note",
                             uploaded_at=datetime(2026, 10, 29, 12, 30, tzinfo=UTC)),
    "case": _case,
    "flowspec": _spec,
    "case_proposal": lambda: propose_cases(_spec())[0],
    "issue": lambda: Issue(project="pathlynks", source_id="s1", recording_label="r", at_s=1.5,
                           screen="home", title="t", what_is_wrong="w"),
}


@pytest.fixture(params=sorted(BACKEND_FACTORIES))
def routed(request: pytest.FixtureRequest, tmp_path: Path,
           monkeypatch: pytest.MonkeyPatch) -> Any:
    """Route every `Path` function to the backend under test; keys are the paths as given."""
    backend = BACKEND_FACTORIES[request.param](tmp_path / "root")
    monkeypatch.setattr(filestore, "_route", lambda path: (backend, Path(path).as_posix()))
    return backend


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_a_model_round_trips_equal_through_a_whole_document(routed: Any, family: str) -> None:
    original = FAMILIES[family]()
    path = Path(f"projects/pathlynks/{family}.json")
    filestore.write_json(path, original)
    assert filestore.read_json(path, type(original)) == original


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_a_model_round_trips_equal_through_rows(routed: Any, family: str) -> None:
    original = FAMILIES[family]()
    path = Path(f"projects/pathlynks/{family}.jsonl")
    filestore.append_jsonl(path, original)
    assert filestore.read_jsonl(path, type(original)) == [original]


def test_read_json_of_a_missing_key_is_none(routed: Any) -> None:
    assert filestore.read_json(Path("projects/x/none.json"), Project) is None
    assert filestore.read_jsonl(Path("projects/x/none.jsonl"), Case) == []


def test_upsert_by_a_stored_field_keeps_position_and_delete_returns_a_bool(routed: Any) -> None:
    path = Path("projects/pathlynks/cases.jsonl")
    first, second, third = _case("a", "f1"), _case("b", "f2"), _case("c", "f3")
    for case in (first, second, third):
        filestore.upsert_jsonl(path, case, Case)
    changed = second.model_copy(update={"title": "b changed"})
    filestore.upsert_jsonl(path, changed, Case, key="flow_id")
    titles = [c.title for c in filestore.read_jsonl(path, Case)]
    assert titles == ["a", "b changed", "c"]
    assert filestore.delete_jsonl_row(path, Case, third.id) is True
    assert filestore.delete_jsonl_row(path, Case, third.id) is False
    assert len(filestore.read_jsonl(path, Case)) == 2


def test_upsert_by_a_derived_key_replaces_in_place_and_appends_when_new(routed: Any) -> None:
    """`CaseProposal.slot_id` is a property, not a stored field (project_store.py:146)."""
    path = Path("projects/pathlynks/case_proposals.jsonl")
    proposals = propose_cases(_spec())
    for proposal in proposals:
        filestore.upsert_jsonl(path, proposal, CaseProposal, key="slot_id")
    fresh = CaseProposal.model_validate({**proposals[0].model_dump(), "title": "changed", "id": ""})
    assert fresh.slot_id == proposals[0].slot_id and fresh.id != proposals[0].id
    filestore.upsert_jsonl(path, fresh, CaseProposal, key="slot_id")  # replaces the slot in place
    filestore.upsert_jsonl(path, fresh, CaseProposal, key="slot_id")  # and is idempotent
    stored = filestore.read_jsonl(path, CaseProposal)
    assert [p.id for p in stored] == [fresh.id, *[p.id for p in proposals[1:]]]


def test_a_delete_by_a_property_is_refused_not_silently_a_no_op(routed: Any) -> None:
    with pytest.raises(ValueError, match="not a stored field"):
        filestore.delete_jsonl_row(Path("projects/p/x.jsonl"), CaseProposal, "z", key="slot_id")


def test_a_malformed_row_raises_naming_the_path_and_row(routed: Any) -> None:
    path = Path("projects/pathlynks/cases.jsonl")
    filestore.append_jsonl(path, _case())
    routed.append_row(path.as_posix(), "{not json")
    with pytest.raises(ValueError, match=r"cases\.jsonl:2:"):
        filestore.read_jsonl(path, Case)
    with pytest.raises(ValueError, match=r"cases\.jsonl:2:"):
        filestore.upsert_jsonl(path, _case("other", "f9"), Case)
    with pytest.raises(ValueError, match=r"cases\.jsonl:2:"):
        filestore.delete_jsonl_row(path, Case, "nope")


def test_write_bytes_and_text_reach_the_backend(routed: Any) -> None:
    filestore.write_text(Path("a/t.txt"), "text")
    filestore.write_bytes(Path("a/b.bin"), b"bytes")
    assert routed.get("a/t.txt") == "text" and routed.get("a/b.bin") == "bytes"


# -- the real routing -----------------------------------------------------------------------

def test_a_path_inside_the_data_root_is_a_key_and_one_outside_is_a_plain_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, elsewhere = tmp_path / "root", tmp_path / "elsewhere"
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    root.mkdir()
    filestore.write_text(root.resolve() / "projects" / "p" / "x.txt", "in")
    filestore.write_text(elsewhere / "y.txt", "out")
    assert (root / "projects" / "p" / "x.txt").read_text(encoding="utf-8") == "in"
    assert (elsewhere / "y.txt").read_text(encoding="utf-8") == "out"


def test_a_path_that_climbs_out_of_the_root_is_refused_before_any_write(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    with pytest.raises(UnsafeName):
        filestore.write_text(root.resolve() / "projects" / ".." / ".." / "escape.txt", "x")
    assert not (tmp_path / "escape.txt").exists()
    assert sorted(p.name for p in root.rglob("*")) == []


# -- the real route table, and the Path-based directory functions ---------------------------

REAL_PATHS: dict[str, tuple[str, str]] = {  # family -> (key, collection the key must route to)
    "project": ("projects/pathlynks/project.json", "projects"),
    "source": ("projects/pathlynks/sources.jsonl", "sources"),
    "case": ("projects/pathlynks/cases.jsonl", "cases"),
    "flowspec": ("projects/pathlynks/flowspec.json", "project_docs"),
    "case_proposal": ("projects/pathlynks/case_proposals.jsonl", "case_proposals"),
    "issue": ("projects/pathlynks/issues.jsonl", "issues"),
}


@pytest.mark.parametrize("family", sorted(REAL_PATHS))
def test_a_model_round_trips_equal_at_its_real_route(routed: Any, family: str) -> None:
    key, collection = REAL_PATHS[family]
    assert routes.route(key).collection == collection
    original = FAMILIES[family]()
    if key.endswith(".jsonl"):
        filestore.append_jsonl(Path(key), original)
        assert filestore.read_jsonl(Path(key), type(original)) == [original]
    else:
        filestore.write_json(Path(key), original)
        assert filestore.read_json(Path(key), type(original)) == original


def test_exists_list_children_and_mtime_follow_the_backend(routed: Any) -> None:
    filestore.write_text(Path("projects/p/a.json"), "1")
    filestore.write_text(Path("projects/p/sub/b.txt"), "2")
    assert filestore.exists_path(Path("projects/p/a.json")) is True
    assert filestore.exists_path(Path("projects/p")) is True  # a directory that holds state
    assert filestore.exists_path(Path("projects/p/sub/b.txt")) is True
    assert filestore.exists_path(Path("projects/q")) is False
    assert filestore.exists_path(Path("projects/p/none.json")) is False
    assert filestore.list_children(Path("projects/p")) == ["a.json", "sub"]
    assert filestore.list_children(Path("projects/p"), suffix=".json") == ["a.json"]
    assert filestore.list_children(Path("projects/none")) == []
    stamp = filestore.mtime_path(Path("projects/p/a.json"))
    assert isinstance(stamp, float) and stamp > 1_000_000_000
    assert filestore.mtime_path(Path("projects/p/none.json")) is None


def test_the_path_functions_on_the_real_file_routing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, elsewhere = tmp_path / "root", tmp_path / "elsewhere"
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    monkeypatch.delenv("AUTOTESTER_STORE_AREAS", raising=False)
    root.mkdir()
    base = root.resolve() / "projects" / "p"
    filestore.write_text(base / "a.json", "in")
    filestore.write_text(elsewhere / "y.txt", "out")
    assert filestore.exists_path(base / "a.json") and filestore.exists_path(base)
    assert not filestore.exists_path(base / "none.json")
    assert filestore.list_children(base) == ["a.json"]
    assert filestore.mtime_path(base / "a.json") == (base / "a.json").stat().st_mtime
    assert filestore.mtime_path(base / "none.json") is None
    # A path outside the data root is a plain file whatever the selection says.
    assert filestore.exists_path(elsewhere / "y.txt") and filestore.exists_path(elsewhere)
    assert filestore.list_children(elsewhere) == ["y.txt"]
    assert filestore.mtime_path(elsewhere / "y.txt") == (elsewhere / "y.txt").stat().st_mtime
    with pytest.raises(UnsafeName):
        filestore.exists_path(root.resolve() / "projects" / ".." / ".." / "x")


def test_a_directory_listing_fans_out_across_the_backends_of_its_areas(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A project dir with `project.json` on disk and its `runs/` in Mongo lists both, and a
    directory that exists only in Mongo still exists (the areas are flipped one at a time)."""
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "runs=mongo")
    monkeypatch.setenv("AUTOTESTER_MONGO_URI", "mongodb://h/")
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    reset_default_backend()
    base = root.resolve() / "projects" / "p"
    try:
        with seams(client_factory=lambda _uri: FakeMongoServer().client()):
            filestore.write_text(base / "project.json", "{}")
            filestore.write_text(base / "runs" / "r1" / "run.json", "{}")
            assert not (base / "runs").exists()  # nothing of the run is on disk
            assert filestore.list_children(base) == ["project.json", "runs"]
            assert filestore.list_children(base / "runs") == ["r1"]
            assert filestore.exists_path(base / "runs")
            assert filestore.exists_path(base / "runs" / "r1")
            assert filestore.exists_path(base / "runs" / "r1" / "run.json")
            assert filestore.mtime_path(base / "runs" / "r1" / "run.json") is not None
            assert not filestore.exists_path(base / "runs" / "r2")
    finally:
        reset_default_backend()


def test_append_path_and_delete_path_follow_the_backend(routed: Any) -> None:
    log = Path("projects/p/trace/t.log")
    filestore.append_path(log, "a\n")
    filestore.append_path(log, b"b\n")  # bytes are text on a state path
    assert routed.get("projects/p/trace/t.log") == "a\nb\n"
    assert filestore.exists_path(log) and filestore.list_children(log.parent) == ["t.log"]
    filestore.delete_path(log)
    assert not filestore.exists_path(log) and routed.get("projects/p/trace/t.log") is None
    filestore.delete_path(log)  # missing_ok defaults to True
    with pytest.raises(FileNotFoundError):
        filestore.delete_path(log, missing_ok=False)


def test_append_path_and_delete_path_refuse_a_path_that_leaves_the_root(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    monkeypatch.delenv("AUTOTESTER_STORE_AREAS", raising=False)
    (tmp_path / "root").mkdir()
    out = tmp_path / "elsewhere" / "x.log"  # outside the data root: a plain file
    filestore.append_path(out, "1\n")
    filestore.append_path(out, "2\n")
    assert out.read_text(encoding="utf-8") == "1\n2\n"
    filestore.delete_path(out)
    assert not out.exists()
    climb = (tmp_path / "root").resolve() / "projects" / ".." / ".." / "x"
    with pytest.raises(UnsafeName):
        filestore.append_path(climb, "x")
    with pytest.raises(UnsafeName):
        filestore.delete_path(climb)
