"""AT-110: `RunApproval.id` is an UNKEYED content hash, so it detects a
careless edit but not a determined forger — a checker widened a 12-action
grant to 9999 with `production=True`, deleted the `id`, and `model_post_init`
minted a matching one (`is_intact: True`), and the widened crawl ran.

Closed per Umesh's HUMAN_GATE answer (`qa/gates/at110-approval-forgery.md`,
answered 2026-09-24, option 1): every `RunApproval` is now ALSO signed with an
HMAC keyed from `AUTOTESTER_APPROVAL_KEY` (repo-root `.env`, never committed —
see `.env.example`). This file replays AT-110's own repro and proves it is now
refused, proves the naive-edit case stays refused, and proves the new gate
fails CLOSED (never silently accepts) on a missing key, a legacy/unsigned row,
or a stale/forged signature.

Contract: qa/contracts/consent.md CN3.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.core.consent import ApprovalRequired, require_approval
from autotester.core.ids import SigningKeyMissing
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

runner = CliRunner()
TARGET = "https://www.vidysea.com/erp"
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def _granted(**overrides: object) -> RunApproval:
    """Unsigned. Callers sign explicitly, the way a real grant does."""
    fields: dict[str, object] = {
        "project": "erp", "run_kind": ApprovalKind.CRAWL, "target": TARGET,
        "scope": "read-only crawl", "max_actions": 12, "wall_clock_s": 900.0,
        "granted_by": "umesh", "granted_at": "2026-09-08", "expires_at": "2099-01-01",
    }
    fields.update(overrides)
    return RunApproval(**fields)  # type: ignore[arg-type]


def _require(approvals: list[RunApproval], **kw: object) -> RunApproval:
    args: dict[str, object] = {
        "project": "erp", "kind": ApprovalKind.CRAWL, "target": TARGET,
        "actions": 10, "wall_clock_s": 100.0,
    }
    args.update(kw)
    return require_approval(approvals, **args)  # type: ignore[arg-type]


# -- the happy path: a real signature verifies -------------------------------

def test_a_freshly_signed_approval_verifies_and_is_returned() -> None:
    granted = _granted().sign()
    assert granted.signature != ""
    assert granted.is_signed_and_verified is True
    assert _require([granted]).id == granted.id


# -- AT-110's own repro, replayed --------------------------------------------

def test_the_at110_forgery_repro_is_now_refused() -> None:
    """The checker's exact scenario (`qa/issues.jsonl` AT-110 evidence):
    rewrite a real 12-action grant with `max_actions=9999`,
    `wall_clock_s=99999`, `production=True`, and the `id` key REMOVED. Before
    this fix, `model_post_init` minted a matching id and the row was accepted
    (`is_intact: True`) — a 500-action crawl then ran on a 12-action grant.
    Now the forged row also carries no valid `signature`, so it is refused
    regardless of the id."""
    granted = _granted(max_actions=12, wall_clock_s=900.0).sign()
    forged = granted.model_dump(mode="json")
    del forged["id"]
    del forged["signature"]  # the forger does not know the key either
    forged["max_actions"] = 9999
    forged["wall_clock_s"] = 99999.0
    forged["production"] = True

    reloaded = RunApproval.model_validate(forged)
    assert reloaded.is_intact is True, "the forged id IS recomputed to match — AT-110's finding"
    assert reloaded.signature == ""

    with pytest.raises(ApprovalRequired) as exc:
        _require([reloaded], actions=500, wall_clock_s=300.0)
    assert "no signature" in str(exc.value)


def test_a_forged_row_carrying_the_stale_original_signature_is_also_refused() -> None:
    """A forger who knows `signature` exists, but not the key, can only replay
    the ORIGINAL signature — computed over the original bounds — which will
    not verify against the widened ones."""
    granted = _granted(max_actions=12).sign()
    forged = granted.model_dump(mode="json")
    del forged["id"]
    forged["max_actions"] = 9999  # signature left untouched: stale, not recomputed
    reloaded = RunApproval.model_validate(forged)
    assert reloaded.is_intact is True

    with pytest.raises(ApprovalRequired, match="does not verify"):
        _require([reloaded], actions=500, wall_clock_s=300.0)


def test_the_naive_edit_case_stays_refused() -> None:
    """CN3's original, still-working guarantee: an id left unchanged after an
    edit is caught before the signature is even checked."""
    granted = _granted(max_actions=10).sign()
    widened = granted.model_copy(update={"max_actions": 100_000})

    with pytest.raises(ApprovalRequired, match="edited after it was granted"):
        _require([widened], actions=50)


# -- legacy / unsigned rows ---------------------------------------------------

def test_a_legacy_approval_granted_before_signing_existed_is_refused_to_re_grant() -> None:
    """No `signature` key in the JSONL row at all (pydantic defaults it to
    ""). Per the gate: approvals granted before the key existed become
    unverifiable and must be re-granted — never auto-signed on load."""
    granted = _granted().sign()
    legacy = granted.model_dump(mode="json")
    del legacy["signature"]
    reloaded = RunApproval.model_validate(legacy)
    assert reloaded.is_intact is True
    assert reloaded.signature == ""

    with pytest.raises(ApprovalRequired) as exc:
        _require([reloaded])
    assert "re-grant" in str(exc.value)


def test_loading_a_legacy_row_never_auto_signs_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-signing on load would let the READER's key re-sign a forged row
    for the forger — the exact hole `RunApproval.sign()`'s docstring names.
    Loading a legacy row must not even attempt it: it must succeed with no
    key configured at all."""
    granted = _granted().sign()
    legacy = granted.model_dump(mode="json")
    del legacy["signature"]
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY", raising=False)

    reloaded = RunApproval.model_validate(legacy)  # must not raise SigningKeyMissing

    assert reloaded.signature == ""


