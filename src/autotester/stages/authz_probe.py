"""The bounded-probe session both authorisation oracles share: gate, budget, log (MP20, A5, MPI4).

One job: everything that must hold BEFORE and WHILE `oracle_tenant` / `oracle_privilege` send a
request, so the two oracles carry only their own judgement. It reuses the T-154 bounded pass
(`stages/adversarial.py`, D-018) instead of inventing a second probe concept:
  * the planned probe count must be covered by a signed `RunApproval` of kind ADVERSARIAL for the
    platform's exact base URL, checked through `core/consent.py::require_project_approval`
    (the same rule that gates a production project: D-088);
  * a code-side `PROBE_CEILING` refuses an oversized plan whatever an approval would permit
    (`ProbeCeilingExceeded`, the class the adversarial pass already raises);
  * a refusal sends nothing and appends one non-secret `ProbeRefusal` line to
    `projects/<slug>/authz/refusals.jsonl` (the shape AD7 already defined).
While probing, `Budget` enforces the per-platform request cap, the wall clock and the pacing
interval, and when a bound stops a probe the oracle names what was left (`UnprobedItem`). The cap
and the clock are shared by the two oracles through the `*_log.json` files they leave behind.
No provider is imported here or in either oracle: the probes are deterministic (MP20, MPI1).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urljoin, urlsplit

from autotester.browser.secrets import SecretStore
from autotester.core.consent import ApprovalRequired, require_project_approval
from autotester.core.redact import Redactor
from autotester.schema.ai_probe import ProbeRefusal
from autotester.schema.approval import RunApproval
from autotester.schema.authz_probe import (
    AuthzPlan,
    PrivilegeProbe,
    ProbeLog,
    ProbeReply,
    ReadTransport,
    StopReason,
    TenantProbe,
)
from autotester.schema.enums import ApprovalKind
from autotester.schema.multi_role_enums import OracleName
from autotester.schema.oracle_context import OracleContext
from autotester.schema.platform import Platform
from autotester.schema.project import Project
from autotester.stages.adversarial import AdversarialBlocked, ProbeCeilingExceeded
from autotester.stages.leak_evidence import templatise_url
from autotester.store.filestore import append_jsonl, read_json, write_json
from autotester.store.project_store import ProjectStore

PROBE_CEILING = 60
"""Absolute planned requests per platform per run, in code, whatever an approval would permit.
Proposed by the build (as `adversarial.PROBE_CEILING` was); the checker and the owner confirm."""
MAX_SWAPS_PER_ENDPOINT = 3
"""Id-swap reads per detail endpoint (MP20, MPI4). One list page per list view is structural:
a list view is read once, so there is no knob."""
APPROVAL_KIND = ApprovalKind.ADVERSARIAL
"""Replaying another role's requests is adversarial by nature, so a human-granted row is needed:
this kind is never account-derived (`core/consent.py::ACCOUNT_KINDS`)."""
AUTHZ_DIR = "authz"
PLAN_FILE = "authz_plan.json"
ID_SWAP = "{id}"


class NoProbeTransport(RuntimeError):
    """The scenario's port cannot read as a role, so there is nothing to probe with."""


class AuthzPlanMissing(RuntimeError):
    """The scenario declared no `authz_plan.json`: an oracle selected without a plan is an error."""


def tenant_cost(probe: TenantProbe) -> int:
    """Upper bound of requests for one tenant probe: viewer list, owner list, id swaps."""
    swaps = MAX_SWAPS_PER_ENDPOINT if probe.detail_url else 0
    return 1 + (probe.owner_role_id is not None) + swaps


def privilege_cost(probe: PrivilegeProbe) -> int:
    """Reads, plus two per role-assign control (the attempt and its possible revert)."""
    return len(probe.read_urls) + 2 * len(probe.controls)


def plan_size(plan: AuthzPlan) -> int:
    """The planned probe count the approval must cover: both oracles, the whole plan."""
    return (sum(tenant_cost(p) for p in plan.tenant_probes)
            + sum(privilege_cost(p) for p in plan.privilege_probes))


def abs_url(platform: Platform, url: str) -> str:
    """`url` (a path or absolute) resolved against the platform's base URL."""
    return urljoin(platform.base_url, url)


def evidence_url(url: str) -> str:
    """Path and query of `url` with ids and values as placeholders: no host, no id (MPI1)."""
    parts = urlsplit(url)
    return templatise_url(parts.path + (f"?{parts.query}" if parts.query else ""))


def finding_id(kind: str, probe_id: str, suffix: str = "") -> str:
    return f"authz-{kind}-{probe_id}{'-' + suffix if suffix else ''}"[:64]


def read_safely(transport: ReadTransport, role_id: str, url: str) -> ProbeReply | None:
    """One read; a transport failure is `None` (the caller names the probe unprobed)."""
    try:
        return transport.read(role_id, url)
    except Exception:  # an error message could carry a page; the category is all that is kept
        return None


def _in_scope(project: Project, platform: Platform, url: str) -> bool:
    host = urlsplit(url).hostname
    return bool(host) and (project.allows_domain(host) or any(
        host == d or host.endswith(f".{d}") for d in platform.allowed_domains))


