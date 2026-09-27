"""Pure-logic pieces of scripts/regression_proof.py. Contract:
qa/contracts/regression-proof.md. The actual proof (a real headed browser
against a real local fixture server, a real judge, a real regression injected
and reverted) is not a live-network-independent unit test by nature -- see
qa/manifests/t110-regression-proof.md for that real run's cited evidence.
These tests cover the parts that don't need a browser or a live judge call.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import regression_proof as rp

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.store.project_store import ProjectStore

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "regression_site"


def test_fixture_files_exist() -> None:
    assert (FIXTURE_DIR / "index.html").exists()
    assert (FIXTURE_DIR / "login.html").exists()
    assert (FIXTURE_DIR / "login.broken.html").exists()


def test_good_fixture_checks_the_real_password() -> None:
    text = (FIXTURE_DIR / "login.html").read_text(encoding="utf-8")
    assert "pass123" in text


def test_broken_fixture_checks_a_different_password() -> None:
    good = (FIXTURE_DIR / "login.html").read_text(encoding="utf-8")
    broken = (FIXTURE_DIR / "login.broken.html").read_text(encoding="utf-8")
    assert "password === 'pass123'" in good
    assert "password === 'pass124'" in broken
    assert "password === 'pass123'" not in broken


def test_build_cases_returns_login_and_homepage() -> None:
    cases = rp.build_cases("regression-demo", "http://127.0.0.1:9")
    assert len(cases) == 2
    assert cases[0].kind is CaseKind.BEST
    assert cases[1].kind is CaseKind.BEST
    login_targets = [s.target for s in cases[0].steps]
    assert any("login.html" in t for t in login_targets)
    assert any(s.action is Action.FILL for s in cases[0].steps)


def test_make_rubric_uses_a_stable_short_criterion_id() -> None:
    """A prior real run showed the judge sometimes invents a criterion id
    (e.g. "login_success_text") instead of using a generic one like "text" --
    grade.py's self-consistency check correctly downgraded that to
    INCONCLUSIVE. A short, explicitly-pinned id ("c1") with an instruction to
    use it exactly reduced this to zero across repeated real runs."""
    case = rp.build_cases("regression-demo", "http://127.0.0.1:9")[0]
    rubric = rp.make_rubric(case, "Login successful")
    assert rubric.criteria[0].id == "c1"
    assert "c1" in rubric.criteria[0].text


def test_rerunning_on_a_new_port_keeps_one_case_per_journey(tmp_path: Path) -> None:
    """AT-434, found in a live browser: the demo's cases.jsonl held 44 cases, 2 titles
    x 22 runs. A case id covers its steps, and every step target carries the fixture
    server's RANDOM port, so each run minted two new ids and `add_case`'s idempotency
    never fired. Three runs on three ports must still leave exactly two cases."""
    store = ProjectStore("regression-demo", tmp_path)
    for port in (41001, 41002, 41003):
        seated = rp.seat_demo_cases(store, rp.build_cases("regression-demo",
                                                          f"http://127.0.0.1:{port}"))

    cases = store.list_cases()
    assert sorted(c.title for c in cases) == ["Homepage loads", "Login with correct credentials"]
    assert {c.id for c in cases} == {c.id for c in seated}, "the LATEST port's cases are kept"
    assert all("41003" in c.steps[0].target for c in cases)


def test_seating_leaves_unrelated_cases_alone(tmp_path: Path) -> None:
    """Only a case for the same journey (flow and title) is replaced; a human-added
    case in the same project, or a demo title under another flow, is not the demo's."""
    store = ProjectStore("regression-demo", tmp_path)
    mine = Case(project="regression-demo", flow_id="flow_login", kind=CaseKind.WORST,
                case_class=CaseClass.AUTH_WRONG_CREDS, title="Login with a wrong password",
                steps=[Step(order=1, action=Action.NAVIGATE, target="http://127.0.0.1:9/login.html")])
    other_flow = Case(project="regression-demo", flow_id="flow_other", kind=CaseKind.BEST,
                      case_class=CaseClass.HAPPY, title="Homepage loads",
                      steps=[Step(order=1, action=Action.NAVIGATE, target="http://127.0.0.1:9/")])
    store.add_case(mine)
    store.add_case(other_flow)

    rp.seat_demo_cases(store, rp.build_cases("regression-demo", "http://127.0.0.1:41001"))
    rp.seat_demo_cases(store, rp.build_cases("regression-demo", "http://127.0.0.1:41002"))

    ids = {c.id for c in store.list_cases()}
    assert mine.id in ids and other_flow.id in ids
    assert len(ids) == 4


def test_bench_trial_seats_the_same_demo_cases_the_same_way() -> None:
    """bench_trial.py writes the same project; if it kept its own `add_case` loop the
    duplicates would simply come back from the other script."""
    import inspect

    import bench_trial

    assert bench_trial.seat_demo_cases is rp.seat_demo_cases
    main = inspect.getsource(bench_trial.main)  # the import alone would not stop a bare loop
    assert "seat_demo_cases(" in main and "add_case(" not in main


def test_swapped_fixture_copies_the_broken_content_in(tmp_path: Path) -> None:
    good = tmp_path / "login.html"
    broken = tmp_path / "login.broken.html"
    good.write_text("GOOD", encoding="utf-8")
    broken.write_text("BROKEN", encoding="utf-8")

    with rp._swapped_fixture(good, broken):
        assert good.read_text(encoding="utf-8") == "BROKEN"

    assert good.read_text(encoding="utf-8") == "GOOD"


def test_swapped_fixture_restores_the_tracked_file_even_when_the_body_raises(
        tmp_path: Path) -> None:
    """AT-560: scripts/regression_proof.py mutates a TRACKED fixture (login.html)
    for the duration of the AFTER run. If that run raises partway -- a browser
    crash, a judge call failing, anything -- the fixture must still come back to
    its good state, never be left broken on disk. Uses a throwaway tmp_path copy,
    never the real tests/fixtures/regression_site/ files."""
    good = tmp_path / "login.html"
    broken = tmp_path / "login.broken.html"
    good.write_text("GOOD", encoding="utf-8")
    broken.write_text("BROKEN", encoding="utf-8")

    with pytest.raises(RuntimeError, match="boom"), rp._swapped_fixture(good, broken):
        assert good.read_text(encoding="utf-8") == "BROKEN"
        raise RuntimeError("boom")

    assert good.read_text(encoding="utf-8") == "GOOD", \
        "the tracked fixture must be restored even after the body raised"


def test_no_cache_handler_overrides_end_headers() -> None:
    """A prior real run showed the persistent browser profile served a stale,
    cached login.html on the AFTER run even after the file changed on disk --
    a plain http.server sends no cache-control headers at all. This handler
    exists specifically to defeat that."""
    import http.server

    assert issubclass(rp._NoCacheHandler, http.server.SimpleHTTPRequestHandler)
    assert rp._NoCacheHandler.end_headers is not http.server.SimpleHTTPRequestHandler.end_headers
