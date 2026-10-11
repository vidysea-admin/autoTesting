# ruff: noqa
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import pytest
from attack_cases import cases, mutants
from zip_fixtures import make_store
from ui_intake_support import client, store, gate  # fixtures
from ui_intake_support import UPLOAD
from autotester.sources.zip_intake import expand_zip
from autotester.schema.intake import IntakeReport

CASES = cases()
OUT = Path(os.environ["ATTACK_OUT"])
OUT.mkdir(exist_ok=True, parents=True)


def _files(root: Path, sub: str):
    d = root / ".work" / sub
    return [p for p in d.rglob("*") if p.is_file()] if d.exists() else []


@pytest.mark.parametrize("name", sorted(CASES))
def test_expand(name, tmp_path):
    st = make_store(tmp_path)
    arc = tmp_path / "in.zip"
    arc.write_bytes(CASES[name])
    try:
        rep = expand_zip(st, arc)
    except BaseException as exc:
        (OUT / f"expand-{name}.txt").write_text(encoding="utf-8", data="RAISED " + "".join(traceback.format_exception(exc))[-1200:])
        raise
    assert isinstance(rep, IntakeReport)
    (OUT / f"expand-{name}.txt").write_text(encoding="utf-8", data=
        f"{rep.status.value} " + "; ".join(f"{m.member}:{m.outcome.value}:{m.reason}" for m in rep.members)[:300])
    for s in st.list_sources():
        assert Path(s.path).is_file()
    assert _files(tmp_path, "intake") == []


@pytest.mark.parametrize("name", sorted(CASES))
def test_route(name, client, store, tmp_path, gate):
    r = client.post(UPLOAD, files={"recording": ("hostile.zip", CASES[name], "application/zip")},
                    data={"label": "x"})
    (OUT / f"route-{name}.txt").write_text(encoding="utf-8", data=f"{r.status_code} " + r.text[-160:].replace("\n", " "))
    assert r.status_code < 500, r.status_code
    assert "Traceback" not in r.text
    for s in store.list_sources():
        assert Path(s.path).is_file()
    assert _files(tmp_path, "uploads") == [] and _files(tmp_path, "intake") == []


def test_fuzz_expand(tmp_path):
    bad = []
    for i, raw in mutants(int(os.environ.get("FUZZ_N", "300")), 20261011):
        st = make_store(tmp_path / f"s{i}")
        arc = tmp_path / f"m{i}.zip"
        arc.write_bytes(raw)
        try:
            expand_zip(st, arc)
            for s in st.list_sources():
                assert Path(s.path).is_file()
            assert _files(tmp_path / f"s{i}", "intake") == []
        except BaseException as exc:
            bad.append((i, repr(exc)[:200]))
            (OUT / f"fuzzbad-{i}.zip").write_bytes(raw)
    (OUT / "fuzz-summary.json").write_text(encoding="utf-8", data=json.dumps(bad))
    assert not bad, bad


def test_fuzz_route(client, store, tmp_path, gate):
    bad = []
    for i, raw in mutants(60, 777):
        r = client.post(UPLOAD, files={"recording": ("h.zip", raw, "application/zip")}, data={"label": "x"})
        if r.status_code >= 500 or "Traceback" in r.text:
            bad.append((i, r.status_code))
            (OUT / f"routefuzzbad-{i}.zip").write_bytes(raw)
        for s in store.list_sources():
            if not Path(s.path).is_file():
                bad.append((i, "row without file"))
    assert not bad, bad
