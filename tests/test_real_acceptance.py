"""T-169 real-target driver, proved on the local fixture product with the mock seams.

No browser, no model, no live site: the driver's approval gate, evidence files and GR1-GR4
checklist are exercised through TestClient exactly as `scripts/run_real_acceptance.py` does.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval
from test_generic_acceptance import (
    SITE,
    _crawl_fixture,
    _drive,
    _spec,
    _vision,
    client,  # noqa: F401 - pytest fixture
    product_url,  # noqa: F401 - pytest fixture
    scratch_root,  # noqa: F401 - pytest fixture
)

from autotester.core.consent import ApprovalRequired
from autotester.schema.enums import ApprovalKind
from autotester.stages.generic_acceptance import ModeSeams
from autotester.stages.real_acceptance import (
    EVIDENCE_DIR,
    drive_real,
    preflight,
    required_kinds,
)
from autotester.store.project_store import ProjectStore

assert SITE.exists()


def test_required_kinds_follow_the_mode() -> None:
    assert required_kinds("teaching") == [ApprovalKind.LIVE_CASE]
    assert required_kinds("url_only") == [ApprovalKind.CRAWL, ApprovalKind.LIVE_CASE]


def test_refuses_without_approval_and_names_the_grant(
    client: TestClient, scratch_root: Path, product_url: str, tmp_path: Path,  # noqa: F811
) -> None:
    spec = _spec("url_only", product_url, tmp_path)
    assert client.post("/onboard", data=spec.form(), follow_redirects=False).status_code == 303
    store = ProjectStore(spec.slug, scratch_root)
    with pytest.raises(ApprovalRequired, match="Grant one with"):
        preflight(store, "url_only")
    assert not (scratch_root / EVIDENCE_DIR).exists()  # nothing started, nothing written


@pytest.mark.parametrize("mode", ["teaching", "url_only"])
def test_driver_writes_evidence_and_checklist(
    mode: str, client: TestClient, scratch_root: Path,  # noqa: F811
    product_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,  # noqa: F811
) -> None:
    first, store, spec = _drive(mode, client, scratch_root, product_url, tmp_path, monkeypatch)
    target = store.load_project().base_url  # type: ignore[union-attr]
    grant_live_case_approval(store, project=spec.slug, target=target,
                             run_kind=ApprovalKind.CRAWL)
    spec.onboard = False
    seams = ModeSeams(crawl_fn=_crawl_fixture(product_url, store),
                      ingest_provider=None, before_run=None)
    if mode == "teaching":  # reuse the stored video source; vision seam from the first drive
        seams.ingest_provider = _vision(product_url)
    result, out, lines = drive_real(client, store, spec, seams, scratch_root)

    assert out == scratch_root / EVIDENCE_DIR / mode and result.run_id != first.run_id
    evidence = json.loads((out / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["run_id"] == result.run_id and evidence["mode"] == mode
    assert sum(evidence["verdict_counts"].values()) >= 1
    assert set(evidence["verdict_counts"]) >= {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}
    assert isinstance(evidence["inconclusive_breakdown"], dict)
    assert evidence["human_verdict"] is None  # GR3 is never filled by the driver
    assert (out / "comparison.json").read_text(encoding="utf-8").strip().startswith("{")
    text = "\n".join(lines)
    assert "GR1" in text and "GR2" in text and "GR3 human" in text and "AT-281" in text
    assert (out / "checklist.md").read_text(encoding="utf-8") == text + "\n"


