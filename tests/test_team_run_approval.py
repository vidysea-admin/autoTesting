"""TT6 (CRITICAL): the same gate as a schedule -- a credential-derived approval, or a refusal
that names the state and leaves no trace.

Scenarios: a Developer and an Admin each press Test on (1) a project that declares no
credential, (2) one whose credential has no value, (3) one whose credential is provisioned.
(1) and (2) are refused with the state named, nothing reaches the browser or grader, no run
directory or queue entry exists and no credential value appears; (3) is queued under the
approval minted from its credential, which carries its own bounds.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from auth_harness import gate_on, team, user_id
from team_run_fakes import FakeQueue, listing, patch_run_world, runnable_project

from autotester.auth.access import set_owner
from autotester.core.consent import is_account_derived
from autotester.core.redact import Redactor
from autotester.schema.project import SecretRef
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_team_run

HTML = {"accept": "text/html"}
CANARY = "CANARY-other-credential-7c1e"
PROVISIONED_VALUE = "prov-account-value"


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = gate_on(tmp_path, monkeypatch)
    counters = patch_run_world(monkeypatch)
    users = team()
    queue = FakeQueue()
    monkeypatch.setattr(routes_team_run, "get_queue", lambda: queue)
    return root, users, counters, queue


def _fixtures(root: Path) -> dict[str, str]:
    """One project per credential state, all owned by the developer (the admin sees all)."""
    runnable_project(root, "nocred")                                   # no SecretRef, no grant
    store = runnable_project(root, "noval", credential="NOVAL_USER")   # declared, no value
    project = store.load_project()
    assert project is not None
    project.secrets.append(SecretRef(key="OTHER_KEY", domains=["noval.test"]))
    store.save_project(project)
    (root / ".env").write_text(f"OTHER_KEY={CANARY}\n", encoding="utf-8")
    runnable_project(root, "prov", credential="PROV_USER", value=PROVISIONED_VALUE)
    for slug in ("nocred", "noval", "prov"):
        set_owner(slug, user_id("dev@team.test"))
    return {"no SecretRef": "nocred", "no value": "noval", "provisioned": "prov"}


@pytest.mark.parametrize("who", ["dev", "admin"])
def test_an_uncredentialed_project_is_refused_naming_the_state_and_leaving_no_trace(
        world, who: str) -> None:
    root, users, counters, queue = world
    slugs = _fixtures(root)
    redactor = Redactor({"OTHER_KEY": CANARY, "PROV_USER": PROVISIONED_VALUE})
    for state, expect_status, words in (
            ("no SecretRef", 403, ("no_secretref", "no credential pair")),
            ("no value", 400, ("NOVAL_USER has no value", "Credentials page"))):
        before = listing(root)
        resp = users[who].post(f"/projects/{slugs[state]}/test", headers=HTML)
        assert resp.status_code == expect_status, (state, resp.text)
        for word in words:
            assert word in resp.text, (state, word)
        assert CANARY not in resp.text and PROVISIONED_VALUE not in resp.text
        assert redactor.scrub(resp.text) == resp.text
        assert listing(root) == before                        # no run dir, no approval row
        assert not (root / "projects" / slugs[state] / "runs").exists()
        assert queue.submitted == []
        assert counters.sessions == 0 and counters.graded == 0     # nothing reached the network


@pytest.mark.parametrize("who", ["dev", "admin"])
def test_a_provisioned_project_is_queued_under_the_approval_minted_from_its_credential(
        world, who: str) -> None:
    root, users, counters, queue = world
    slugs = _fixtures(root)
    resp = users[who].post(f"/projects/{slugs['provisioned']}/test", headers=HTML)
    assert resp.status_code == 303 and len(queue.submitted) == 1   # queued; the fake holds it
    rows = ProjectStore(slugs["provisioned"], root).list_approvals()
    assert len(rows) == 1 and is_account_derived(rows[0])         # derived from the credential
    assert rows[0].max_actions > 0 and rows[0].wall_clock_s > 0   # its own bounds, no extra brake
    assert counters.sessions == 0
