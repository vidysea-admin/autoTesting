"""C1-C3 (T-136 marks, T-218 answer list): the benchmark inputs a person gives through the UI.

Real routes through the login gate: an editor marks findings on the crawl and run pages and
uploads the private answer list; a view-only account sees read-only controls and is refused on
POST; the list is stored under `.work/`, pinned by sha256 and never served back. All data here
is synthetic.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from auth_harness import ADMIN, PASSWORD, account, client, gate_on, login, project
from fastapi.testclient import TestClient

from autotester.auth import accounts, groups
from autotester.schema.crawl import Crawl, CrawlIssue
from autotester.schema.enums import CrawlStatus, IssueKind, Result
from autotester.schema.run import Run
from autotester.schema.verdict import Failure, Verdict
from autotester.stages import bench_inputs, bench_marks
from autotester.stages.bench_from_run import bench_from_run
from autotester.store.project_store import ProjectStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_acceptance_comparison as check

API = "https://demo.test/api/status"
CORPUS = "demo-acceptance"
LIST = {"items": [
    {"id": "A1", "priority": "P0", "technique": "inbox"},
    {"id": "A2", "priority": "P1", "technique": "state_after", "needs_seeded_data": True},
]}
LIST_BYTES = json.dumps(LIST).encode()


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = gate_on(tmp_path, monkeypatch)
    account(ADMIN)  # the first account becomes the admin the others may be added beside
    project(base, "demo")
    store = ProjectStore("demo", base)
    store.save_crawl(Crawl(project="demo", id="crawl_1", status=CrawlStatus.STOPPED_BOUND,
                           stop_reason="max_actions", screens=1, issues=1))
    store.add_crawl_issue(CrawlIssue(crawl_id="crawl_1", project="demo", kind=IssueKind.NETWORK,
                                     node_id="n1", detail=f"{API} -> 502"))
    t0 = datetime(2026, 10, 21, tzinfo=UTC)
    store.save_run(Run(id="run_1", project="demo", case_ids=["c1"], started_at=t0,
                       finished_at=t0 + timedelta(seconds=9)))
    store.save_verdict("run_1", Verdict(run_id="run_1", case_id="c1", result=Result.FAIL,
                                        failures=[Failure(criterion_id="k", reason="boom")]))
    return base


def _member(email: str, perms: list[str]) -> TestClient:
    uid = accounts.signup(email, PASSWORD).id
    accounts.set_user_groups(uid, [groups.create_group(f"g-{email}", perms).id])
    return login(email)


def _editor() -> TestClient:
    return _member("editor@team.test", ["project.view@all", "project.edit@all",
                                        "report.view@all"])


def _viewer() -> TestClient:
    return _member("viewer@team.test", ["project.view@all", "report.view@all"])


def _first_key(page: str) -> str:
    return re.search(r"name='finding' value='([0-9a-f]{16})'", page).group(1)  # type: ignore[union-attr]


def _mark(who: TestClient, key: str, verdict: str, nxt: str = "/projects/demo/crawls/crawl_1"):
    return who.post("/projects/demo/bench/marks",
                    data={"finding": key, "verdict": verdict, "next": nxt})


# -- C1: marks on the crawl page and the run page ------------------------------------------

def test_c1_an_editor_marks_a_crawl_finding_real_and_the_fp_rate_follows(root: Path) -> None:
    who = _editor()
    page = who.get("/projects/demo/crawls/crawl_1").text
    assert "Mark real bug" in page and "Mark false positive" in page and "unadjudicated" in page
    resp = _mark(who, _first_key(page), "false_positive")
    assert resp.status_code == 303 and resp.headers["location"] == "/projects/demo/crawls/crawl_1"
    after = who.get("/projects/demo/crawls/crawl_1").text
    assert "Undo mark" in after and "Mark real bug" not in after
    store = ProjectStore("demo", root)
    bench_from_run(store, "demo", "run_1", crawl_ids=["crawl_1"])
    key_502 = next(bench_marks.finding_key(f) for f in store.list_bench_trials(CORPUS)[0].findings
                   if "502" in f.text)
    assert key_502 == _first_key(page)  # the page's key is the trial's key
    col = check.build_comparison(store, "demo").autotester
    assert (col.adjudicated_false_positives, col.adjudicated_real) == (1, 0)
    assert col.false_positive_rate.value == 1.0 and col.unadjudicated == 1  # the run's FAIL
    assert check.main(["demo", "--root", str(root)]) == 0


def test_c1_an_editor_marks_a_run_finding_and_undoes_it(root: Path) -> None:
    who = _editor()
    page = who.get("/projects/demo/runs/run_1").text
    assert "boom" in page and "Mark real bug" in page
    key = _first_key(page)
    assert _mark(who, key, "real", "/projects/demo/runs/run_1").status_code == 303
    marks = bench_marks.load_marks(ProjectStore("demo", root), CORPUS).marks
    assert marks[key].verdict == "real" and marks[key].marked_by == "editor@team.test"
    assert "Undo mark" in who.get("/projects/demo/runs/run_1").text
    assert _mark(who, key, "clear", "/projects/demo/runs/run_1").status_code == 303
    assert bench_marks.load_marks(ProjectStore("demo", root), CORPUS).marks == {}
    assert "Mark real bug" in who.get("/projects/demo/runs/run_1").text


def test_c1_a_view_only_account_sees_the_ruling_without_controls_and_cannot_mark(
        root: Path) -> None:
    editor = _editor()
    key = _first_key(editor.get("/projects/demo/crawls/crawl_1").text)
    _mark(editor, key, "real")
    viewer = _viewer()
    for url in ("/projects/demo/crawls/crawl_1", "/projects/demo/runs/run_1"):
        page = viewer.get(url).text
        assert "read-only" in page and "Mark real bug" not in page and "Undo mark" not in page
        assert "name='finding'" not in page
    assert "real bug" in viewer.get("/projects/demo/crawls/crawl_1").text
    refused = _mark(viewer, key, "false_positive")
    assert refused.status_code == 403
    assert bench_marks.load_marks(ProjectStore("demo", root), CORPUS).marks[key].verdict == "real"


def test_c1_anonymous_and_cross_origin_marks_are_refused_and_nothing_is_written(
        root: Path) -> None:
    editor = _editor()
    key = _first_key(editor.get("/projects/demo/crawls/crawl_1").text)
    assert _mark(client(), key, "real").status_code in (302, 303, 401, 403)
    cross = editor.post("/projects/demo/bench/marks", headers={"origin": "https://evil.test"},
                           data={"finding": key, "verdict": "real"})
    assert cross.status_code == 403
    assert bench_marks.load_marks(ProjectStore("demo", root), CORPUS).marks == {}


@pytest.mark.parametrize("data", [
    {"finding": "nothex", "verdict": "real"},
    {"finding": "0123456789abcdef", "verdict": "maybe"},
    {"verdict": "real"},
])
def test_c1_a_malformed_mark_is_a_400_and_writes_nothing(root: Path, data: dict) -> None:
    assert _editor().post("/projects/demo/bench/marks", data=data).status_code == 400
    assert not ProjectStore("demo", root).paths.bench_marks(CORPUS).exists()


def test_c1_simultaneous_marks_over_http_all_stored_and_none_errors(root: Path) -> None:
    who = _editor()
    keys = [f"{i:016x}" for i in range(24)]
    with ThreadPoolExecutor(max_workers=24) as pool:
        assert {_.status_code for _ in pool.map(lambda k: _mark(who, k, "real"), keys)} == {303}
    assert set(bench_marks.load_marks(ProjectStore("demo", root), CORPUS).marks) == set(keys)


def test_c1_an_off_site_next_is_ignored(root: Path) -> None:
    who = _editor()
    key = _first_key(who.get("/projects/demo/crawls/crawl_1").text)
    for nxt in ("https://evil.test/x", "//evil.test", "/projects/other/runs/x"):
        resp = _mark(who, key, "real", nxt)
        assert resp.headers["location"] == "/projects/demo/bench"


# -- C2: the private answer list ----------------------------------------------------------

def _upload(who: TestClient, raw: bytes, name: str = "list.json"):
    return who.post("/projects/demo/bench/atomic-list", files={"atomic_list": (name, raw)})


def test_c2_an_editor_uploads_the_list_it_is_stored_privately_and_its_hash_is_pinned(
        root: Path) -> None:
    who = _editor()
    resp = _upload(who, LIST_BYTES)
    assert resp.status_code == 303 and resp.headers["location"] == "/projects/demo/bench"
    digest = hashlib.sha256(LIST_BYTES).hexdigest()
    stored = root / ".work" / "ceo-bench" / "demo" / "atomic-list.json"
    assert stored.read_bytes() == LIST_BYTES
    pin = bench_inputs.load_pin("demo", root)
    assert pin is not None and pin.sha256 == digest and pin.items == 2
    assert pin.pinned_by == "editor@team.test"
    atomic, pinned_hash = bench_inputs.load_pinned_list("demo", root)
    assert pinned_hash == digest and [i.id for i in atomic.items] == ["A1", "A2"]
    page = who.get("/projects/demo/bench").text
    assert digest in page and "2 atomic findings" in page
    assert "A1" not in page and "state_after" not in page  # the rows are never shown back


def test_c2_the_list_is_never_served_and_the_repo_ignores_it(root: Path) -> None:
    who = _editor()
    _upload(who, LIST_BYTES)
    for url in ("/projects/demo/bench/atomic-list", "/.work/ceo-bench/demo/atomic-list.json",
                "/projects/demo/bench/atomic-list.json"):
        assert who.get(url).status_code in (404, 405)
    ignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert re.search(r"^/?\.work/?$", ignore, re.M)


def test_c2_a_view_only_account_cannot_upload_and_sees_no_form(root: Path) -> None:
    viewer = _viewer()
    page = viewer.get("/projects/demo/bench").text
    assert "type='file'" not in page and "needs permission to edit" in page
    assert _upload(viewer, LIST_BYTES).status_code == 403
    assert bench_inputs.load_pin("demo", root) is None


@pytest.mark.parametrize("raw", [
    b"", b"not json", b'{"items": []}',
    json.dumps({"items": [{"id": "A1", "priority": "P0", "technique": "inbox",
                           "text": "CEO-SECRET-FINDING-TEXT"}]}).encode(),
    json.dumps({"items": [{"id": "A1", "priority": "P9", "technique": "inbox"}]}).encode(),
    json.dumps({"items": [{"id": "A1", "priority": "P0", "technique": "inbox"}] * 2}).encode(),
])
def test_c2_a_bad_list_is_refused_without_echoing_its_content_and_nothing_is_stored(
        root: Path, raw: bytes) -> None:
    resp = _upload(_editor(), raw)
    assert resp.status_code == 400 and "CEO-SECRET-FINDING-TEXT" not in resp.text
    assert bench_inputs.load_pin("demo", root) is None
    assert not (root / ".work" / "ceo-bench" / "demo" / "atomic-list.json").exists()


def test_c2_an_oversize_list_is_refused_413_without_the_body_being_spooled(
        root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    who = _editor()  # sign in first: the login route itself reads a form
    monkeypatch.setattr("starlette.requests.Request.form", lambda *_a, **_k: pytest.fail("spool"))
    assert _upload(who, b" " * (bench_inputs.MAX_BYTES + 1)).status_code == 413
    assert _upload(who, LIST_BYTES, name="list.exe").status_code == 400  # name vetted first
    assert who.post("/projects/demo/bench/atomic-list", data={"o": "x"}).status_code == 400
    assert bench_inputs.load_pin("demo", root) is None
    assert not list((root / ".work" / "uploads").rglob("*.part"))  # staging removed


def test_c2_a_second_upload_replaces_the_list_and_records_the_old_hash(root: Path) -> None:
    who = _editor()
    _upload(who, LIST_BYTES)
    newer = json.dumps({"items": [{"id": "B1", "priority": "P2", "technique": "payment"}]}).encode()
    _upload(who, newer)
    pin = bench_inputs.load_pin("demo", root)
    assert pin is not None and pin.sha256 == hashlib.sha256(newer).hexdigest()
    assert pin.replaced_sha256 == [hashlib.sha256(LIST_BYTES).hexdigest()]


def test_c2_a_stored_list_edited_after_pinning_no_longer_loads(root: Path) -> None:
    _upload(_editor(), LIST_BYTES)
    path = root / ".work" / "ceo-bench" / "demo" / "atomic-list.json"
    path.write_bytes(LIST_BYTES + b" ")
    with pytest.raises(bench_inputs.ListRefused, match="no longer matches"):
        bench_inputs.load_pinned_list("demo", root)


# -- C3: labels, no external request, navigation ------------------------------------------

def test_c3_every_new_control_has_a_visible_label_and_no_page_loads_anything_external(
        root: Path) -> None:
    who = _editor()
    pages = [who.get(u).text for u in ("/projects/demo/bench", "/projects/demo/crawls/crawl_1",
                                       "/projects/demo/runs/run_1")]
    bench = pages[0]
    assert re.search(r"<label for='atomic-list-file'>[^<]+</label>", bench)
    assert "id='atomic-list-file'" in bench
    for page in pages[1:]:
        for form in re.findall(r"<form[^>]*bench/marks.*?</form>", page, re.S):
            assert re.search(r"<button[^>]*>[A-Z][^<]+</button>", form)  # text on every button
    for page in pages:  # the shared theme head is not ours; everything in <main> is
        assert not re.search(r"(?:src|href|action)=['\"]https?://", page.split("<main>", 1)[1])


def test_c3_the_sidebar_and_project_page_link_to_the_benchmark_inputs(root: Path) -> None:
    who = _editor()
    for url in ("/projects/demo", "/projects/demo/crawls/crawl_1", "/projects/demo/bench"):
        page = who.get(url).text
        assert "class='sidebar-sub' href='/projects/demo/bench'" in page, url
    assert "href='/projects/demo/bench'>" in who.get("/projects/demo").text
    assert who.get("/projects/demo/bench").status_code == 200


def test_c3_a_view_only_account_can_open_the_page_and_an_unknown_project_is_a_404(
        root: Path) -> None:
    viewer = _viewer()
    assert viewer.get("/projects/demo/bench").status_code == 200
    assert viewer.get("/projects/nope/bench").status_code == 404


def test_c3_finding_text_is_escaped_on_the_marking_card(root: Path) -> None:
    store = ProjectStore("demo", root)
    store.add_crawl_issue(CrawlIssue(
        crawl_id="crawl_1", project="demo", kind=IssueKind.CONSOLE, node_id="n1",
        detail="error: <script>alert(1)</script>"))
    page = _editor().get("/projects/demo/crawls/crawl_1").text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page
