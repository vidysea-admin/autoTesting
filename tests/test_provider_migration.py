"""Exact-only selected migration, byte-preserving reversal and stale-write refusal."""
import hashlib
import json
import os
import runpy
import sys
from pathlib import Path

import pytest
from litellm_fake import no_network  # noqa: F401

from autotester.providers import config_migration as migration
from autotester.schema.project import ProviderConfig
from autotester.store.filestore import write_bytes, write_text

pytestmark = pytest.mark.usefixtures("no_network")
LEGACY = {"vision": "gemini", "agent": "langchain-fallback", "judge": "langchain-fallback"}


def seed(root, slug, providers):
    record = {"slug": slug, "name": 'Démø "providers"', "base_url": "https://demo.test",
              "providers": providers}
    path = root/"projects"/slug/"project.json"
    path.parent.mkdir(parents=True)
    raw = json.dumps(record, ensure_ascii=False, indent=2).encode().replace(b"\n", b"\r\n")
    path.write_bytes(raw)
    return path, raw


def test_dry_run_selects_only_exact_legacy_preserving_custom_partial_and_evidence(tmp_path):
    a, raw = seed(tmp_path, "demo", LEGACY)
    custom, custom_raw = seed(tmp_path, "custom", {**LEGACY, "vision": "gemini,anthropic"})
    partial, partial_raw = seed(tmp_path, "partial", {"vision": "gemini"})
    evidence = a.parent/"sources.jsonl"
    evidence.write_bytes(b'{"immutable":"evidence"}\r\n')
    plan = migration.plan_legacy_roles(tmp_path, ["demo", "custom", "partial", "missing"])
    assert [e.status for e in plan.entries] == ["eligible", "custom", "partial", "missing"]
    assert plan.entries[0].target == ProviderConfig()
    assert a.read_bytes() == raw and custom.read_bytes() == custom_raw
    assert partial.read_bytes() == partial_raw and evidence.read_bytes().endswith(b"\r\n")
    assert not (tmp_path/".work").exists()


def test_selected_apply_and_restore_are_byte_exact_atomic_and_idempotent(tmp_path):
    a, raw = seed(tmp_path, "demo", LEGACY)
    b, other = seed(tmp_path, "other", LEGACY)
    plan = migration.plan_legacy_roles(tmp_path, ["demo", "other"])
    first = migration.change_legacy_roles(tmp_path, plan, ["demo"])
    assert first[0].status == "applied" and b.read_bytes() == other
    changed = a.read_bytes()
    assert json.loads(changed)["providers"] == ProviderConfig().model_dump()
    old, new = json.loads(raw), json.loads(changed)
    new["providers"] = LEGACY
    assert old == new
    start = raw.index(b"{", raw.index(b'"providers": {'))
    end = raw.index(b"}", start)+1
    assert changed.startswith(raw[:start]) and changed.endswith(raw[end:])
    backup = migration._backup_path(tmp_path, plan.entries[0])
    assert backup.read_bytes() == raw
    assert migration.change_legacy_roles(tmp_path, plan, ["demo"])[0].status == "unchanged"
    restored = migration.change_legacy_roles(tmp_path, plan, ["demo"], restore=True)
    assert restored[0].status == "restored"
    assert a.read_bytes() == raw
    repeated = migration.change_legacy_roles(tmp_path, plan, ["demo"], restore=True)
    assert repeated[0].status == "unchanged"


def test_stale_forged_target_and_tampered_backup_never_overwrite(tmp_path):
    path, raw = seed(tmp_path, "demo", LEGACY)
    plan = migration.plan_legacy_roles(tmp_path, ["demo"])
    edited = raw.replace("Démø".encode(), b"Externally edited")
    path.write_bytes(edited)
    assert migration.change_legacy_roles(tmp_path, plan, ["demo"])[0].status == "stale"
    assert path.read_bytes() == edited
    path.write_bytes(raw)
    forged = plan.model_copy(deep=True)
    forged.entries[0].target.vision = "mock"
    forged.entries[0].after_sha256 = hashlib.sha256(
        migration._replacement(raw, forged.entries[0].target)).hexdigest()
    assert migration.change_legacy_roles(tmp_path, forged, ["demo"])[0].status == "stale"
    assert path.read_bytes() == raw
    assert migration.change_legacy_roles(tmp_path, plan, ["demo"])[0].status == "applied"
    applied = path.read_bytes()
    migration._backup_path(tmp_path, plan.entries[0]).write_bytes(b"corrupt")
    refused = migration.change_legacy_roles(tmp_path, plan, ["demo"], restore=True)
    assert refused[0].status == "stale"
    assert path.read_bytes() == applied


def test_root_path_duplicate_json_and_selection_ambiguity_fail_closed(tmp_path):
    path, raw = seed(tmp_path, "demo", LEGACY)
    plan = migration.plan_legacy_roles(tmp_path, ["demo"])
    with pytest.raises(ValueError):
        migration.plan_legacy_roles(tmp_path, ["../outside"])
    with pytest.raises(ValueError):
        migration.change_legacy_roles(tmp_path/"elsewhere", plan, ["demo"])
    with pytest.raises(ValueError):
        migration.change_legacy_roles(tmp_path, plan, ["not-selected"])
    plan.entries.append(plan.entries[0])
    with pytest.raises(ValueError):
        migration.change_legacy_roles(tmp_path, plan, ["demo"])
    path.write_bytes(raw.replace(b'"vision": "gemini"', b'"vision": "mock", "vision": "gemini"'))
    assert migration.plan_legacy_roles(tmp_path, ["demo"]).entries[0].status == "invalid"


def test_atomic_byte_extension_preserves_mixed_newlines_and_existing_text_behavior(tmp_path):
    raw = b'first\r\nsecond\n\xc3\xa9'
    target = tmp_path/"snapshot.json"
    write_bytes(target, raw)
    assert target.read_bytes() == raw
    write_text(target, "first\nsecond\n")
    assert target.read_bytes() == ("first"+os.linesep+"second"+os.linesep).encode()
    assert not list(tmp_path.glob(".tmp-*"))


def test_migration_cli_defaults_to_plan_and_requires_explicit_selected_apply(tmp_path, monkeypatch):
    path, raw = seed(tmp_path, "demo", LEGACY)
    plan = tmp_path/"plan.json"
    script = Path(migration.__file__).resolve().parents[3]/"scripts/migrate_provider_roles.py"
    argv = [str(script), "--root", str(tmp_path), "--project", "demo", "--plan", str(plan)]
    monkeypatch.setattr(sys, "argv", argv)
    runpy.run_path(str(script), run_name="__main__")
    assert path.read_bytes() == raw and plan.is_file()
    monkeypatch.setattr(sys, "argv", [*argv, "--apply"])
    runpy.run_path(str(script), run_name="__main__")
    assert json.loads(path.read_bytes())["providers"] == ProviderConfig().model_dump()
