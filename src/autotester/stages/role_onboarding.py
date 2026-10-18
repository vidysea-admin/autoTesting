"""Validate N role accounts across M platforms at onboarding time (T-208, MP4-MP5).

One job: turn the typed `Platform`/`RoleAccount` rows an onboarder submitted, plus the optional
per-account scope they typed and the env values they supplied, into the `SecretRef`s the project
declares -- or refuse with a message that names accounts, platforms and hosts but never a value.
`.env` writes go through `ui/env_editor.py` (the one write path) and key hygiene through
`ui/credential_guard.py`; nothing here reads a stored value or prints one (MPI1, MPI5).

Scope rule (MP5): an account's `SecretRef` scope is the platform's `allowed_domains` unless the
onboarder typed a narrower one, with the platform's `include_subdomains`. It is refused when it
admits a host outside the account's own platform: a typed domain the platform does not own, or a
sibling platform's host reached by the suffix match. The runtime `_host_matches` is stricter today;
this check is the declared-scope contract, so a loosened runtime cannot widen a stored account.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import ValidationError

from autotester.schema.platform import Platform
from autotester.schema.project import Project, SecretRef
from autotester.schema.role_account import RoleAccount
from autotester.ui.credential_guard import refuse_foreign_key
from autotester.ui.env_editor import InvalidEnvValue, set_env_values, validate_env_values

T = TypeVar("T", Platform, RoleAccount)


class OnboardingError(ValueError):
    """A refusal safe to show the onboarder: it names rows, keys and hosts, never a value."""


def safe_validation_message(exc: ValidationError) -> str:
    """Field paths and rule text only -- pydantic's `input` (the submitted text) is dropped."""
    return "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                     for err in exc.errors())


def _norm(host: str) -> str:
    return host.strip().lower().lstrip(".").rstrip(".")


def _admits(host: str, domain: str, include_subdomains: bool) -> bool:
    """The declared scope: `domain` itself, and its subdomains when `include_subdomains`."""
    h, d = _norm(host), _norm(domain)
    return bool(h) and (h == d or (include_subdomains and h.endswith("." + d)))


def _hosts_of(platform: Platform) -> set[str]:
    base = _norm(urlsplit(platform.base_url).hostname or "")
    return {_norm(d) for d in platform.allowed_domains} | ({base} if base else set())


def merge_by_id(old: Sequence[T], new: Sequence[T]) -> list[T]:
    """`new` replaces an `old` row with the same id in place; unmentioned rows stay."""
    fresh = {row.id: row for row in new}
    kept = [fresh.pop(row.id, row) for row in old]
    return kept + list(fresh.values())


def check_platforms(platforms: Sequence[Platform]) -> None:
    """Unique ids, at least one domain each, and a base URL its own domains cover."""
    seen: set[str] = set()
    for plat in platforms:
        if plat.id in seen:
            raise OnboardingError(f"platform {plat.id!r} is declared twice")
        seen.add(plat.id)
        base = _norm(urlsplit(plat.base_url).hostname or "")
        if not plat.allowed_domains or not base:
            raise OnboardingError(f"platform {plat.id!r} needs a base URL and at least one "
                                  "allowed domain")
        for domain in plat.allowed_domains:
            if "." not in _norm(domain) and _norm(domain) != "localhost":
                raise OnboardingError(
                    f"platform {plat.id!r}: {domain!r} is a bare top-level name, not a host; "
                    "declare the platform's own host (for example app.example.com)")
        if not any(_admits(base, d, True) for d in plat.allowed_domains):
            raise OnboardingError(f"platform {plat.id!r}: its base URL host {base!r} is not "
                                  "covered by its allowed domains")


def _refs_for(acct: RoleAccount, plat: Platform, scope: Sequence[str]) -> list[SecretRef]:
    domains = [_norm(d) for d in scope if _norm(d)] or [_norm(d) for d in plat.allowed_domains]
    return [SecretRef(key=key, description=f"{acct.role} {what} on {plat.name}", domains=domains,
                      include_subdomains=plat.include_subdomains)
            for key, what in ((acct.username_key, "username"), (acct.password_key, "password"))]


