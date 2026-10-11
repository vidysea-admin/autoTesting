"""ADVERSARIAL: a bounded pass of file-defined probes at one AI endpoint. It records, never judges.

Contract: qa/contracts/adversarial.md AD1-AD7 (D-017, D-018), core-invariants C5/C7. This is the
only code path that sends probes, and it sends nothing until every gate has held: probe files
load, the endpoint host is inside `allowed_domains`, no secret rides in any input, a signed
`ApprovalKind.ADVERSARIAL` row names this exact endpoint with a probe count at or above the plan
and the stated `production` flag (AD1-AD3), and the plan is under the code's own `PROBE_CEILING`
(AD6). A refusal sends nothing and appends one non-secret line to `refusals.jsonl` (AD7). What a
reply MEANS is settled elsewhere, by the independent judge; this module builds no verdict (AD5).

The transport is an injected `send(endpoint, prompt) -> AiReply`; no HTTP client lives here.
Probes are `.md` files under `prompts/probes/` (AD4): a `# name` title, free description text,
then one `## heading` section per probe whose body is the probe text.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit

from autotester.core.consent import ApprovalRequired, require_approval
from autotester.core.ids import run_id as new_run_id
from autotester.core.paths import RepoDocs
from autotester.core.redact import Redactor
from autotester.schema.ai_check import AiExchange, AiReply
from autotester.schema.ai_probe import ProbeRecord, ProbeRefusal, ProbeRun, ProbeSet
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.stages.ai_capture import CaptureWithheld, Send
from autotester.store.filestore import append_jsonl, write_json
from autotester.store.project_store import ProjectStore

PROBE_CEILING = 50
"""Absolute probes per pass, in code, whatever an approval would permit (AD6). Proposed by the
build; the checker and the owner confirm the number."""


class AdversarialBlocked(ValueError):
    """The pass cannot start: probe files unusable or the host is outside `allowed_domains`."""


class ProbeCeilingExceeded(ApprovalRequired):
    """The plan is above `PROBE_CEILING`; no approval can raise it (AD6)."""


def parse_probe_set(name: str, text: str) -> ProbeSet:
    """A probe file's title, description and one probe per `## ` section. Empty sections drop."""
    description: list[str] = []
    probes: list[str] = []
    section: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            section = []
            probes.append("")
            continue
        if section is not None:
            section.append(line)
            probes[-1] = "\n".join(section).strip()
        elif not line.startswith("# "):
            description.append(line)
    return ProbeSet(name=name, description=" ".join(description).strip(),
                    probes=[p for p in probes if p])


def load_probe_sets(folder: Path, names: list[str] | None = None) -> list[ProbeSet]:
    """The named sets (default: every `*.md`, sorted). A missing, unnamed or empty set blocks."""
    if not folder.is_dir():
        raise AdversarialBlocked(f"probe folder not found: {folder.name}")
    wanted = names if names is not None else sorted(p.stem for p in folder.glob("*.md"))
    if not wanted:
        raise AdversarialBlocked("no probe files found; nothing to send")
    sets = []
    for name in wanted:
        path = folder / f"{name}.md"
        if not path.is_file():
            raise AdversarialBlocked(f"probe set '{name}' has no file")
        parsed = parse_probe_set(name, path.read_text(encoding="utf-8"))
        if not parsed.probes:
            raise AdversarialBlocked(f"probe set '{name}' is empty")
        sets.append(parsed)
    return sets


def _check_inputs(project: Project, endpoint: str, sets: list[ProbeSet],
                  approvals: list[RunApproval], redactor: Redactor) -> None:
    host = urlsplit(endpoint).hostname
    if not host or not project.allows_domain(host):
        raise AdversarialBlocked("endpoint host is not inside the project's allowed_domains")
    try:
        texts = [project.slug, endpoint, *(p for s in sets for p in s.probes),
                 *(a.model_dump_json() for a in approvals)]
        for text in texts:
            redactor.assert_clean(text)
    except ValueError:
        raise CaptureWithheld("run input carries a secret value; nothing was sent") from None


def _gate(*, project: Project, endpoint: str, sets: list[ProbeSet], planned: int,
          approvals: list[RunApproval], redactor: Redactor, wall_clock_s: float,
          production: bool, now: datetime) -> RunApproval:
    """Every check that must hold before the first byte leaves; raises, never sends."""
    _check_inputs(project, endpoint, sets, approvals, redactor)
    approval = require_approval(
        approvals, project=project.slug, kind=ApprovalKind.ADVERSARIAL, target=endpoint,
        probes=planned, wall_clock_s=wall_clock_s, production=production, now=now)
    if planned > PROBE_CEILING:
        raise ProbeCeilingExceeded(
            f"planned probes {planned} exceed the code ceiling {PROBE_CEILING}; "
            "no approval can raise it")
    return approval


