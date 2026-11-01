"""mongo-store U8: `autotester store migrate` / `verify` over the file state (M9, M25, M41-M44).

Fake Mongo and tmp dirs only; every value is synthetic.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fake_mongo import CANARY
from store_migrate_support import (
    CEO_CANARY,
    PNG,
    PRIVATE_KEY,
    URI,
    Rig,
    approval,
    make_rig,
    seed_state,
)

from autotester.store.blobs import MongoBlobStore
from autotester.store.migrate_state import verify_approvals
from autotester.store.mongo_backend import MongoBackend


@pytest.fixture
def rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Rig:
    return make_rig(tmp_path, monkeypatch)


def test_dry_run_opens_no_connection_and_writes_nothing(rig: Rig) -> None:
    seed_state(rig)
    before = rig.tree()
    result = rig.invoke("migrate")
    assert result.exit_code == 0, result.output
    assert rig.opened == 0 and rig.server.databases == {} and rig.server.log == []
    assert rig.tree() == before
    for section in ("per collection:", "to_insert=", "bytes per kind:", "largest documents",
                    "GridFS total:", "keys that failed safe_name:", "never moved (M25):",
                    "browser sessions are never migrated"):
        assert section in result.output
    assert "DRY RUN (no connection opened)" in result.output


def test_dry_run_loads_no_driver(rig: Rig) -> None:
    seed_state(rig)
    code = ("import sys\nfrom typer.testing import CliRunner\n"
            "from autotester.cli_store import app\n"
            "r =CliRunner().invoke(app, ['migrate'])\n"
            "print(r.exit_code, 'pymongo' in sys.modules, 'bson' in sys.modules)")
    env = {**os.environ, "AUTOTESTER_ROOT": str(rig.root),
           "AUTOTESTER_AUTH_DIR": str(rig.auth_dir), "PATHLYNKS_MONGO_URI": URI}
    done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                          timeout=120, check=False)
    assert done.stdout.split() == ["0", "False", "False"], done.stdout + done.stderr


def test_m25_families_are_reported_and_never_stored(rig: Rig) -> None:
    seed_state(rig)
    report = rig.invoke("migrate").output
    for family in ("profiles=1", "chunks=1", "exports=1", ".work-scratch=1",
                   ".env=1", "crawl_summaries=1", ".xlsx=1"):
        assert family in report
    assert "to_insert" in report
    assert rig.invoke("migrate", "--apply").exit_code == 0
    stored = rig.everywhere()
    for banned in ("private", "profiles", "chunks", "report.xlsx", "scratch",
                   "crawl_summaries/s.json", "loose.xlsx"):
        assert banned not in stored


def test_apply_is_idempotent_and_never_touches_the_source(rig: Rig) -> None:
    seed_state(rig)
    before = rig.tree()
    first = rig.invoke("migrate", "--apply")
    assert first.exit_code == 0, first.output
    assert "written: 0" not in first.output and rig.opened == 1
    assert rig.tree() == before
    second = rig.invoke("migrate", "--apply")
    assert second.exit_code == 0 and "written: 0" in second.output
    assert rig.tree() == before


def test_blobs_are_written_before_the_documents(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    seed_state(rig)
    order: list[str] = []
    put, row, blob = MongoBackend.put, MongoBackend.append_row, MongoBlobStore.put
    monkeypatch.setattr(MongoBackend, "put", lambda s, k, d: (order.append("doc"), put(s, k, d))[1])
    monkeypatch.setattr(MongoBackend, "append_row",
                        lambda s, k, t: (order.append("doc"), row(s, k, t))[1])
    monkeypatch.setattr(MongoBlobStore, "put",
                        lambda s, *a, **k: (order.append("blob"), blob(s, *a, **k))[1])
    assert rig.invoke("migrate", "--apply").exit_code == 0
    assert "blob" in order and order.index("blob") < order.index("doc")
    assert order.count("blob") == 1 and set(order[: order.index("doc")]) == {"blob"}


def test_signed_rows_arrive_byte_identical_and_verify(rig: Rig) -> None:
    rows = seed_state(rig)
    assert rig.invoke("migrate", "--apply").exit_code == 0
    stored = sorted(rig.docs("approvals"), key=lambda d: d["seq"])
    assert [d["text"] for d in stored] == rows
    done = rig.invoke("verify")
    assert done.exit_code == 0, done.output
    assert "approvals: " in done.output and "rows=3" in done.output
    assert "not_intact=0" in done.output and "signature_failed=0" in done.output
    assert "mismatches: 0" in done.output


def test_verify_catches_one_flipped_byte_in_a_signed_row(rig: Rig) -> None:
    seed_state(rig)
    rig.invoke("migrate", "--apply")
    doc = rig.docs("approvals")[0]
    doc["text"] = doc["text"].replace("Umesh", "Umesk", 1)
    done = rig.invoke("verify")
    assert done.exit_code == 1 and "conflicting-id=1" in done.output


def test_verify_catches_an_altered_document_and_a_changed_blob(rig: Rig) -> None:
    seed_state(rig)
    rig.invoke("migrate", "--apply")
    assert rig.invoke("verify").exit_code == 0
    rig.docs("runs")[0]["text"] = '{"id": "r1", "status": "tampered"}'
    assert rig.invoke("verify").exit_code == 1
    rig.docs("runs")[0]["text"] = '{"id": "r1", "status": "done"}'
    rig.write("projects/demo/runs/r1/shot.png", PNG + b"-edited")
    done = rig.invoke("verify")
    assert done.exit_code == 1 and "gridfs" in done.output and "conflicting-id=1" in done.output


def test_a_differing_stored_document_is_a_conflict_never_overwritten(rig: Rig) -> None:
    seed_state(rig)
    rig.invoke("migrate", "--apply")
    held = rig.docs("projects")[0]
    held["text"] = '{"slug": "elsewhere"}'
    done = rig.invoke("migrate", "--apply")
    assert done.exit_code == 1 and "conflicting-id=1" in done.output
    assert rig.docs("projects")[0]["text"] == '{"slug": "elsewhere"}'


def test_apply_without_a_uri_refuses_and_writes_nothing(
        rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    seed_state(rig)
    monkeypatch.delenv("PATHLYNKS_MONGO_URI")
    for args in (("migrate", "--apply"), ("verify",)):
        done = rig.invoke(*args)
        assert done.exit_code == 2 and "no Mongo URI" in done.output
    assert rig.opened == 0 and rig.server.databases == {}


def test_a_failing_migrate_prints_the_class_name_and_never_the_uri(
        rig: Rig, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    seed_state(rig)
    rig.server.down = True
    rig.server.down_message = f"cannot reach {URI}"
    for args in (("migrate", "--apply"), ("migrate", "--check-remote"), ("verify",)):
        done = rig.invoke(*args)
        assert done.exit_code == 1 and " failed: " in done.output
        assert CANARY not in done.output and CANARY not in capsys.readouterr().out
    assert CANARY not in caplog.text


def test_a_raw_exception_carrying_the_uri_prints_only_its_class_name(
        rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    """The fake driver already sanitises its errors; this one is raw, as a driver's may be."""
    from autotester import cli_store

    seed_state(rig)

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError(f"cannot reach {URI}")

    monkeypatch.setattr(cli_store, "migrate_state", boom)
    for args in (("migrate",), ("migrate", "--apply"), ("verify",)):
        done = rig.invoke(*args)
        assert done.exit_code == 1 and "failed: RuntimeError" in done.output
        assert CANARY not in done.output and URI not in done.output


