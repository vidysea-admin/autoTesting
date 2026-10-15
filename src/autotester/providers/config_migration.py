"""Plan, explicitly apply and reverse only exact historical provider triplets."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from autotester.schema.project import Project, ProviderConfig
from autotester.schema.provider_migration import (
    ProviderMigrationEntry,
    ProviderMigrationOutcome,
    ProviderMigrationPlan,
)
from autotester.store.filestore import write_bytes

_LEGACY = {"vision": "gemini", "agent": "langchain-fallback", "judge": "langchain-fallback"}
_SLUG = re.compile(r"^[a-z][a-z0-9-]*$")
_SPACE = re.compile(r"\s*")


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _project_path(root: Path, slug: str) -> Path:
    if not _SLUG.fullmatch(slug):
        raise ValueError("invalid_project_selection")
    path = root.resolve()/"projects"/slug/"project.json"
    if path.resolve() != path:
        raise ValueError("project_migration_path_escape")
    return path


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _providers_span(text: str) -> tuple[int, int]:
    decoder = json.JSONDecoder()
    cursor = _SPACE.match(text).end()+1
    while text[cursor:].strip() and text[cursor:].lstrip()[0] != "}":
        key, end = decoder.raw_decode(text, _SPACE.match(text, cursor).end())
        cursor = _SPACE.match(text, end).end()
        start = _SPACE.match(text, cursor+1).end()
        _, end = decoder.raw_decode(text, start)
        if key == "providers":
            return start, end
        cursor = _SPACE.match(text, end).end()+1
    raise ValueError("providers_missing")


def _replacement(raw: bytes, target: ProviderConfig) -> bytes:
    text = raw.decode("utf-8")
    start, end = _providers_span(text)
    replacement = json.dumps(target.model_dump(), ensure_ascii=False, sort_keys=True)
    return (text[:start]+replacement+text[end:]).encode("utf-8")


def _read_record(raw: bytes, slug: str) -> dict:
    record = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    if Project.model_validate(record).slug != slug:
        raise ValueError("project_identity_mismatch")
    return record


def plan_legacy_roles(root: Path, slugs: list[str]) -> ProviderMigrationPlan:
    """Read selected records only; exact raw JSON key/value match defines eligibility."""
    entries = []
    for slug in dict.fromkeys(slugs):
        path = _project_path(root, slug)
        entry = ProviderMigrationEntry(slug=slug, status="missing")
        if path.is_file():
            raw = path.read_bytes()
            entry.before_sha256 = _hash(raw)
            try:
                record = _read_record(raw, slug)
                providers = record.get("providers")
                partial = not isinstance(providers, dict) or set(providers) < set(_LEGACY)
                entry.status = "partial" if partial else "custom"
                if providers == _LEGACY:
                    entry.status, entry.target = "eligible", ProviderConfig()
                    entry.after_sha256 = _hash(_replacement(raw, entry.target))
            except (ValueError, TypeError, AttributeError):
                entry.status = "invalid"
        entries.append(entry)
    return ProviderMigrationPlan(root=str(root.resolve()), entries=entries)


def _backup_path(root: Path, entry: ProviderMigrationEntry) -> Path:
    path = (root.resolve()/".work/provider-migration-backups"
            /entry.before_sha256/(entry.slug+".json"))
    if path.resolve() != path:
        raise ValueError("migration_backup_path_escape")
    return path


def _migration_bytes(raw: bytes, entry: ProviderMigrationEntry) -> bytes:
    if (entry.target != ProviderConfig()
            or _read_record(raw, entry.slug).get("providers") != _LEGACY):
        raise ValueError("migration_requires_exact_original_and_approved_target")
    replacement = _replacement(raw, entry.target)
    if _hash(replacement) != entry.after_sha256:
        raise ValueError("migration_target_identity_mismatch")
    return replacement


def _payload(raw: bytes, backup: Path, entry: ProviderMigrationEntry, restore: bool) -> bytes:
    if restore:
        original = backup.read_bytes()
        if _hash(original) != entry.before_sha256:
            raise ValueError("migration_backup_identity_mismatch")
        _migration_bytes(original, entry)
        return original
    replacement = _migration_bytes(raw, entry)
    if backup.exists() and _hash(backup.read_bytes()) != entry.before_sha256:
        raise ValueError("migration_backup_identity_mismatch")
    if not backup.exists():
        write_bytes(backup, raw)
    return replacement


def _change_one(root: Path, entry: ProviderMigrationEntry,
                restore: bool) -> ProviderMigrationOutcome:
    outcome = ProviderMigrationOutcome(slug=entry.slug, status="skipped", reason="not_exact_legacy")
    if (entry.status != "eligible" or entry.target is None
            or entry.before_sha256 is None or entry.after_sha256 is None):
        return outcome
    path, backup = _project_path(root, entry.slug), _backup_path(root, entry)
    try:
        raw = path.read_bytes()
    except OSError:
        outcome.status, outcome.reason = "stale", "project_unavailable"
        return outcome
    current = _hash(raw)
    desired = entry.before_sha256 if restore else entry.after_sha256
    expected = entry.after_sha256 if restore else entry.before_sha256
    if current == desired:
        outcome.status, outcome.reason = "unchanged", "already_requested_state"
        return outcome
    if current != expected:
        outcome.status, outcome.reason = "stale", "project_changed_since_plan"
        return outcome
    try:
        replacement = _payload(raw, backup, entry, restore)
    except (OSError, ValueError, TypeError):
        outcome.status, outcome.reason = "stale", "plan_or_backup_invalid"
        return outcome
    if _hash(path.read_bytes()) != expected:
        outcome.status, outcome.reason = "stale", "project_changed_before_write"
        return outcome
    write_bytes(path, replacement)
    outcome.status, outcome.reason = ("restored" if restore else "applied"), "selected_exact_legacy"
    return outcome


def change_legacy_roles(root: Path, plan: ProviderMigrationPlan, selected: list[str], *,
                        restore: bool = False) -> list[ProviderMigrationOutcome]:
    """Explicit selection only; compare snapshots, preserve originals and refuse stale writes."""
    if str(root.resolve()) != plan.root or type(restore) is not bool:
        raise ValueError("migration_plan_root_or_mode_mismatch")
    entries = {entry.slug: entry for entry in plan.entries}
    if len(entries) != len(plan.entries) or any(slug not in entries for slug in selected):
        raise ValueError("migration_selection_not_in_plan")
    return [_change_one(root, entries[slug], restore) for slug in dict.fromkeys(selected)]
