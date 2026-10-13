"""One production rule on every path that acts on a live target (D-088, cycle 2 of
approval-prod-gate): `core.consent.require_project_approval` is the single function.

For each path: a production project refuses a derived / unsigned / `production:false` /
other-target row with a named reason, accepts a valid human production row, and a
non-production project is unaffected. Plus the done_check key rule and stop_reason hygiene.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from test_approval_prod_gate import _crawl, _load_script, _prod_project
from test_approval_prod_gate import _row as prod_row

from autotester.agents import guards
from autotester.core.consent import ApprovalRequired, require_project_approval
from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import Action, ApprovalKind, CaseClass, CaseKind
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.stages import adversarial, explore_summary, run_launcher
from autotester.stages.orchestrate_gate import release_preflight
from autotester.stages.run_launcher import LaunchRefused
from autotester.store.project_store import ProjectStore

BASE = "https://shop.test/"
BOUNDS = CrawlBounds()
BAD = ("derived", "unsigned", "production_false", "other_target")
NAMES = ("helper", "crawl_guard", "case_guard", "release", "adversarial", "ui_case_run")
KINDS = {"helper": ApprovalKind.CRAWL, "crawl_guard": ApprovalKind.CRAWL,
         "case_guard": ApprovalKind.LIVE_CASE, "release": ApprovalKind.LIVE_CASE,
         "adversarial": ApprovalKind.ADVERSARIAL, "ui_case_run": ApprovalKind.LIVE_CASE}


def _project(production: bool) -> Project:
    return Project(slug="demo", name="Demo", base_url=BASE, allowed_domains=["shop.test"],
                   production=production)


def _row(kind: ApprovalKind, variant: str = "good") -> RunApproval:
    row = RunApproval(
        project="demo", run_kind=kind,
        target="https://elsewhere.test/" if variant == "other_target" else BASE,
        scope="t", max_actions=1000, max_probes=1000, wall_clock_s=100_000.0,
        granted_by="account-derived:D-068" if variant == "derived" else "Umesh",
        granted_at="2026-10-13", expires_at="2099-01-01",
        production=variant != "production_false")
    return row if variant == "unsigned" else row.sign()


def _case() -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="t", steps=[Step(order=0, action=Action.CLICK, target="#go")])


def _store(tmp_path: Path, rows: list[RunApproval]) -> ProjectStore:
    store = ProjectStore("demo", tmp_path)
    for row in rows:
        store.add_approval(row)
    return store


def _ctx(store: ProjectStore, approval: RunApproval) -> SimpleNamespace:
    scope = SimpleNamespace(project="demo", run_id="r1", approval_id=approval.id,
                            max_actions=1, wall_clock_s=10.0, plans=[])
    return SimpleNamespace(release_scope=scope, run_id="r1", store=store)


def _run_path(name: str, tmp_path: Path, project: Project, rows: list[RunApproval]) -> None:
    """Drive one real path; raises `ApprovalRequired` on refusal."""
    if name == "helper":
        require_project_approval(rows, project=project, kind=ApprovalKind.CRAWL,
                                 target=BASE, actions=5)
    elif name == "crawl_guard":
        guards.crawl_approval(_store(tmp_path, rows), project, BOUNDS)
    elif name == "case_guard":
        guards.live_case_approval(_store(tmp_path, rows), project, _case())
    elif name == "release":
        release_preflight(project, _ctx(_store(tmp_path, rows), rows[0]))
    elif name == "adversarial":
        adversarial._gate(
            project=project, endpoint=BASE, sets=[], planned=1, approvals=rows,
            redactor=SimpleNamespace(assert_clean=lambda text: None), wall_clock_s=10.0,
            production=False, now=None)
    else:  # the UI case-run launcher gate
        try:
            run_launcher.require_live_case_approval(
                project, _store(tmp_path, rows), [_case()])
        except LaunchRefused as exc:
            assert exc.status == 403
            raise ApprovalRequired(exc.reason) from None


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("variant", BAD)
def test_production_project_refuses_a_bad_row_on_every_path(
        tmp_path: Path, name: str, variant: str) -> None:
    with pytest.raises(ApprovalRequired) as exc:
        _run_path(name, tmp_path, _project(True), [_row(KINDS[name], variant)])
    assert "refusing to start" in str(exc.value)


@pytest.mark.parametrize("name", NAMES)
def test_production_project_accepts_a_valid_human_production_row(
        tmp_path: Path, name: str) -> None:
    _run_path(name, tmp_path, _project(True), [_row(KINDS[name])])  # must not raise


@pytest.mark.parametrize("name", NAMES)
def test_non_production_project_is_unaffected(tmp_path: Path, name: str) -> None:
    _run_path(name, tmp_path, _project(False), [_row(KINDS[name], "production_false")])


def test_refusals_name_the_reason_for_derived_and_production_false() -> None:
    derived = _row(ApprovalKind.CRAWL, "derived")
    plain = _row(ApprovalKind.CRAWL, "production_false")
    with pytest.raises(ApprovalRequired) as exc:
        require_project_approval([derived, plain], project=_project(True),
                                 kind=ApprovalKind.CRAWL, target=BASE)
    text = str(exc.value)
    assert "D-088" in text and derived.id in text and plain.id in text


def test_hand_edited_scope_naming_a_non_production_row_does_not_pass_release(
        tmp_path: Path) -> None:
    store = _store(tmp_path, [_row(ApprovalKind.LIVE_CASE),
                              _row(ApprovalKind.LIVE_CASE, "production_false")])
    good, bad = store.list_approvals()
    with pytest.raises(ApprovalRequired):
        release_preflight(_project(True), _ctx(store, bad))
    release_preflight(_project(True), _ctx(store, good))


# -- check_crawl_approval.py: a production project needs the key, so the signature is verified

def test_done_check_fails_closed_for_production_without_the_key(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    store.add_approval(prod_row(project, production=True))
    _crawl(tmp_path, project, store)
    store.save_project(project)
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY", raising=False)
    assert _load_script(tmp_path, monkeypatch).main() == 1
    out = capsys.readouterr().out
    assert "AUTOTESTER_APPROVAL_KEY" in out and "cannot be verified" in out


def test_done_check_fails_for_production_with_a_forged_signature(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    project = _prod_project()
    store = ProjectStore("demo", tmp_path)
    row = prod_row(project, production=True)
    _crawl(tmp_path, project, _with(store, row))
    forged = row.model_copy(update={"signature": "0" * 64})
    path = store.paths.dir / "approvals.jsonl"
    path.write_text(forged.model_dump_json() + "\n", encoding="utf-8")
    store.save_project(project)
    assert _load_script(tmp_path, monkeypatch).main() == 1
    capsys.readouterr()


def _with(store: ProjectStore, row: RunApproval) -> ProjectStore:
    store.add_approval(row)
    return store


# -- CrawlSummary.stop_reason carries a code and a short URL-free detail only

@pytest.mark.parametrize("raw,code", [
    ("max_actions", "max_actions"),
    ("abandoned visits: aborted_error (https://shop.test/orders/42?token=abc)",
     "abandoned_visits"),
    ("could not open base_url -- net::ERR at https://shop.test/secret/page",
     "seed_unreachable"),
    ("Dear Alice Smith, your balance is 4,200", "other"),
])
def test_stop_reason_is_a_code_with_a_short_url_free_detail(raw: str, code: str) -> None:
    out = explore_summary.safe_stop_reason(raw)
    assert out is not None and out.split(":")[0] == code
    assert "http" not in out and "/secret" not in out and "token" not in out
    assert len(out) <= 100


def test_stop_reason_none_stays_none() -> None:
    assert explore_summary.safe_stop_reason(None) is None
    assert explore_summary.safe_stop_reason("") is None
