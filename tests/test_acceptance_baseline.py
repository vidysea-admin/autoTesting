"""Input-only baseline preparation must preserve scope without inheriting product truth."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from prepare_acceptance_baselines import main

from autotester.schema.acceptance_baseline import BaselineInput, BaselinePlan, BaselineReceipt
from autotester.schema.project import Project, ProviderConfig, SecretRef
from autotester.stages.acceptance_baseline import prepare_baselines
from autotester.store.project_store import ProjectStore


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def baseline(tmp_path):
    source_root, inputs = tmp_path / "original", tmp_path / "inputs"
    store = ProjectStore("product", source_root)
    store.save_project(Project(
        slug="product", name="Product", base_url="https://product.example/app",
        allowed_domains=["product.example"], production=True, login_case_id="old-login",
        secrets=[SecretRef(key="TEST_USER", domains=["product.example"]),
                 SecretRef(key="OTHER_KEY", domains=["product.example"])],
        providers=ProviderConfig(vision="configured-vision", agent="configured-agent",
                                 judge="configured-judge")))
    for name in (".env", "flowspec.json", "cases.jsonl", "case_proposals.jsonl",
                 "approvals.jsonl", "runs/old/report.json", "crawl/old.json"):
        path = store.paths.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture-only-historical-data", encoding="utf-8")
    inputs.mkdir()
    rows = []
    for name, kind in (("clip.mp4", "video"), ("guide.md", "doc")):
        blob = f"approved-{kind}".encode()
        (inputs / name).write_bytes(blob)
        rows.append(BaselineInput(path=name, sha256=digest(blob), kind=kind,
                                  approval_ref="owner-input-approval-1"))
    plan = BaselinePlan(source_slug="product", baseline_slug="trial",
                        source_config_sha256=digest(store.paths.config.read_bytes()),
                        target_build="build-immutable-1", credential_keys=["TEST_USER"],
                        teaching_inputs=rows)
    return source_root, inputs, tmp_path / "pair", plan, store


def test_same_build_scoped_refs_and_input_only_isolation(baseline, monkeypatch):
    root, inputs, output, plan, original = baseline
    before = {p: p.read_bytes() for p in original.paths.dir.rglob("*") if p.is_file()}
    read_bytes, reads = Path.read_bytes, []

    def recording_read(path):
        reads.append(path)
        if path.name == ".env":
            pytest.fail("credential values must never be read")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", recording_read)
    manifest = inputs / "plan.json"
    manifest.write_text(plan.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prepare_acceptance_baselines", "--plan", str(manifest),
                                     "--source-root", str(root), "--input-root", str(inputs),
                                     "--destination", str(output)])
    assert main() == 0
    receipt = BaselineReceipt.model_validate_json((output / "baseline-receipt.json").read_bytes())
    assert receipt.target_build == "build-immutable-1" and not receipt.target_build_verified
    assert receipt.source_config_sha256 == plan.source_config_sha256
    assert receipt.plan_sha256 == digest(plan.model_dump_json().encode())
    for mode, slug in (("teaching", receipt.teaching_slug), ("url_only", receipt.url_only_slug)):
        store = ProjectStore(slug, output / mode)
        project = store.load_project()
        assert project.base_url == "https://product.example/app" and project.production
        assert project.allowed_domains == ["product.example"]
        assert project.providers == original.load_project().providers
        assert project.secrets == [original.load_project().secrets[0]]
        assert (project.login_case_id is None and project.schedule is None
                and project.tracker is None)
        sources = store.list_sources()
        assert len(sources) == (2 if mode == "teaching" else 0)
        for source, row in zip(sources, plan.teaching_inputs, strict=False):
            assert source.project == slug and source.sha256 == row.sha256
            assert row.approval_ref in source.provenance.note
            assert (store.paths.dir / source.path).read_bytes() == (inputs / row.path).read_bytes()
        assert not store.load_flowspec() and not store.list_cases() and not store.list_approvals()
        assert not store.list_case_proposals() and not store.paths.runs_dir.exists()
        assert (output / mode / "qa/evidence/t169-real" / mode).is_dir()
    assert not any(p.name == ".env" for p in output.rglob("*"))
    assert not any(p.is_relative_to(original.paths.dir) and p != original.paths.config
                   for p in reads)
    assert all(read_bytes(p) == blob for p, blob in before.items())


@pytest.mark.parametrize("fault", ["config", "input", "existing", "overlap",
                                  "empty-build", "redirected", "source-escape"])
def test_stale_or_existing_plan_refused_without_writes(baseline, fault):
    root, inputs, output, plan, store = baseline
    if fault == "config":
        plan.source_config_sha256 = "stale"
    elif fault == "input":
        plan.teaching_inputs[0].sha256 = "stale"
    elif fault == "existing":
        output.mkdir()
        (output / "comparison.json").write_text("preserve", encoding="utf-8")
    elif fault == "overlap":
        output = store.paths.dir / "acceptance"
    elif fault == "redirected":
        output = output.parent / "unused" / ".." / "pair"
    elif fault == "source-escape":
        foreign = root / "elsewhere"
        foreign.mkdir()
        (foreign / "project.json").write_bytes(store.paths.config.read_bytes())
        plan.source_slug = "../elsewhere"
    else:
        plan.target_build = " "
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ValueError):
        prepare_baselines(root, inputs, output, plan)
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert sorted(p.name for p in output.rglob("*")) == (
        ["comparison.json"] if fault == "existing" else [])


@pytest.mark.parametrize("fault", ["escape", "absolute", "env", "historical-json",
                                  "unapproved", "no-doc"])
def test_only_explicit_approved_contained_inputs(baseline, fault):
    root, inputs, output, plan, _ = baseline
    row = plan.teaching_inputs[0]
    if fault == "escape":
        row.path = "../outside.mp4"
        (inputs.parent / "outside.mp4").write_bytes((inputs / "clip.mp4").read_bytes())
    elif fault == "absolute":
        row.path = str((inputs / "clip.mp4").resolve())
    elif fault == "env":
        row.path = ".env.txt"
        row.kind = "doc"
        plan.teaching_inputs.append(plan.teaching_inputs[0].model_copy(
            update={"path": "clip.mp4", "kind": "video"}))
        (inputs / row.path).write_bytes((inputs / "clip.mp4").read_bytes())
    elif fault == "historical-json":
        row.path = "flowspec.json"
        (inputs / row.path).write_bytes((inputs / "clip.mp4").read_bytes())
    elif fault == "unapproved":
        row.approval_ref = ""
    else:
        plan.teaching_inputs.pop()
    with pytest.raises(ValueError):
        prepare_baselines(root, inputs, output, plan)
    assert not output.exists()


@pytest.mark.parametrize("fault", ["unknown", "duplicate", "unscoped", "foreign-domain",
                                  "url-credentials", "empty"])
def test_credential_reference_scope_never_widens(baseline, fault):
    root, inputs, output, plan, store = baseline
    project = store.load_project()
    if fault == "unknown":
        plan.credential_keys = ["MISSING"]
    elif fault == "duplicate":
        plan.credential_keys *= 2
    elif fault == "empty":
        plan.credential_keys = []
    elif fault == "unscoped":
        project.secrets[0].domains = []
    elif fault == "foreign-domain":
        project.secrets[0].domains = ["foreign.example"]
    else:
        project.base_url = "https://user:password@product.example/"
    store.save_project(project)
    plan.source_config_sha256 = digest(store.paths.config.read_bytes())
    with pytest.raises(ValueError):
        prepare_baselines(root, inputs, output, plan)
    assert not output.exists()


def test_real_resolved_alias_cannot_escape_inputs(baseline):
    root, inputs, output, plan, _ = baseline
    outside, alias = inputs.parent / "outside", inputs / "linked"
    outside.mkdir()
    (outside / "clip.mp4").write_bytes((inputs / "clip.mp4").read_bytes())
    if os.name == "nt":
        script = ("New-Item -ItemType Junction -Path $env:BASELINE_ALIAS "
                  "-Target $env:BASELINE_TARGET -ErrorAction Stop | Out-Null")
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            env=dict(os.environ, BASELINE_ALIAS=str(alias), BASELINE_TARGET=str(outside)),
            capture_output=True, timeout=20)
        assert result.returncode == 0, (
            "Environment gap: junction creation failed: "
            + result.stderr.decode(errors="replace"))
    else:
        alias.symlink_to(outside, target_is_directory=True)
    assert alias.resolve() == outside.resolve()
    plan.teaching_inputs[0].path = "linked/clip.mp4"
    with pytest.raises(ValueError, match="contained"):
        prepare_baselines(root, inputs, output, plan)
    assert not output.exists()


def test_partial_write_is_visible_and_refuses_reuse(baseline, monkeypatch):
    root, inputs, output, plan, store = baseline
    before = {p: p.read_bytes() for p in store.paths.dir.rglob("*") if p.is_file()}
    write_bytes = Path.write_bytes

    def fail_second_input(path, blob):
        if path.is_relative_to(output) and path.name == "input-1.md":
            raise OSError("injected input write failure")
        return write_bytes(path, blob)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "write_bytes", fail_second_input)
        with pytest.raises(OSError, match="injected input write failure"):
            prepare_baselines(root, inputs, output, plan)
    assert output.is_dir() and (output / "baseline-plan.json").exists()
    assert not (output / "baseline-receipt.json").exists()
    partial = {p: p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert any(p.name == "input-0.mp4" for p in partial)
    with pytest.raises(ValueError, match="destination must be new"):
        prepare_baselines(root, inputs, output, plan)
    assert partial == {p: p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert before == {p: p.read_bytes() for p in store.paths.dir.rglob("*") if p.is_file()}
