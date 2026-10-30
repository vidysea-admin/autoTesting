"""mongo-store M18, M21, M22 on the Mongo BACKEND: how text is laid out, indexed and split.

M18: a document holds the text verbatim (any key shape, CRLF, non-ASCII), 12 MB is refused and
nothing is stored, concurrent appends never share a `seq`, upsert keeps `seq`. M21: every routed
collection is a real collection with its indexes, created idempotently; each key family lands in
the collection the table names. M22: a persona over 4 MB keeps its graph as `kg_*` rows and reads
back equal; a rewrite never mixes generations.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

import pytest
from fake_mongo import FakeMongoServer, open_store

from autotester.core.redact import Redactor
from autotester.schema.portal_persona import GraphEdge, GraphNode, PortalPersona
from autotester.store import mongo_routes as routes
from autotester.store.mongo_backend import MAX_DOC_BYTES, MongoBackend
from autotester.store.mongo_guard import COLLECTIONS
from autotester.store.mongo_routes import StoreDocTooLarge, text_sha

DB = "autotester"
PERSONA = "projects/p/portal_persona.json"


def make(server: FakeMongoServer | None = None) -> tuple[MongoBackend, FakeMongoServer]:
    server = server or FakeMongoServer()
    return MongoBackend(open_store(client=server.client()), Redactor({})), server


def coll(server: FakeMongoServer, name: str) -> Any:
    return server.databases[DB][name]


@pytest.mark.parametrize("body", [
    '{"a.b": 1}', '{"$set": {"x": 1}}', '{"k": "v"}\r\n', "héllo wörld ✓\n", "", "plain text",
    '{"nested": {"a.b": {"$x": [1, 2]}}}', "line1\r\nline2\r\n"])
def test_a_body_comes_back_byte_for_byte(body: str) -> None:
    backend, _ = make()
    backend.put("projects/p/doc.json", body)
    assert backend.get("projects/p/doc.json") == body
    assert backend.put_if("projects/p/doc.json", body + "x", text_sha(body)) is True


def test_rows_with_dotted_and_dollar_keys_round_trip_and_match_on_a_field() -> None:
    backend, _ = make()
    row = json.dumps({"id": "a", "a.b": 1, "$gt": 2}, sort_keys=True)
    backend.append_row("projects/p/cases.jsonl", row)
    assert backend.rows("projects/p/cases.jsonl") == [row]
    backend.upsert_row("projects/p/cases.jsonl", "id", "a", row.replace("1", "7"))
    assert json.loads(backend.rows("projects/p/cases.jsonl")[0])["a.b"] == 7


def test_a_body_over_12_mb_is_refused_and_nothing_is_stored(
        caplog: pytest.LogCaptureFixture) -> None:
    backend, server = make()
    with pytest.raises(StoreDocTooLarge, match="limit"):
        backend.put("projects/p/big.json", "x" * (MAX_DOC_BYTES + 1))
    with pytest.raises(StoreDocTooLarge):
        backend.append_row("projects/p/cases.jsonl", "x" * (MAX_DOC_BYTES + 1))
    assert backend.get("projects/p/big.json") is None
    assert backend.rows("projects/p/cases.jsonl") == []
    stored = [d for c in server.databases[DB].collections.values() for d in c.docs]
    assert [d["_id"] for d in stored] == ["marker"]  # only the identity marker
    with caplog.at_level(logging.WARNING, logger="autotester.store.mongo_backend"):
        backend.put("projects/p/mid.json", "y" * (5 * 1024 * 1024))
    assert "state document projects/p/mid.json" in caplog.text
    assert len(backend.get("projects/p/mid.json") or "") == 5 * 1024 * 1024


def test_concurrent_appends_never_share_a_seq_and_keep_one_order() -> None:
    backend, server = make()
    gate = threading.Barrier(16)

    def work(index: int) -> None:
        gate.wait()
        backend.append_row("projects/p/cases.jsonl", json.dumps({"id": index}))

    threads = [threading.Thread(target=work, args=(i,)) for i in range(16)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    seqs = [d["seq"] for d in coll(server, "cases").docs]
    assert sorted(seqs) == list(range(1, 17)) and len(backend.rows("projects/p/cases.jsonl")) == 16


def test_upsert_keeps_the_seq_of_the_row_it_replaces() -> None:
    backend, server = make()
    for name in "abc":
        backend.append_row("projects/p/cases.jsonl", json.dumps({"id": name, "v": 1}))
    before = {d["_id"]: d["seq"] for d in coll(server, "cases").docs}
    backend.upsert_row("projects/p/cases.jsonl", "id", "b", json.dumps({"id": "b", "v": 2}))
    assert {d["_id"]: d["seq"] for d in coll(server, "cases").docs} == before


def test_indexes_exist_for_every_routed_collection_and_a_second_pass_changes_nothing() -> None:
    backend, server = make()
    snapshot = {n: dict(c.indexes) for n, c in server.databases[DB].collections.items()}
    assert set(snapshot) >= routes.ROUTED_COLLECTIONS
    for name in routes.ROUTED_COLLECTIONS:
        assert set(snapshot[name]) == {"k", "p_k", "k_seq"}, name
        assert snapshot[name]["k_seq"] == ([("k", 1), ("seq", 1)], True)
    backend.ensure_indexes()
    MongoBackend(open_store(client=server.client()), Redactor({}))  # a second start
    assert {n: dict(c.indexes) for n, c in server.databases[DB].collections.items()} == snapshot


def test_every_collection_of_the_closed_set_is_routed_or_owned_by_a_later_unit() -> None:
    assert routes.ROUTED_COLLECTIONS <= COLLECTIONS
    assert set(routes.OTHER_UNITS) == COLLECTIONS - routes.ROUTED_COLLECTIONS
    assert set(routes.OTHER_UNITS.values()) <= {"U6", "U11", "U12"}


ROUTED = [  # key -> (collection, area, is a row set)
    ("projects/p/project.json", "projects", "projects", False),
    ("projects/p/sources.jsonl", "sources", "projects", True),
    ("projects/p/sources/s1/media.json", "source_media", "projects", False),
    ("projects/p/sources/s1/transcript.json", "source_docs", "projects", False),
    ("projects/p/cases.jsonl", "cases", "projects", True),
    ("projects/p/case_proposals.jsonl", "case_proposals", "projects", True),
    ("projects/p/rubrics/r1.json", "rubrics", "projects", False),
    ("projects/p/issues.jsonl", "issues", "projects", True),
    ("projects/p/requests.jsonl", "requests", "projects", True),
    ("projects/p/user_personas.jsonl", "user_personas", "projects", True),
    ("projects/p/flow_plans.jsonl", "flow_plans", "projects", True),
    ("projects/p/approvals.jsonl", "approvals", "approvals", True),
    ("projects/p/approval_revocations.jsonl", "approval_revocations", "approvals", True),
    ("projects/p/bench/a.json", "bench_docs", "projects", False),
    ("projects/p/bug_events/e.json", "bug_events", "projects", False),
    ("projects/p/bug_loop_config.json", "bug_config", "projects", False),
    ("projects/p/scripts/s.json", "scripts", "projects", False),
    ("projects/p/reviews/r.json", "reviews", "projects", False),
    ("projects/p/ai/x.json", "ai_docs", "projects", False),
    ("projects/p/flowspec.json", "project_docs", "projects", False),
    (PERSONA, "project_docs", "projects", False),
    ("projects/p/runs/r1/trace.jsonl", "run_traces", "runs", True),
    ("projects/p/runs/r1/bundles/b.json", "bundles", "runs", False),
    ("projects/p/runs/r1/run.json", "runs", "runs", False),
    ("projects/p/runs/r1/c1.verdict.json", "run_verdicts", "runs", False),
    ("projects/p/runs/r1/c1.json", "run_results", "runs", False),
    ("projects/p/runs/r1/state.json", "run_docs", "runs", False),
    ("projects/p/runs/r1/ux_report.json", "run_docs", "runs", False),
    ("projects/p/crawl/c1/crawl.json", "crawls", "crawls", False),
    ("projects/p/crawl/c1/nodes.jsonl", "crawl_nodes", "crawls", True),
    ("projects/p/crawl/c1/edges.jsonl", "crawl_edges", "crawls", True),
    ("projects/p/crawl/c1/issues.jsonl", "crawl_issues", "crawls", True),
    ("projects/p/crawl/c1/network.jsonl", "crawl_network", "crawls", True),
    ("projects/p/crawl/c1/other.json", "crawl_docs", "crawls", False),
    ("projects/p/crawl_summaries/c1.json", "crawl_summaries", "crawls", False),
    (".work/run_queue.json", "server_state", "queue", False),
    (".work/notification_prefs/u.json", "notification_prefs", "settings", False),
    (".work/audit.jsonl", "audit_log", "settings", True),
    (".work/drive-jobs/j.json", "drive_jobs", "settings", False),
    (".work/team/schedule/claims/c.json", "schedule_claims", "queue", False),
    (".work/team/schedule/records.jsonl", "schedule_records", "queue", True),
    (".work/team/schedule/state.json", "server_state", "queue", False),
    (".work/team/delivery/d.json", "delivery_records", "queue", False),
    (".work/server_settings.json", "server_state", "settings", False),
]


@pytest.mark.parametrize(("key", "collection", "area", "rows"), ROUTED)
def test_each_key_family_lands_in_the_collection_the_table_names(
        key: str, collection: str, area: str, rows: bool) -> None:
    assert routes.route(key) == routes.Route(collection, area, rows, routes.route(key).project)
    backend, server = make()
    if rows:
        backend.append_row(key, '{"id": 1}')
        assert backend.rows(key) == ['{"id": 1}']
    else:
        backend.put(key, "body")
        assert backend.get(key) == "body"
    holders = [n for n, c in server.databases[DB].collections.items()
               if any(d.get("k") == key for d in c.docs)]
    assert holders == [collection]
    assert routes.route(key).project == (key.split("/")[1] if key.startswith("projects/") else "")


def test_a_row_set_key_refuses_a_document_call_and_the_reverse() -> None:
    backend, _ = make()
    with pytest.raises(ValueError, match="row set"):
        backend.put_if("projects/p/cases.jsonl", "x", None)
    with pytest.raises(ValueError, match="row set"):
        backend.append_row("projects/p/project.json", "{}")


def _persona(nodes: int, label: int, tag: str = "v1") -> PortalPersona:
    graph_nodes = [GraphNode.make("screen", f"s{i}", tag + "x" * label) for i in range(nodes)]
    edges = [GraphEdge(kind="leads_to", src=f"screen:s{i}", dst=f"screen:s{i + 1}")
             for i in range(nodes - 1)]
    persona = PortalPersona(project="p")
    persona.graph.nodes.extend(graph_nodes)
    persona.graph.edges.extend(edges)
    return persona


def test_a_small_persona_is_stored_whole() -> None:
    backend, server = make()
    original = _persona(5, 10)
    backend.put(PERSONA, original.model_dump_json(indent=2, exclude_none=True))
    assert not coll(server, "kg_nodes").docs and "split" not in coll(server, "project_docs").docs[0]
    assert PortalPersona.model_validate_json(backend.get(PERSONA) or "") == original


def test_a_persona_over_4_mb_splits_into_kg_rows_and_reads_back_equal() -> None:
    backend, server = make()
    original = _persona(2000, 2300)
    text = original.model_dump_json(indent=2, exclude_none=True)
    assert len(text.encode()) > routes.KG_SPLIT_BYTES
    backend.put(PERSONA, text)
    doc = coll(server, "project_docs").docs[0]
    assert doc["split"] and len(doc["text"]) < 4096
    assert len(coll(server, "kg_nodes").docs) == 2000 and len(coll(server, "kg_edges").docs) == 1999
    assert PortalPersona.model_validate_json(backend.get(PERSONA) or "") == original
    assert backend.exists(PERSONA) and backend.keys("projects/p/") == [PERSONA]


def test_a_rewrite_never_mixes_generations_and_a_shrink_or_delete_drops_the_rows() -> None:
    backend, server = make()
    first, second = _persona(2000, 2300, "first"), _persona(1900, 2400, "second")
    backend.put(PERSONA, first.model_dump_json(indent=2, exclude_none=True))
    backend.put(PERSONA, second.model_dump_json(indent=2, exclude_none=True))
    assert len(coll(server, "kg_nodes").docs) == 1900  # the first generation is gone
    assert PortalPersona.model_validate_json(backend.get(PERSONA) or "") == second
    backend.put(PERSONA, _persona(3, 5).model_dump_json())
    assert not coll(server, "kg_nodes").docs and not coll(server, "kg_edges").docs
    backend.put(PERSONA, second.model_dump_json(indent=2, exclude_none=True))
    assert backend.delete(PERSONA) is True
    assert not coll(server, "kg_nodes").docs and backend.get(PERSONA) is None


def test_a_persona_that_is_not_a_graph_document_stays_whole_however_large() -> None:
    backend, server = make()
    text = json.dumps({"graph": "not a dict", "pad": "x" * (5 * 1024 * 1024)})
    backend.put(PERSONA, text)
    assert backend.get(PERSONA) == text and not coll(server, "kg_nodes").docs
