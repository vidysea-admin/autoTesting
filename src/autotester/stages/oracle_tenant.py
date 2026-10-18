"""Cross-tenant oracle: rows tenant A can see that are not A's are counted, P0 (MP18, MP20).

One job: read each declared list view as tenant A (one page), learn which rows belong to the other
tenant (its own list, or a declared own-row count), try up to three id-swap reads of the other
tenant's rows through the detail URL, and report ONE `DATA_LEAK` finding per view whose foreign rows
reached A. The finding holds only what `stages/leak_evidence.py::collect_leak_evidence` lets
through -- a count, column headers, at most five HMAC ids and a URL template (MPI1). The rows
themselves live in local variables of this module and are never logged, stored or sent to a model.

Deterministic and bounded: no provider is called; `stages/authz_probe.py` has already passed the
signed-approval and ceiling gate (A5), and its `Budget` stops the pass at the request cap or the
wall clock, after which `probe_tenant` names what was left unprobed. Entry point for the
oracle registry: `run(context)` (interface in `schema/oracle_context.py`).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from datetime import datetime
from urllib.parse import quote

from autotester.schema.authz_probe import ProbeLog, StopReason, TenantProbe, UnprobedItem
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext
from autotester.stages.authz_probe import (
    ID_SWAP,
    MAX_SWAPS_PER_ENDPOINT,
    ProbeSession,
    abs_url,
    evidence_url,
    finding_id,
    open_session,
    read_safely,
    tenant_cost,
    write_log,
)
from autotester.stages.leak_evidence import collect_leak_evidence, write_finding

Row = Mapping[str, object]


def _steps(probe: TenantProbe) -> list[str]:
    names = ["list"]
    if probe.owner_role_id:
        names.append("owner_list")
    if probe.detail_url:
        names += [f"swap_{i}" for i in range(1, MAX_SWAPS_PER_ENDPOINT + 1)]
    return names


def _unprobed(probe: TenantProbe, names: list[str], reason: StopReason) -> list[UnprobedItem]:
    return [UnprobedItem(item=f"tenant:{probe.id}:{n}", reason=reason) for n in names]


def _ids(rows: list[Row], id_field: str) -> list[str]:
    """Distinct ids of `rows` in order; held in memory only, hashed by the evidence collector."""
    return list(dict.fromkeys(str(r[id_field]) for r in rows if r.get(id_field) is not None))


def _foreign_in_list(probe: TenantProbe, rows: list[Row], owner_ids: list[str]) -> list[Row]:
    """Rows of A's list that are not A's: the other tenant's, or the surplus over the declared one.

    With a declared count nothing says WHICH rows are foreign, so the surplus is kept without its
    id field: the count and the headers are evidence, an arbitrary id would not be."""
    if probe.owner_role_id is not None:
        return [r for r in rows if r.get(probe.id_field) is not None
                and str(r[probe.id_field]) in owner_ids]
    surplus = rows[probe.declared_own_count or 0:]
    return [{k: v for k, v in r.items() if k != probe.id_field} for r in surplus]


def _swap_reads(probe: TenantProbe, prep: ProbeSession, owner_ids: list[str],
                unprobed: list[UnprobedItem]) -> list[Row]:
    """Up to three detail reads as the viewer with the owner's ids; a 2xx with a row is foreign."""
    found: list[Row] = []
    chosen = owner_ids[:MAX_SWAPS_PER_ENDPOINT]
    for index, raw in enumerate(chosen, start=1):
        stop = prep.budget.take()
        if stop is not None:
            unprobed += _unprobed(probe, [f"swap_{i}" for i in range(index, len(chosen) + 1)], stop)
            return found
        url = abs_url(prep.platform, (probe.detail_url or "").replace(ID_SWAP, quote(raw, safe="")))
        reply = read_safely(prep.transport, probe.viewer_role_id, url)
        if reply is None:
            unprobed += _unprobed(probe, [f"swap_{index}"], StopReason.TRANSPORT_ERROR)
        elif reply.ok and reply.rows:
            found.append(reply.rows[0])
    if len(owner_ids) > MAX_SWAPS_PER_ENDPOINT:
        unprobed.append(UnprobedItem(item=f"tenant:{probe.id}:swap_beyond_{MAX_SWAPS_PER_ENDPOINT}",
                                     reason=StopReason.SWAP_LIMIT))
    return found