def test_a_screenshot_recorded_unmasked_stays_out(rig: Rig) -> None:
    seed_state(rig)
    rig.write("projects/demo/runs/r1/case1.json",
              '{"id": "x", "evidence": [{"path": "shot.png", "masked": false}]}')
    done = rig.invoke("migrate", "--apply")
    assert done.exit_code == 1 and "refused=1" in done.output
    assert not any("shot.png" in repr(d) for d in rig.docs("fs.files"))


def test_part_filter_and_unknown_part(rig: Rig) -> None:
    seed_state(rig)
    done = rig.invoke("migrate", "--apply", "--only", "approvals")
    assert done.exit_code == 0
    assert rig.docs("cases") == [] and len(rig.docs("approvals")) == 2
    bad = rig.invoke("migrate", "--only", "nonsense")
    assert bad.exit_code == 2 and "unknown part" in bad.output


def test_ceo_bench_list_moves_but_only_its_count_and_hash_are_reported(
        rig: Rig, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    """D-128: the private answer list is copied and verified; its item text and name never leave."""
    seed_state(rig)
    text = (rig.root / PRIVATE_KEY).read_text(encoding="utf-8")
    digest = hashlib.sha256(hashlib.sha256(text.encode()).hexdigest().encode()).hexdigest()
    shown = []
    for args in (("migrate",), ("migrate", "--check-remote"), ("migrate", "--apply"),
                 ("migrate", "--apply"), ("verify",)):
        done = rig.invoke(*args)
        assert done.exit_code == 0, done.output
        shown.append(done.output)
        assert f"ceo-bench (private, D-128): 1 file(s), content hash {digest}" in done.output
    rig.server.down = True
    rig.server.down_message = f"cannot reach {CEO_CANARY}"
    shown.append(rig.invoke("verify").output)
    rig.server.down = False
    assert any(d["_id"] == PRIVATE_KEY for d in rig.docs("server_state"))
    seen = "".join(shown) + capsys.readouterr().out + caplog.text
    assert CEO_CANARY not in seen and "ceo-bench/" not in seen and "atomic-list" not in seen
    assert "written: 0" in shown[3]


def test_a_changed_ceo_bench_list_is_a_conflict_not_an_overwrite(rig: Rig) -> None:
    seed_state(rig)
    rig.invoke("migrate", "--apply")
    rig.write(PRIVATE_KEY, '{"items": []}')
    done = rig.invoke("verify")
    assert done.exit_code == 1 and "conflicting-id=1" in done.output
    assert CEO_CANARY not in done.output


def test_a_reserialised_signed_row_is_a_conflict_not_the_same_row(rig: Rig) -> None:
    """M43: approvals are compared as written, so a re-serialised row (same JSON, other bytes)
    is not accepted as equal."""
    seed_state(rig)
    rig.invoke("migrate", "--apply")
    doc = rig.docs("approvals")[0]
    doc["text"] = json.dumps(json.loads(doc["text"]), indent=1, sort_keys=True)
    done = rig.invoke("verify")
    assert done.exit_code == 1 and "conflicting-id=1" in done.output


class _Rows:
    def __init__(self, rows: list[str]) -> None:
        self._rows = rows

    def rows(self, _key: str) -> list[str]:
        return self._rows


def test_verify_approvals_flags_forged_unsigned_and_unreadable_rows() -> None:
    good = approval("https://a.demo.test/")
    forged = json.loads(good.model_dump_json(exclude_none=True))
    forged["scope"] = "widened"  # edited after the grant: the content id no longer matches
    badsig = json.loads(good.model_dump_json(exclude_none=True))
    badsig["signature"] = "00" * 32
    rows = [json.dumps(forged), json.dumps(badsig), "not json", good.model_dump_json()]
    got = verify_approvals(_Rows(rows), ["projects/demo/approvals.jsonl"])
    # the forged row also fails its signature; the bad-signature row is intact; "not json" is
    # unreadable and not counted as a row
    assert (got["not_intact"], got["signature_failed"], got["unreadable"], got["rows"]) == (
        1, 2, 1, 3)
