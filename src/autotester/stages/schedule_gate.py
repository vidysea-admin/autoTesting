"""The TS5 gate: a scheduled run may start only under the credential-derived approval (D-068).

`credential_state` classifies, read-only, why a project's credentials do or do not cover its
target. `credential_gate` is the `TickDeps.gate` the tick asks before it touches the queue: it
returns a refusal sentence (state value first, never a credential value) or None. It runs in
ADDITION to the owner's rights (HO24), so no role skips it (AU15). Only a provisioned state
reaches `covering_approval`, which mints or reuses the signed audit row; every refused state
writes nothing.
"""

from __future__ import annotations

from collections.abc import Callable

from autotester.browser.secrets import SecretStore, _host_matches, host_of
from autotester.core.consent import ApprovalRequired
from autotester.schema.crawl import CrawlBounds
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.schema.schedule import CredentialState
from autotester.stages.explore_consent import covering_approval, signing_key_available
from autotester.stages.scheduler import Slot
from autotester.store.project_store import ProjectStore

_SAYS = {
    CredentialState.NO_SECRETREF:
        "this project declares no credentials, so a scheduled run has no approval; "
        "declare them on the Credentials page",
    CredentialState.SECRETREF_WITHOUT_VALUE:
        "a credential is declared but no value is set; set it on the Credentials page",
    CredentialState.TARGET_OUTSIDE_DOMAINS:
        "the credentials are not scoped to this project's target host or allowed domains",
}


def credential_state(project: Project, store: ProjectStore,
                     secrets: SecretStore | None = None) -> CredentialState:
    """Read-only. Reads which declared keys have a value, never the values themselves."""
    if not project.secrets:
        return CredentialState.NO_SECRETREF
    secrets = secrets or SecretStore.load(project, store.paths.env_file, strict=False)
    with_value = [ref for ref in project.secrets if secrets.has_value(ref.key)]
    if not with_value:
        return CredentialState.SECRETREF_WITHOUT_VALUE
    host = host_of(project.base_url)
    if (not host or not project.allows_domain(host) or not any(
            _host_matches(host, d, ref.include_subdomains) for ref in with_value
            for d in ref.domains)):
        return CredentialState.TARGET_OUTSIDE_DOMAINS
    return CredentialState.PROVISIONED


def refusal_for(project: Project, store: ProjectStore,
                secrets: SecretStore | None = None) -> str | None:
    """The read-only refusal, for `--dry-run` and as the gate's first step: the credential state,
    then whether the approval could be minted (a lost signing key blocks the real tick). Writes
    nothing: no approval row, no key, no lock file."""
    state = credential_state(project, store, secrets)
    if state is not CredentialState.PROVISIONED:
        return f"{state.value}: {_SAYS[state]}"
    if not signing_key_available(store):
        return "approval_required: the approval signing key is unavailable"
    return None


def credential_gate(project: Project, store: ProjectStore, bounds: CrawlBounds | None = None,
                    secrets: SecretStore | None = None) -> Callable[[Slot], str | None]:
    """The `TickDeps.gate` for one project. `bounds` are the run's brakes (the approval's own)."""
    def gate(slot: Slot) -> str | None:
        refusal = refusal_for(project, store, secrets)
        if refusal is not None:
            return refusal
        try:
            covering_approval(project, store, bounds or CrawlBounds(),
                              kind=ApprovalKind.LIVE_CASE, secrets=secrets)
        except ApprovalRequired as exc:
            return f"approval_required: {exc}"
        return None
    return gate