def check_scopes(platforms: Sequence[Platform], accounts: Sequence[RoleAccount],
                 refs: Mapping[str, Sequence[SecretRef]]) -> None:
    """MP5: refuse an account whose scope admits a host outside its own platform."""
    by_id = {p.id: p for p in platforms}
    for acct in accounts:
        plat = by_id[acct.platform_id]
        own = _hosts_of(plat)
        others = {h for p in platforms if p.id != plat.id for h in _hosts_of(p)} - own
        for ref in refs[acct.id]:
            outside = {_norm(d) for d in ref.domains
                       if not any(_admits(d, o, plat.include_subdomains) for o in own)}
            sibling = {h for h in others
                       if any(_admits(h, d, ref.include_subdomains) for d in ref.domains)}
            if outside | sibling:
                raise OnboardingError(
                    f"account {acct.id!r} on platform {plat.id!r}: the scope of {ref.key} "
                    f"admits {', '.join(sorted(outside | sibling))}, outside that platform")


def _check_structure(platforms: Sequence[Platform], accounts: Sequence[RoleAccount]) -> None:
    check_platforms(platforms)
    ids = {p.id for p in platforms}
    seen_accounts: set[str] = set()
    owner: dict[str, str] = {}
    for acct in accounts:
        if acct.id in seen_accounts:
            raise OnboardingError(f"account {acct.id!r} is declared twice")
        seen_accounts.add(acct.id)
        if acct.platform_id not in ids:
            raise OnboardingError(f"account {acct.id!r} names platform {acct.platform_id!r}, "
                                  "which is not declared")
        if acct.username_key == acct.password_key:
            raise OnboardingError(f"account {acct.id!r} uses one key for username and password")
        for key in (acct.username_key, acct.password_key):
            if key in owner and owner[key] != acct.id:
                raise OnboardingError(
                    f"key {key} is used by accounts {owner[key]!r} and {acct.id!r}; "
                    "each account needs its own keys")
            owner[key] = acct.id


def validate_accounts(platforms: Sequence[Platform], accounts: Sequence[RoleAccount],
                      scopes: Mapping[str, Sequence[str]],
                      values: Mapping[str, str]) -> list[SecretRef]:
    """The `SecretRef`s for every account, or an `OnboardingError`. `values` is only checked
    for keys no account declares (named, never echoed)."""
    _check_structure(platforms, accounts)
    by_id = {p.id: p for p in platforms}
    refs = {a.id: _refs_for(a, by_id[a.platform_id], scopes.get(a.id, ())) for a in accounts}
    check_scopes(platforms, accounts, refs)
    flat = [ref for acct in accounts for ref in refs[acct.id]]
    stray = sorted(set(values) - {ref.key for ref in flat})
    if stray:
        raise OnboardingError(f"a value was given for undeclared key(s): {', '.join(stray)}")
    return flat


def rescoped_keys(project: Project, refs: Sequence[SecretRef], accounts: Sequence[RoleAccount],
                  present: Mapping[str, str]) -> list[str]:
    """Keys whose stored value this submission would re-bind: an already-declared key whose
    domain scope, subdomain rule or platform changes, or a new declaration of a key that
    already holds a value in `.env`. Changing any of these is a credential action (MP6)."""
    stored = {s.key: s for s in project.secrets}
    plat_of = {k: a.platform_id for a in project.role_accounts or []
               for k in (a.username_key, a.password_key)}
    new_plat = {k: a.platform_id for a in accounts for k in (a.username_key, a.password_key)}
    moved: list[str] = []
    for ref in refs:
        prev = stored.get(ref.key)
        if prev is None:
            if ref.key in present:
                moved.append(ref.key)
            continue
        if (sorted(_norm(d) for d in prev.domains), prev.include_subdomains) != (
                sorted(_norm(d) for d in ref.domains), ref.include_subdomains) or (
                ref.key in plat_of and plat_of[ref.key] != new_plat.get(ref.key)):
            moved.append(ref.key)
    return sorted(moved)


def check_key_namespace(project: Project, refs: Sequence[SecretRef]) -> None:
    """AU21 through the one gate every project route uses (`refuse_foreign_key`)."""
    for ref in refs:
        try:
            refuse_foreign_key(project, ref.key)
        except HTTPException as exc:
            raise OnboardingError(str(exc.detail)) from exc


def check_values(values: Mapping[str, str]) -> None:
    """Render the whole batch through the env editor's validator; nothing is written."""
    try:
        validate_env_values(dict(values))
    except InvalidEnvValue as exc:
        raise OnboardingError(str(exc)) from exc


def write_values(env_path: Path, values: Mapping[str, str]) -> None:
    """The one `.env` write: validated as a batch, then atomically merged by the env editor."""
    check_values(values)
    set_env_values(env_path, dict(values))
