"""Inbox 2026-10-28 (run3): manifest integrity hashes must survive redaction.

`_dump` used to scrub the whole manifest, so a short `.env` value (a 3-char SMTP port) that
happened to occur inside a hex `sha256` was replaced by `[REDACTED]:..` and `load_bundle`
then failed its own hash check (PartialBundleError). Hashes are exempt; every free-text
manifest field is still scrubbed. Fully offline.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    EvidenceKind,
    Outcome,
    Result,
)
from autotester.schema.flowspec import Step
from autotester.schema.run import Evidence, RawResult
from autotester.schema.run_state import StageName
from autotester.schema.trace import StageSpan
from autotester.schema.verdict import Failure, Verdict
from autotester.stages.failure_bundle import (
    PartialBundleError,
    build_failure_bundle,
    load_bundle,
    sources_from_result,
)

PNG = b"\x89PNG\r\n\x1a\nfake-masked-pixels"
PNG_SHA = hashlib.sha256(PNG).hexdigest()


def _build(tmp: Path, redactor: Redactor, run_id: str = "run_A") -> Path:
    steps = [Step(order=i, action=Action.CLICK, target=f"button {i}") for i in (1, 2, 3)]
    case = Case(project="demo", flow_id="login", kind=CaseKind.WORST,
                case_class=CaseClass.AUTH_WRONG_CREDS, title="wrong password", steps=steps)
    (tmp / "s2.png").write_bytes(PNG)
    ev = [Evidence(kind=EvidenceKind.SCREENSHOT, path="s2.png", step_order=2, masked=True,
                   label="step 2")]
    result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error="timed out", evidence=ev)
    verdict = Verdict(run_id=run_id, case_id=case.id, result=Result.FAIL,
                      failures=[Failure(criterion_id="c1", reason="login did not error")])
    span = StageSpan(trace_id=run_id, stage=StageName.EXECUTE, status="failed", error="timed out")
    return build_failure_bundle(
        out_dir=tmp / "bundles", run_id=run_id, case=case, result=result, verdict=verdict,
        sources=sources_from_result(run_id, tmp, result), spans=[span], redactor=redactor,
        failing_step=2)


def test_short_secret_inside_a_computed_hash_does_not_break_the_bundle(tmp_path: Path) -> None:
    short = PNG_SHA[10:13]  # a 3-char secret that occurs inside the screenshot's real hash
    assert short in PNG_SHA
    bundle = _build(tmp_path, Redactor({"AUTOTESTER_SMTP_PORT": short}))
    manifest = load_bundle(bundle)  # pre-fix: PartialBundleError (hash was scrubbed)
    shots = [f for f in manifest.files if f.name.startswith("screenshots/")]
    assert shots and all(f.sha256 == PNG_SHA for f in shots)
    assert "[REDACTED]" not in (bundle / "manifest.json").read_text(encoding="utf-8")


def test_free_text_manifest_field_is_still_masked(tmp_path: Path) -> None:
    secret = "Zq7-planted-Secret-9981"
    run_id = f"run_{secret}"
    bundle = _build(tmp_path, Redactor({"APP_PASSWORD": secret}), run_id=run_id)
    text = (bundle / "manifest.json").read_text(encoding="utf-8")
    assert secret not in text and "[REDACTED]:APP_PASSWORD" in text
    load_bundle(bundle)


def test_a_tampered_hash_is_still_refused(tmp_path: Path) -> None:
    bundle = _build(tmp_path, Redactor({"K": "unrelated-secret-123"}))
    path = bundle / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["files"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    try:
        load_bundle(bundle)
    except PartialBundleError:
        return
    raise AssertionError("tampered hash accepted")
