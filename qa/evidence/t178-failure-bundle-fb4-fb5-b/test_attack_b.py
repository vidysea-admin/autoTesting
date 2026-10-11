"""Coordinator B adversarial pass (throwaway copy only)."""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from eval_compiler_fixtures import BROWSE, LOGIN, persona, provider, spec
from test_failure_bundle import SECRET, _build, _case, _fixture

import autotester.stages.failure_bundle as fbm
from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.stages.eval_compiler import compile_evals
from autotester.stages.expand import propose_cases
from autotester.stages.failure_bundle import BundleError, PartialBundleError, load_bundle
from autotester.store.project_store import ProjectStore


def _rewrite(bundle: Path, name: str, idx: int = 0, sha: str | None = None) -> None:
    m = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    m["files"][idx]["name"] = name
    if sha:
        m["files"][idx]["sha256"] = sha
    (bundle / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


def _decoy(tmp_path: Path, bundle: Path) -> tuple[Path, str]:
    out = tmp_path / "outside"
    out.mkdir(exist_ok=True)
    data = (bundle / "case.json").read_bytes()
    (out / "case.json").write_bytes(data)
    import hashlib
    return out, hashlib.sha256(data).hexdigest()


def _hashed(monkeypatch):
    seen = []
    real = fbm._sha256
    monkeypatch.setattr(fbm, "_sha256", lambda p: (seen.append(Path(p)), real(p))[1])
    return seen


def _inside(p: Path, root: Path) -> bool:
    return p.resolve().is_relative_to(root.resolve())


def _mkjunction(link: Path, target: Path) -> None:
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
    assert r.returncode == 0, r.stderr


NAMES = [
    "../outside/case.json", "..\\outside\\case.json", "a/../../outside/case.json",
    "a/..\\..\\outside/case.json", "..", "...", "....//outside/case.json",
    "/outside/case.json", "\\outside\\case.json", "//localhost/c$/outside/case.json",
    "\\\\localhost\\c$\\outside\\case.json", "\\\\?\\C:\\outside\\case.json",
    "\\\\.\\C:\\outside\\case.json", "C:\\outside\\case.json", "c:outside/case.json",
    "case.json::$DATA", "case.json:stream", "case.json\x00.txt", "CON", "NUL", "AUX/x",
    "case.json.", "case.json ", " case.json", "CASE.JSON", "steps/../case.json",
    "./case.json", "steps//2.json", "\u2025/outside/case.json", "%2e%2e/outside/case.json",
    "..%5coutside%5ccase.json", "\uff0e\uff0e/outside/case.json", "outside/../case.json",
]


@pytest.mark.parametrize("name", NAMES)
def test_names(tmp_path, monkeypatch, name):
    bundle = _build(tmp_path, _fixture(tmp_path))
    out, sha = _decoy(tmp_path, bundle)
    # absolute spellings of the decoy too
    name = name.replace("outside/case.json", "outside/case.json")
    _rewrite(bundle, name, sha=sha)
    seen = _hashed(monkeypatch)
    try:
        load_bundle(bundle)
        outcome = "loaded"
    except BundleError as exc:
        outcome = type(exc).__name__
    except Exception as exc:  # anything not a BundleError is a finding
        outcome = "UNEXPECTED " + type(exc).__name__
    assert not outcome.startswith("UNEXPECTED"), outcome
    for p in seen:
        assert _inside(p, bundle), f"hashed outside: {p}"
    print(ascii(name), outcome)


def test_absolute_spellings_of_real_decoy(tmp_path, monkeypatch):
    bundle = _build(tmp_path, _fixture(tmp_path))
    out, sha = _decoy(tmp_path, bundle)
    target = out / "case.json"
    spellings = [str(target), target.as_posix(), "/" + target.as_posix().replace(":", "", 1),
                 "\\\\localhost\\" + str(target).replace(":", "$", 1),
                 "//localhost/" + target.as_posix().replace(":", "$", 1)]
    seen = _hashed(monkeypatch)
    for s in spellings:
        _rewrite(bundle, s, sha=sha)
        with pytest.raises(BundleError):
            load_bundle(bundle)
    assert not seen


def test_junction_variants(tmp_path, monkeypatch):
    bundle = _build(tmp_path, _fixture(tmp_path))
    out, sha = _decoy(tmp_path, bundle)
    _mkjunction(bundle / "up", tmp_path)            # points at the PARENT of the bundles dir
    _mkjunction(bundle / "Out", out)
    seen = _hashed(monkeypatch)
    for name in ["up/outside/case.json", "UP/outside/case.json", "Out/case.json",
                 "OUT/CASE.JSON", "up/bundles/../outside/case.json"]:
        try:
            _rewrite(bundle, name, sha=sha)
            with pytest.raises(BundleError):
                load_bundle(bundle)
        except Exception:
            print("variant", name)
            raise
    assert not seen, seen
    # junction chain: bundle/chain -> bundle/Out (itself a junction)
    _mkjunction(bundle / "chain", bundle / "Out")
    _rewrite(bundle, "chain/case.json", sha=sha)
    with pytest.raises(BundleError, match="escapes"):
        load_bundle(bundle)
    # junction that stays inside is allowed and not an escape
    _mkjunction(bundle / "stepsalias", bundle / "steps")
    m = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    m["files"][0]["name"] = "case.json"
    m["files"][0]["sha256"] = m["files"][0]["sha256"]
    # (restore real hash)
    import hashlib
    m["files"][0]["sha256"] = hashlib.sha256((bundle / "case.json").read_bytes()).hexdigest()
    (bundle / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    load_bundle(bundle)


def test_junction_to_partial_and_short_name(tmp_path):
    bundle = _build(tmp_path, _fixture(tmp_path))
    part = tmp_path / "bundles" / "zzzz-long-partial-name.partial"
    bundle.rename(part)  # a complete-looking tree under a .partial name
    # direct
    with pytest.raises(PartialBundleError):
        load_bundle(part)
    # via junction with innocent name
    j = tmp_path / "bundles" / "innocent"
    _mkjunction(j, part)
    with pytest.raises(PartialBundleError, match="partial"):
        load_bundle(j)
    # via 8.3 short name
    buf = ctypes.create_unicode_buffer(300)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(part), buf, 300)
    print("short:", buf.value if n else None)
    if n and buf.value.lower() != str(part).lower():
        with pytest.raises(PartialBundleError):
            load_bundle(Path(buf.value))
    # case variant of the suffix
    up = tmp_path / "bundles" / "upper.PARTIAL"
    part.rename(up)
    try:
        load_bundle(up)
        print("UPPERCASE .PARTIAL loads (complete tree under .PARTIAL name)")
    except PartialBundleError:
        print("uppercase refused")


def test_manifest_file_symlink(tmp_path):
    bundle = _build(tmp_path, _fixture(tmp_path))
    real = bundle / "manifest.json"
    outside = tmp_path / "outside_manifest.json"
    outside.write_bytes(real.read_bytes())
    real.unlink()
    try:
        os.symlink(outside, real)
    except OSError as exc:
        pytest.skip(f"no symlink privilege: {exc}")
    with pytest.raises(PartialBundleError, match="escapes"):
        load_bundle(bundle)


def test_run_id_and_case_id_with_separators(tmp_path):
    from autotester.schema.run import RawResult
    from autotester.schema.verdict import Failure, Verdict
    from autotester.schema.trace import StageSpan
    from autotester.schema.run_state import StageName
    from autotester.schema.enums import Outcome, Result
    from autotester.stages.failure_bundle import build_failure_bundle, sources_from_result

    evil = "..\\..\\evil/../../x:y"
    case = _case()
    ev = _fixture(tmp_path)[1].evidence
    result = RawResult(case_id=case.id, outcome=Outcome.ERRORED, error="boom", evidence=ev)
    verdict = Verdict(run_id=evil, case_id=case.id, result=Result.FAIL,
                      failures=[Failure(criterion_id="c1", reason="r")])
    span = StageSpan(trace_id=evil, stage=StageName.EXECUTE, status="failed", error="boom")
    before = {p for p in tmp_path.rglob("*")}
    out = tmp_path / "b2"
    b = build_failure_bundle(out_dir=out, run_id=evil, case=case, result=result, verdict=verdict,
                             sources=sources_from_result(evil, tmp_path, result), spans=[span],
                             redactor=Redactor({"APP_PASSWORD": SECRET}), failing_step=3)
    assert b.parent == out and ".." not in b.name and "/" not in b.name and ":" not in b.name
    new = {p for p in tmp_path.rglob("*")} - before
    assert all(p.resolve().is_relative_to(out.resolve()) for p in new)
    load_bundle(b)


@pytest.mark.parametrize("secret", [
    'p"a\\ss<&>\'w\nx\ty', "caf\u00e9-\u2603-\U0001f600-secret", "a/b\\c%20d+e=f", "Zq7-planted-Secret-9981",
])
def test_special_secret_in_every_field(tmp_path, secret):
    from autotester.schema.flowspec import Step
    from autotester.schema.enums import Action, CaseClass, CaseKind
    fx = _fixture(tmp_path, error=f"typed {secret} failed", verdict_reason=f"saw {secret}",
                  secret_in_note=False)
    case, result, verdict, spans = fx
    steps = list(case.steps)
    steps[2] = Step(order=3, action=Action.CLICK, target=f"btn {secret}", note=f"n {secret}")
    case = Case(project="demo", flow_id="login", kind=CaseKind.WORST,
                case_class=CaseClass.AUTH_WRONG_CREDS, title=f"t {secret}", steps=steps)
    result = result.model_copy(update={"case_id": case.id})
    verdict = verdict.model_copy(update={"case_id": case.id})
    b = _build(tmp_path, (case, result, verdict, spans),
               redactor=Redactor({"APP_PASSWORD": secret}))
    forms = {secret, json.dumps(secret), json.dumps(secret)[1:-1], json.dumps(secret, ensure_ascii=False)[1:-1],
             secret.replace("\n", "\\n"), repr(secret)}
    for p in b.rglob("*"):
        if p.is_file():
            data = p.read_text(encoding="utf-8", errors="replace")
            for f in forms:
                assert f not in data, (p.name, f)
    load_bundle(b)


def test_secret_in_screenshot_suffix(tmp_path):
    secret = "Zq7-planted-Secret-9981"
    fx = _fixture(tmp_path)
    case, result, verdict, spans = fx
    ev = list(result.evidence)
    f = tmp_path / f"s3.{secret}"
    f.write_bytes(b"\x89PNGx")
    ev[2] = ev[2].model_copy(update={"path": f.name})
    result = result.model_copy(update={"evidence": ev})
    try:
        b = _build(tmp_path, (case, result, verdict, spans))
    except Exception as exc:
        print("secret-suffix build raised", type(exc).__name__, str(exc)[:120])
        return
    names = [p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file()]
    print("secret-suffix names:", names)
    assert not any(secret in n for n in names), names


# -- FB5 / compile_evals partial spend -------------------------------------------
def test_compile_evals_partial_spend(tmp_path):
    sp = spec(LOGIN, BROWSE)
    store = ProjectStore("demo", tmp_path)
    store.save_flowspec(sp)
    rows = propose_cases(sp)
    store.stage_case_proposals(rows)
    for r in rows:
        if r.flow_id == LOGIN.id:
            store.review_case_proposal(r.id, "umesh", approved=True)
    prov = provider(LOGIN, BROWSE)
    with pytest.raises(ValueError):
        compile_evals(sp, persona(LOGIN, BROWSE), [], prov, store=store)
    print("COMPILE partial-spend prompts:", len(prov.prompts))
    assert prov.prompts == [], f"{len(prov.prompts)} provider call(s) spent before refusal"


def test_proposal_id_edge_cases(tmp_path):
    from autotester.stages.expand import expand
    sp = spec(LOGIN, BROWSE)
    store = ProjectStore("demo", tmp_path)
    store.save_flowspec(sp)
    rows = propose_cases(sp)
    store.stage_case_proposals(rows)
    prov = provider(LOGIN, BROWSE)
    for ids in ([], ["x"], ["../../etc"]):
        with pytest.raises(ValueError):
            expand(sp, prov, store=store, proposal_ids=ids)
    assert prov.prompts == []
    # CLI --by whitespace
    with pytest.raises(ValueError):
        store.review_case_proposal(rows[0].id, " ", True)


@pytest.mark.parametrize("secret", ['ab"cd1234', "ab\cd1234", "ab\ncd1234", "abcd1234", "ab<cd>1234&"])
def test_trace_leak_minimal(tmp_path, secret):
    case, result, verdict, spans = _fixture(tmp_path, error=f"typed {secret} failed")
    try:
        b = _build(tmp_path, (case, result, verdict, spans), redactor=Redactor({"APP_PASSWORD": secret}))
    except ValueError as exc:
        print("FAILCLOSED", ascii(secret))
        return
    leaked = [p.name for p in b.rglob("*") if p.is_file()
              and (json.dumps(secret)[1:-1] in p.read_text(encoding="utf-8", errors="replace")
                   or secret in p.read_text(encoding="utf-8", errors="replace"))]
    print("LEAK" if leaked else "CLEAN", ascii(secret), leaked)


def test_suffix_load(tmp_path):
    secret = "Zq7-planted-Secret-9981"
    case, result, verdict, spans = _fixture(tmp_path)
    ev = list(result.evidence)
    f = tmp_path / f"s3.{secret}"
    f.write_bytes(b"\x89PNGx")
    ev[2] = ev[2].model_copy(update={"path": f.name})
    result = result.model_copy(update={"evidence": ev})
    b = _build(tmp_path, (case, result, verdict, spans))
    m = (b / "manifest.json").read_text(encoding="utf-8")
    print("MANIFEST has secret:", secret in m, "| has REDACTED name:", "REDACTED" in m)
    try:
        load_bundle(b)
        print("LOADS ok")
    except BundleError as exc:
        print("LOAD refused:", exc)