def _log_refusal(store: ProjectStore, redactor: Redactor, *, endpoint: str, planned: int,
                 now: datetime, error: Exception) -> None:
    """AD7: target, time, count and reason. Never a probe: the reason is the gate's own text."""
    path = store.paths.dir / "ai" / "adversarial" / "refusals.jsonl"
    append_jsonl(path, ProbeRefusal(
        target=redactor.scrub(endpoint), timestamp=now.isoformat(), requested_probes=planned,
        reason=redactor.scrub(str(error))))


def _record(probe_set: str, prompt: str, reply: AiReply | None, error: str | None,
            latency_s: float, redactor: Redactor) -> ProbeRecord:
    scrub = redactor.scrub
    return ProbeRecord(probe_set=probe_set, exchange=AiExchange(
        prompt=scrub(prompt), response=scrub(reply.text) if reply else "",
        status=reply.status if reply else None, latency_s=max(latency_s, 0.0),
        tools_called=[scrub(t) for t in reply.tools_called] if reply else [],
        handoffs=[scrub(h) for h in reply.handoffs] if reply else [], error=error))


def _fire(send: Send, endpoint: str, sets: list[ProbeSet], redactor: Redactor,
          wall_clock_s: float, clock: Callable[[], float]) -> tuple[list[ProbeRecord], int]:
    """Send each probe in set order until the wall clock runs out; (records, unsent count)."""
    pending = [(s.name, p) for s in sets for p in s.probes]
    records: list[ProbeRecord] = []
    started = clock()
    for name, prompt in pending:
        if clock() - started >= wall_clock_s:
            break
        begun = clock()
        try:
            reply: AiReply | None = send(endpoint, prompt)
            error = None
        except Exception:  # any transport failure is an observation, named by a fixed category
            reply, error = None, "transport_error"
        records.append(_record(name, prompt, reply, error, clock() - begun, redactor))
    return records, len(pending) - len(records)


def run_adversarial(
    *, store: ProjectStore, project: Project, endpoint: str, send: Send, redactor: Redactor,
    production: bool, probe_sets: list[str] | None = None, probes_dir: Path | None = None,
    wall_clock_s: float = 120.0, clock: Callable[[], float] = time.monotonic,
    now: datetime | None = None,
) -> ProbeRun:
    """Run the bounded pass and return (and store) its record.

    Raises `ApprovalRequired` (or `ProbeCeilingExceeded`), `AdversarialBlocked` or
    `CaptureWithheld` with nothing sent; each is logged to `refusals.jsonl` first (AD7)."""
    if not isfinite(wall_clock_s) or wall_clock_s < 0:
        raise ValueError("wall_clock_s must be finite and nonnegative")
    moment = now or datetime.now(UTC)
    planned = 0
    try:
        sets = load_probe_sets(probes_dir or RepoDocs().prompts_dir / "probes", probe_sets)
        planned = sum(len(s.probes) for s in sets)
        approval = _gate(
            project=project, endpoint=endpoint, sets=sets, planned=planned,
            approvals=store.list_approvals(), redactor=redactor, wall_clock_s=wall_clock_s,
            production=production, now=moment)
    except (ApprovalRequired, AdversarialBlocked, CaptureWithheld) as error:
        _log_refusal(store, redactor, endpoint=endpoint, planned=planned, now=moment, error=error)
        raise
    run_id = new_run_id("adv")
    records, unsent = _fire(send, endpoint, sets, redactor, wall_clock_s, clock)
    run = ProbeRun(
        run_id=run_id, project=project.slug, endpoint=redactor.scrub(endpoint),
        production=production, probe_sets=[s.name for s in sets], approval_id=approval.id,
        planned_probes=planned, approved_probes=approval.max_probes, ceiling=PROBE_CEILING,
        cap_hit=unsent > 0, unsent_probes=unsent, records=records)
    try:
        redactor.assert_clean(run.model_dump_json())
    except ValueError:
        raise CaptureWithheld("a secret survived scrubbing; the record was withheld") from None
    write_json(store.paths.dir / "ai" / "adversarial" / run_id / "run.json", run)
    return run
