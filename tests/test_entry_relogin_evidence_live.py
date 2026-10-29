"""Checker B cycle-0 F1, on a REAL headless Chromium (loopback only): the login replay after a
relaunch of the lent session must not restart the screenshot counter, or the next ordinary cases
write `NN-step..png` at indexes the earlier ordinary cases already used and overwrite their
evidence. Real `BrowserSession`, `EntryBrowserPool`, `_run_normal_cases` and `run_case`; only the
grader is stubbed. Skipped when no Chromium binary is installed.
"""

from __future__ import annotations

import http.server
import threading
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

import autotester.ui.run_execution as rx
from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project, SecretRef
from autotester.schema.verdict import Verdict
from autotester.stages.execute import run_case


class _Site(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        page = f"<!doctype html><title>t</title><input id=i><h1>{self.path}</h1>"
        self.wfile.write(page.encode())


@pytest.fixture
def base_url() -> Iterator[str]:
    pytest.importorskip("playwright.sync_api")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Site)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()
    server.server_close()


def _case(case_id: str, steps: list[Step]) -> Case:
    return Case(id=case_id, project="rl", flow_id="f", kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title=case_id, steps=steps)


def test_a_login_replay_after_a_relaunch_does_not_overwrite_earlier_cases_screenshots(
    base_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    project = Project(slug="rl", name="rl", base_url=base_url, allowed_domains=["127.0.0.1"],
                      headed=False, secrets=[SecretRef(key="USER", domains=["127.0.0.1"])],
                      login_case_id="login")
    secrets = SecretStore(project, {"USER": "u"})
    login = _case("login", [Step(order=1, action=Action.NAVIGATE, target=base_url + "login"),
                            Step(order=2, action=Action.FILL, target="#i",
                                 value="{{SECRET:USER}}")])
    cases = [_case(f"p{n}", [Step(order=i, action=Action.NAVIGATE, target=f"{base_url}{n}{i}")
                             for i in (1, 2)]) for n in range(1, 5)]
    evidence: dict[str, list[str]] = {}
    closed = {"done": False}

    def graded(case, session, judge, run_id, store):
        if case.id == "p2" and not closed["done"]:  # the browser dies inside p2's last shot
            closed["done"] = True
            real = session.screenshot
            shots = {"n": 0}

            def shot(label, **kw):
                shots["n"] += 1
                if shots["n"] == 2:
                    session._context.close()
                return real(label, **kw)
            session.screenshot = shot
        result = run_case(case, session)
        session.__dict__.pop("screenshot", None)
        evidence.setdefault(case.id, []).extend(e.path for e in result.evidence
                                                if e.path.endswith(".png"))
        ok = result.outcome is not Outcome.ERRORED
        return result, Verdict(run_id="r", case_id=case.id, grader_provider="mock",
                               result=Result.PASS if ok else Result.INCONCLUSIVE)

    monkeypatch.setattr(rx, "_run_and_grade_resilient", graded)
    monkeypatch.setattr(rx, "grade_errored_result", lambda case, result, judge, run_id, store:
                        Verdict(run_id=run_id, case_id=case.id, grader_provider="mock",
                                result=Result.INCONCLUSIVE))
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    store = SimpleNamespace(save_result=lambda *_a: None, save_verdict=lambda *_a: None)
    budget = SimpleNamespace(check_start=lambda: None, check=lambda **_k: None,
                             remaining_ms=lambda r=None: int(r or 15000))
    judge = SimpleNamespace(trace=None)
    pool = rx._entry_pool(project, secrets, run_dir, "rl", judge, budget)
    try:
        session = pool.acquire(login)
        result, verdict = graded(login, session, judge, "r", store)
        pool.release(login, session, result, passed=verdict.result is Result.PASS)
        assert pool.lend() is session  # the fixture is real: a passed login is lent
        rx._run_normal_cases(cases, pool, project, secrets, run_dir,
                             ProjectPaths("rl", tmp_path), judge, "r", store, budget=budget)
    finally:
        pool.close()
    assert "p3" in evidence and "p4" in evidence  # both ran after the relaunch and the replay
    ordinary = [path for case in cases for path in evidence.get(case.id, [])]
    assert len(set(ordinary)) == len(ordinary), f"two cases share a screenshot path: {ordinary}"
    for path in ordinary:
        assert (run_dir / path).exists()