def _merge(*groups: list[Row], id_field: str) -> list[Row]:
    """One row per id (seen in the list and by id swap = once); id-less rows each count."""
    seen: dict[str, Row] = {}
    loose: list[Row] = []
    for row in (r for g in groups for r in g):
        key = row.get(id_field)
        if key is None:
            loose.append(row)
        else:
            seen.setdefault(str(key), row)
    return [*seen.values(), *loose]


def _read_rows(probe: TenantProbe, prep: ProbeSession, role_id: str, name: str,
               unprobed: list[UnprobedItem]) -> list[Row] | None:
    """One list page as `role_id`; None (rest of the view unprobed, with why) when it cannot go."""
    names = _steps(probe)
    rest = names[names.index(name):]
    stop = prep.budget.take()
    if stop is not None:
        unprobed += _unprobed(probe, rest, stop)
        return None
    reply = read_safely(prep.transport, role_id, abs_url(prep.platform, probe.list_url))
    if reply is None:
        unprobed += _unprobed(probe, rest, StopReason.TRANSPORT_ERROR)
        return None
    if not reply.ok:  # a 401/403/5xx is not "no rows": the view was not probed, and says so
        unprobed += _unprobed(probe, rest, StopReason.LIST_STATUS)
        return None
    return list(reply.rows)


def _probe_view(probe: TenantProbe, prep: ProbeSession,
                unprobed: list[UnprobedItem]) -> MultiRoleFinding | None:
    viewer_rows = _read_rows(probe, prep, probe.viewer_role_id, "list", unprobed)
    if viewer_rows is None:
        return None
    owner_ids: list[str] = []
    if probe.owner_role_id:
        owner_rows = _read_rows(probe, prep, probe.owner_role_id, "owner_list", unprobed)
        if owner_rows is None:
            return None
        owner_ids = _ids(owner_rows, probe.id_field)
    swapped = _swap_reads(probe, prep, owner_ids, unprobed) if probe.detail_url else []
    foreign = _merge(_foreign_in_list(probe, viewer_rows, owner_ids), swapped,
                     id_field=probe.id_field)
    count = len(foreign)
    if count == 0:
        return None
    fid = finding_id("tenant", probe.id)
    evidence = collect_leak_evidence(
        project_slug=prep.project.slug, run_dir=prep.run_dir, finding_id=fid, rows=foreign,
        id_field=probe.id_field, url=evidence_url(probe.list_url))
    return MultiRoleFinding(
        finding_id=fid, finding_class=FindingClass.DATA_LEAK,
        title=f"Tenant isolation: {probe.viewer_role_id} sees {count} rows it does not own",
        role=probe.viewer_role_id, platform_id=prep.platform.id,
        url_template=evidence.url_template,
        steps=[f"login {probe.viewer_role_id}", f"goto {evidence.url_template}"],
        count=count, oracle=OracleName.TENANT, leak_evidence=evidence)


def probe_tenant(prep: ProbeSession) -> tuple[list[MultiRoleFinding], list[UnprobedItem]]:
    """Probe every tenant view in the plan, within `prep.budget`. Writes nothing itself."""
    findings: list[MultiRoleFinding] = []
    unprobed: list[UnprobedItem] = []
    for probe in prep.plan.tenant_probes:
        found = _probe_view(probe, prep, unprobed)
        if found is not None:
            findings.append(found)
    return findings, unprobed


def run_tenant_pass(context: OracleContext, *, clock: Callable[[], float],
              sleep: Callable[[float], None], now: datetime | None = None,
              ) -> list[MultiRoleFinding]:
    """Gate, probe, store the findings and the log. A refused plan raises with nothing sent."""
    prep = open_session(context, OracleName.TENANT, clock=clock, sleep=sleep, now=now)
    before = prep.budget.sent
    findings, unprobed = probe_tenant(prep)
    for finding in findings:
        write_finding(prep.run_dir, finding)
    write_log(prep.run_dir, ProbeLog(
        oracle=OracleName.TENANT, platform_id=prep.platform.id,
        planned=sum(tenant_cost(p) for p in prep.plan.tenant_probes),
        sent=prep.budget.sent - before, elapsed_s=round(prep.budget.elapsed(), 3),
        findings=len(findings), unprobed=unprobed))
    return findings


def run(context: OracleContext) -> list[MultiRoleFinding]:
    """The oracle registry's entry point (`schema/oracle_context.py`, HOW TO WRITE AN ORACLE)."""
    return run_tenant_pass(context, clock=time.monotonic, sleep=time.sleep)