# -- missing key: fail closed, both directions -------------------------------

def test_granting_without_a_key_refuses_with_an_actionable_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY", raising=False)

    with pytest.raises(SigningKeyMissing, match="AUTOTESTER_APPROVAL_KEY"):
        _granted().sign()


def test_verifying_without_a_key_refuses_even_a_validly_signed_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail CLOSED: a missing key must never read as "nothing to check, so
    accept". Sign while the key is present, then take it away — the exact
    sequence a rotated or deleted key produces."""
    granted = _granted().sign()
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY", raising=False)

    with pytest.raises(ApprovalRequired) as exc:
        _require([granted])
    assert "cannot verify" in str(exc.value)
    assert "AUTOTESTER_APPROVAL_KEY" in str(exc.value)


def test_the_grant_cli_refuses_without_a_key_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    monkeypatch.delenv("AUTOTESTER_APPROVAL_KEY", raising=False)
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))

    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", "https://demo.test",
        "--scope", "s", "--granted-by", "umesh", "--expires", TOMORROW,
    ])

    assert result.exit_code == 1
    assert "AUTOTESTER_APPROVAL_KEY" in result.output
    assert store.list_approvals() == [], "a refused grant must write nothing"


# -- the key value itself never leaks ----------------------------------------

def test_the_signing_key_value_never_appears_in_any_cli_output_or_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The KEY (not the signature it produces) must never be logged, printed,
    put in a prompt, or written to any artifact (CLAUDE.md "Credentials"; C5).
    Grant a real approval through the shipped CLI and check every surface it
    touches: stdout, the stored approval's own JSON, and the file on disk."""
    secret_key = "unit-test-signing-key-zzz111-not-a-real-secret"
    monkeypatch.setenv("AUTOTESTER_APPROVAL_KEY", secret_key)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))

    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", "https://demo.test",
        "--scope", "s", "--granted-by", "umesh", "--expires", TOMORROW,
    ])

    assert result.exit_code == 0, result.output
    assert secret_key not in result.output
    approval = store.list_approvals()[0]
    assert secret_key not in approval.model_dump_json()
    assert secret_key not in approval.signature
    on_disk = (tmp_path / "projects" / "demo" / "approvals.jsonl").read_text(encoding="utf-8")
    assert secret_key not in on_disk


# -- .env.example ships the key name, never a value --------------------------

def test_env_example_declares_the_key_with_no_real_value() -> None:
    text = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.startswith("AUTOTESTER_APPROVAL_KEY")]
    assert lines == ["AUTOTESTER_APPROVAL_KEY="], "the committed template must ship no real value"


# -- overclaiming prose is corrected, repo-wide ------------------------------

def test_no_overclaiming_tamper_proof_prose_remains_anywhere_in_src() -> None:
    """The AT-110 finding: an operator-facing docstring or --help text that
    says an approval "cannot be edited on disk to widen itself" (or the
    pre-fix "tamper EVIDENCE, not tamper proofing" framing, now stale once a
    signature genuinely provides proofing against a non-key-holder) overclaims
    or misdescribes the real guarantee."""
    offenders = []
    stale = (
        "cannot be edited on disk to widen itself",
        "editing the row afterwards to widen it invalidates it",
        "tamper EVIDENCE, not tamper",
    )
    for path in (Path(__file__).resolve().parents[1] / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(phrase in text for phrase in stale):
            offenders.append(str(path))
    assert offenders == []