def _check_scope(project: Project, platform: Platform, plan: AuthzPlan) -> None:
    urls = [platform.base_url]
    for t in plan.tenant_probes:
        urls += [t.list_url, *([t.detail_url] if t.detail_url else [])]
    for p in plan.privilege_probes:
        urls += [*p.read_urls, *(c.url for c in p.controls)]
    if not all(_in_scope(project, platform, abs_url(platform, u)) for u in urls):
        raise AdversarialBlocked("a planned URL is outside the platform's allowed_domains")


def _log_refusal(store: ProjectStore, redactor: Redactor, *, target: str, planned: int,
                 now: datetime, error: Exception) -> None:
    """AD7: target, time, count and the gate's own words. Never a URL path or a probe detail."""
    append_jsonl(store.paths.dir / AUTHZ_DIR / "refusals.jsonl", ProbeRefusal(
        target=redactor.scrub(target), timestamp=now.isoformat(), requested_probes=planned,
        reason=redactor.scrub(str(error))))


def gate(*, store: ProjectStore, project: Project, platform: Platform, plan: AuthzPlan,
         redactor: Redactor, now: datetime) -> RunApproval:
    """Every check that must hold before the first request leaves; raises, never sends."""
    planned = plan_size(plan)
    try:
        _check_scope(project, platform, plan)
        approval = require_project_approval(
            store.list_approvals(), project=project, kind=APPROVAL_KIND, target=platform.base_url,
            probes=planned, wall_clock_s=plan.wall_clock_s, production=project.production,
            now=now)
        if planned > PROBE_CEILING:
            raise ProbeCeilingExceeded(
                f"planned probes {planned} exceed the code ceiling {PROBE_CEILING}; "
                "no approval can raise it")
    except (ApprovalRequired, AdversarialBlocked) as error:
        _log_refusal(store, redactor, target=platform.base_url, planned=planned, now=now,
                     error=error)
        raise
    return approval


class Budget:
    """Per-platform request cap, wall clock and pacing, shared across the two oracles."""

    def __init__(self, *, cap: int, wall_clock_s: float, interval_s: float,
                 clock: Callable[[], float], sleep: Callable[[float], None],
                 sent: int = 0, used_s: float = 0.0) -> None:
        self.cap, self.sent, self.stop = cap, sent, None
        self._wall, self._interval = wall_clock_s - used_s, interval_s
        self._clock, self._sleep, self._start = clock, sleep, clock()
        self._paced = False

    def elapsed(self) -> float:
        return max(self._clock() - self._start, 0.0)

    def take(self, reserve: int = 1) -> StopReason | None:
        """Pay for one request (`reserve` = how many the caller may need, e.g. attempt + revert).

        Returns the reason it must stop, or None and the request is counted. Sticky once hit."""
        if self.stop is None and self.sent + reserve > self.cap:
            self.stop = StopReason.REQUEST_CAP
        if self.stop is None and self.elapsed() >= self._wall:
            self.stop = StopReason.WALL_CLOCK
        if self.stop is not None:
            return self.stop
        if self._paced and self._interval > 0:
            self._sleep(self._interval)
        self._paced = True
        self.sent += 1
        return None

    def extra(self) -> None:
        """Count a request that was reserved by `take` (a revert), never refused."""
        self.sent += 1


def prior_usage(run_dir: Path, platform_id: str, oracle: OracleName) -> tuple[int, float]:
    """Requests and seconds the OTHER oracle already spent on this platform in this run."""
    sent, used = 0, 0.0
    for other in OracleName:
        if other is oracle:
            continue
        log = read_json(run_dir / AUTHZ_DIR / f"{other.value}_log.json", ProbeLog)
        if log is not None and log.platform_id == platform_id:
            sent, used = sent + log.sent, used + log.elapsed_s
    return sent, used


def write_log(run_dir: Path, log: ProbeLog) -> Path:
    path = run_dir / AUTHZ_DIR / f"{log.oracle.value}_log.json"
    write_json(path, log)
    return path


class ProbeSession(NamedTuple):
    project: Project
    platform: Platform
    plan: AuthzPlan
    transport: ReadTransport
    budget: Budget
    run_dir: Path
    store: ProjectStore


def open_session(context: OracleContext, oracle: OracleName, *, clock: Callable[[], float],
            sleep: Callable[[float], None], now: datetime | None = None) -> ProbeSession:
    """Load the plan, pass the gate, build the budget. Raises with nothing sent."""
    run_dir = Path(context.run_dir)
    plan = read_json(run_dir / PLAN_FILE, AuthzPlan)
    if plan is None:
        raise AuthzPlanMissing(PLAN_FILE)
    if not isinstance(context.port, ReadTransport):
        raise NoProbeTransport(type(context.port).__name__)
    store = ProjectStore(context.project_slug)
    project = store.load_project()
    platform = next((p for p in (project.effective_platforms() if project else [])
                     if p.id == plan.platform_id), None)
    if project is None or platform is None:
        raise AdversarialBlocked("the plan names a project or platform that does not exist")
    redactor = SecretStore.load(project, store.paths.env_file, strict=False).redactor()
    gate(store=store, project=project, platform=platform, plan=plan, redactor=redactor,
         now=now or datetime.now(UTC))
    sent, used = prior_usage(run_dir, platform.id, oracle)
    budget = Budget(cap=min(plan.request_cap, PROBE_CEILING), wall_clock_s=plan.wall_clock_s,
                    interval_s=plan.request_interval_s, clock=clock, sleep=sleep,
                    sent=sent, used_s=used)
    return ProbeSession(project, platform, plan, context.port, budget, run_dir, store)
