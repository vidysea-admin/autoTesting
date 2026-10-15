"""T-179a fix cycle 1: AL3(c) decided fail-closed at the tool gate, plus the dispatch hardening
(F2 typed errors, F3 nothing unreleasable on disk, F4 real values + size cap) and F5.

Every refused case asserts the same three things from the tool's own result: a typed refusal,
zero sessions opened, zero `execute.run_case` calls. Offline; fake canary secrets only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_agent_tools import (
    BASE,
    RAW,
    Spies,
    _case,
    _ctx,
    _go,
    _grant,
    spies,  # noqa: F401  (the fixture the `spy` wrapper below asks for)
)

from autotester.agents import tools
from autotester.schema.agent_layer import RefusalClass
from autotester.schema.enums import Action, ApprovalKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.portal_persona import PortalPersona


@pytest.fixture
def spy(spies: Spies) -> Spies:  # noqa: F811  (the shared fixture, re-exposed under a new name)
    return spies


RO, TA, AW = WritePolicy.READ_ONLY, WritePolicy.TEST_ACCOUNT, WritePolicy.ALLOW_WRITES
A = Action
HOME = f"{BASE}/reports"


def _run(tmp: Path, spy: Spies, policy: WritePolicy, steps: list[Step],
         login: bool = False) -> tuple[Any, Any]:
    ctx = _ctx(tmp, spy, policy)
    _grant(ctx.store, ApprovalKind.LIVE_CASE)
    case = ctx.store.add_case(_case(steps))
    if login:
        ctx.project = ctx.project.model_copy(update={"login_case_id": case.id})
    return ctx, _go(ctx, "run_case", {"case_id": case.id})


def _one(action: Action, target: str = "x", value: str | None = None) -> list[Step]:
    return [Step(order=1, action=action, target=target, value=value)]


_CLICKS = ["Save", "Save changes", "Place order", "Confirm", "Apply now", "Register", "Sign up",
           "Add to cart", "Sign in", "Delete account", "खाता हटाएं (delete)", "Log out"]
_NAVS = [f"{BASE}/account/delete?id=1&confirm=1", f"{BASE}/logout", f"{BASE}/reports?page=2",
         f"{BASE}/account/delete", "/reports", "Admin portal URL", "{{SECRET:APP_PASS}}",
         f"{BASE}/x/{{{{SECRET:APP_PASS}}}}"]
_REFUSED_RO: list[tuple[Action, str, str | None]] = (
    [(A.CLICK, t, None) for t in _CLICKS]
    + [(A.PRESS_KEY, "", None), (A.PRESS_KEY, "", "Enter"), (A.PRESS_KEY, "", "Delete"),
       (A.PRESS_KEY, "Search", "Tab")]
    + [(A.NAVIGATE, t, None) for t in _NAVS]
    + [(A.FILL, "Name", v) for v in ("", "   ", None, "Eve")]
    + [(A.SELECT, "Plan", "pro"), (A.SELECT, "Plan", None), (A.UPLOAD, "CV", "cv.pdf"),
       (A.FILL, "Password", "{{SECRET:APP_PASS}}")]  # a credential outside the login case
)


# -- AL3(c): every READ_ONLY step that can change state is refused from the tool's result -------
@pytest.mark.parametrize(("action", "target", "value"), _REFUSED_RO)
def test_read_only_refuses_each_state_changing_step(
        tmp_path: Path, spy: Spies, action: Action, target: str, value: str | None) -> None:
    _, out = _run(tmp_path, spy, RO, _one(action, target, value))
    assert not out.ok and out.refusal in (RefusalClass.WRITE_POLICY, RefusalClass.DESTINATION)
    assert "read_only" in out.summary
    assert spy.sessions == 0 and spy.count("run_case") == 0


_READS = [(A.NAVIGATE, HOME, None), (A.WAIT, "Reports", "500"), (A.ASSERT, "x", None),
          (A.BACK, "", None), (A.HOVER, "Reports", None), (A.SCROLL, "", "400"),
          (A.NAVIGATE, f"{BASE}/reports#top", None)]


@pytest.mark.parametrize(("action", "target", "value"), _READS)
def test_read_only_still_runs_reads(
        tmp_path: Path, spy: Spies, action: Action, target: str, value: str | None) -> None:
    _, out = _run(tmp_path, spy, RO, _one(action, target, value))
    assert out.ok and spy.sessions == 1 and spy.count("run_case") == 1


@pytest.mark.parametrize("policy", [RO, TA, AW])
@pytest.mark.parametrize("url", ["javascript:alert(1)", " javascript:alert(1)", "JAVASCRIPT:1",
                                 "data:text/html,x", "https://evil.test/x", "http://evil.test",
                                 "https://app.test.evil.test/", "https://u:p@app.test/",
                                 f"{BASE}\\@evil.test", "//evil.test/x"])
# ftp://app.test/x is not listed: the seam accepts it, so above READ_ONLY the guard does too
def test_off_domain_and_non_http_navigation_is_refused_under_every_policy(
        tmp_path: Path, spy: Spies, policy: WritePolicy, url: str) -> None:
    _, out = _run(tmp_path, spy, policy, _one(A.NAVIGATE, url))
    assert out.refusal is RefusalClass.DESTINATION and url not in out.summary
    assert spy.sessions == 0 and spy.count("run_case") == 0


# -- ALLOW_WRITES / TEST_ACCOUNT: D-098 still refuses account destruction -----------------------
@pytest.mark.parametrize(("action", "target", "value"), [
    (A.CLICK, "Save", None), (A.CLICK, "Delete account", None), (A.CLICK, "Place order", None),
    (A.FILL, "Name", "Eve"), (A.FILL, "Name", None), (A.FILL, "Name", ""),
    (A.SELECT, "Plan", "pro"), (A.UPLOAD, "CV", "cv.pdf"), (A.PRESS_KEY, "", "Delete"),
    (A.PRESS_KEY, "", None), (A.NAVIGATE, f"{BASE}/account/delete?id=1&confirm=1", None),
    (A.NAVIGATE, "{{SECRET:APP_PASS}}", None)])  # bare paths: test_agent_destination_seam.py
def test_allow_writes_refuses_nothing_the_account_may_do(
        tmp_path: Path, spy: Spies, action: Action, target: str, value: str | None) -> None:
    _, out = _run(tmp_path, spy, AW, _one(action, target, value))
    if target in ("Delete account", f"{BASE}/account/delete?id=1&confirm=1"):
        assert not out.ok and out.refusal is RefusalClass.WRITE_POLICY
        assert "account-destroying (policy)" in out.summary
        assert spy.sessions == 0 and spy.count("run_case") == 0
    else:
        assert out.ok and spy.sessions == 1 and spy.count("run_case") == 1


def test_allow_writes_keeps_the_existing_never_click_and_test_account_keeps_its_deny_list(
        tmp_path: Path, spy: Spies) -> None:
    _, out = _run(tmp_path, spy, AW, _one(A.CLICK, "Log out"))
    assert out.refusal is RefusalClass.WRITE_POLICY
    _, save = _run(tmp_path / "t1", spy, TA, _one(A.CLICK, "Save"))
    _, gone = _run(tmp_path / "t2", spy, TA, _one(A.CLICK, "Delete account"))
    assert save.ok and gone.refusal is RefusalClass.WRITE_POLICY


# -- the login carve-out: only the declared login case, only declared-key placeholders ---------
_SIGNIN = f"{BASE}/signin?next=/"


def _login(extra: list[Step] | None = None, user: str = "{{SECRET:APP_PASS}}") -> list[Step]:
    steps = [Step(order=1, action=A.NAVIGATE, target=_SIGNIN),
             Step(order=2, action=A.FILL, target="Email", value=user),
             Step(order=3, action=A.FILL, target="Password", value="{{SECRET:APP_PASS}}"),
             Step(order=4, action=A.CLICK, target="Sign in")]
    return steps + (extra or [])


def test_the_declared_login_case_signs_in_under_read_only(tmp_path: Path, spy: Spies) -> None:
    _, out = _run(tmp_path, spy, RO, _login(), login=True)
    assert out.ok and spy.count("run_case") == 1
    enter = [*_login()[:3], Step(order=4, action=A.PRESS_KEY, target="", value="Enter")]
    _, out = _run(tmp_path / "e", spy, RO, enter, login=True)
    assert out.ok


@pytest.mark.parametrize("name", ["not the declared login", "bad key", "literal", "no fill",
                                  "second submit", "other key", "delete", "mixed"])
def test_login_carve_out_is_narrow(tmp_path: Path, spy: Spies, name: str) -> None:
    steps, login = _login(), True
    if name == "not the declared login":
        login = False
    elif name == "bad key":
        steps = _login(user="{{SECRET:NOT_DECLARED}}")
    elif name == "literal":
        steps = _login(user="alice")
    elif name == "no fill":
        steps = [steps[0], steps[3]]
    elif name == "second submit":
        steps = _login([Step(order=5, action=A.CLICK, target="Confirm")])
    elif name == "other key":
        steps = _login([Step(order=5, action=A.PRESS_KEY, target="", value="Delete")])
    elif name == "delete":
        steps[3] = Step(order=4, action=A.CLICK, target="Delete account")
    else:
        steps = _login(user="{{SECRET:APP_PASS}}x")
    _, out = _run(tmp_path, spy, RO, steps, login=login)
    assert out.refusal is RefusalClass.WRITE_POLICY
    assert spy.sessions == 0 and spy.count("run_case") == 0


# -- F2: typed errors, scrubbed text, never an echoed name --------------------------------------
def test_a_stage_session_or_judge_failure_is_a_scrubbed_typed_refusal(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, _ = _run(tmp_path, spy, AW, _one(A.WAIT, "x"))
    case = ctx.store.add_case(_case(_one(A.WAIT, "y")))

    def boom(text: str) -> Any:
        def _raise(*_a: Any, **_k: Any) -> Any:
            raise RuntimeError(text)
        return _raise
    monkeypatch.setattr(tools.execute, "run_case", boom(f"login failed for {RAW}"))
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.refusal is RefusalClass.STAGE_ERROR and RAW not in out.model_dump_json()
    assert "RuntimeError" in out.summary
    monkeypatch.setattr(tools.execute, "run_case", boom(f"folded {RAW[::-1]} here"))
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.refusal is RefusalClass.SECRET and RAW[::-1] not in out.model_dump_json()
    ctx.open_session = boom(f"no browser {RAW}")
    assert _go(ctx, "run_case", {"case_id": case.id}).refusal is RefusalClass.STAGE_ERROR
    monkeypatch.setattr(tools.catalog, "catalog", boom(f"db down {RAW}"))
    assert _go(ctx, "get_catalog").refusal is RefusalClass.STAGE_ERROR


def _deep(n: int) -> Any:
    node: Any = "x"
    for _ in range(n):
        node = [node]
    return node


@pytest.mark.parametrize(("name", "args"), [
    ("run_case", []), ("run_case", "case"), ("run_case", None), ("run_case", 5),
    (["run_case"], {}), ({"a": 1}, {}), (None, {}), (b"run_case", {}),
    ("run_case", {"case_id": _deep(100_000)}), ("run_case", {1: "x"}),
    ("run_case", {"case_id": b"bytes"}), ("Zq9-not-a-tool", {}),
    ("run_case", {"case_id": {"a": 1}})])
def test_malformed_calls_return_typed_refusals_without_echoing_the_name(
        tmp_path: Path, spy: Spies, name: Any, args: Any) -> None:
    ctx = _ctx(tmp_path, spy)
    out = tools.dispatch(ctx, name, args)
    assert not out.ok and out.refusal in (RefusalClass.UNKNOWN_TOOL, RefusalClass.BAD_ARGUMENTS)
    assert "Zq9" not in out.model_dump_json() and spy.sessions == 0 and not spy.calls


# -- F3: nothing the release gate would refuse is ever written ----------------------------------
def test_a_folded_secret_in_a_stage_result_is_never_stored(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    from autotester.schema.enums import Outcome
    from autotester.schema.run import RawResult
    ctx, _ = _run(tmp_path, spy, AW, _one(A.WAIT, "x"))
    case = ctx.store.add_case(_case(_one(A.WAIT, "y")))
    ctx.run_id = "run-f3"
    leak = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error=f"saw {RAW[::-1]}")
    monkeypatch.setattr(tools.execute, "run_case", lambda c, s: leak)
    out = _go(ctx, "run_case", {"case_id": case.id})
    assert out.refusal is RefusalClass.SECRET and ctx.store.load_results("run-f3") == []
    run_dir = ctx.store.paths.run_dir("run-f3")
    files = [p for p in run_dir.rglob("*") if p.is_file()] if run_dir.exists() else []
    assert all(RAW[::-1] not in p.read_text("utf-8", "ignore") for p in files)


# -- F4: real values, not their repr; size cap ahead of the scan --------------------------------
@pytest.mark.parametrize("sep", ["\t", "\n", "​", "­"])
def test_a_secret_split_by_whitespace_or_invisible_characters_is_refused(
        tmp_path: Path, spy: Spies, sep: str) -> None:
    ctx = _ctx(tmp_path, spy)
    out = _go(ctx, "get_catalog", {"note": RAW[:6] + sep + RAW[6:]})
    assert out.refusal is RefusalClass.SECRET and not spy.calls


def test_oversized_arguments_are_refused_before_any_secret_scan(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _ctx(tmp_path, spy)
    scanned: list[int] = []
    monkeypatch.setattr(ctx.secrets, "guard_prompt", lambda t: scanned.append(len(t)) or t)
    out = _go(ctx, "run_case", {"case_id": "a" * 2_000_000})
    assert out.refusal is RefusalClass.BAD_ARGUMENTS and max(scanned, default=0) < 100_000


# -- F5: get_persona really calls the wrapped reader ---------------------------------------------
def test_get_persona_calls_the_wrapped_reader(
        tmp_path: Path, spy: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _ctx(tmp_path, spy)
    ctx.store.save_portal_persona(PortalPersona(project="demo"))
    real, calls = ctx.store.load_portal_persona, []
    monkeypatch.setattr(ctx.store, "load_portal_persona", lambda: calls.append(1) or real())
    out = _go(ctx, "get_persona")
    assert out.ok and out.artifact_ref == "persona:demo" and calls == [1]


# -- D-086 HG-1: benign clicks run under READ_ONLY; everything else keeps its guard -------------
@pytest.mark.parametrize("name", ["Home", "Next", "Search", "Reports", "Details", "Close"])
def test_read_only_runs_a_benign_click(tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.ok and spy.sessions == 1 and spy.count("run_case") == 1


@pytest.mark.parametrize("name", ["Delete account", "Log out", "Sign out", "Submit", "Save",
                                  "Place order", "Sign in", ""])
def test_read_only_still_refuses_a_destructive_or_commit_click(
        tmp_path: Path, spy: Spies, name: str) -> None:
    _, out = _run(tmp_path, spy, RO, _one(A.CLICK, name))
    assert out.refusal is RefusalClass.WRITE_POLICY and "read_only" in out.summary
    assert spy.sessions == 0 and spy.count("run_case") == 0


def test_the_click_relaxation_does_not_unlock_the_other_write_steps(
        tmp_path: Path, spy: Spies) -> None:
    for i, step in enumerate([(A.FILL, "Name", "Eve"), (A.SELECT, "Plan", "pro"),
                              (A.UPLOAD, "CV", "cv.pdf"), (A.PRESS_KEY, "", "Enter")]):
        _, out = _run(tmp_path / f"s{i}", spy, RO, _one(*step))
        assert out.refusal is RefusalClass.WRITE_POLICY
    assert spy.sessions == 0 and spy.count("run_case") == 0
