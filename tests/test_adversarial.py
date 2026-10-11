"""Offline tests of the bounded adversarial pass: adversarial.md AD1-AD7, CN1, CN5-CN7, C5, C7.

Every send goes through a counting fake; nothing here opens a socket or calls a model."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from autotester.core.consent import ApprovalRequired
from autotester.core.redact import Redactor
from autotester.schema.ai_check import AiReply
from autotester.schema.ai_probe import ProbeRefusal, ProbeRun
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.stages import adversarial
from autotester.stages.adversarial import (
    PROBE_CEILING,
    AdversarialBlocked,
    ProbeCeilingExceeded,
    load_probe_sets,
    run_adversarial,
)
from autotester.stages.ai_capture import CaptureWithheld
from autotester.store.project_store import ProjectStore

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "autotester"
URL = "https://llm.test/chat"
NOW = datetime(2026, 10, 11, tzinfo=UTC)
SECRET = "sk-live-1234567890abcdef"
BODY = "ZZPROBE-BODY-MARKER"


class Counting:
    """The transport seam: records every call, so 'nothing was sent' is asserted here."""

    def __init__(self, text: str = "I cannot help with that.") -> None:
        self.calls: list[tuple[str, str]] = []
        self.text = text

    def __call__(self, endpoint: str, prompt: str) -> AiReply:
        self.calls.append((endpoint, prompt))
        return AiReply(status=200, text=self.text)


class Clock:
    def __init__(self, step: float = 0.5) -> None:
        self.t, self.step = 0.0, step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def _approval(**kw: object) -> RunApproval:
    fields: dict[str, object] = {
        "project": "demo", "run_kind": ApprovalKind.ADVERSARIAL, "target": URL,
        "scope": "bounded adversarial pass on the fixture chat", "max_actions": 0,
        "max_probes": 4, "wall_clock_s": 120.0, "granted_by": "umesh",
        "granted_at": "2026-10-10", "expires_at": "2026-12-01"}
    return RunApproval(**{**fields, **kw}).sign()  # type: ignore[arg-type]


def _probes(tmp_path: Path, counts: dict[str, int] | None = None, name: str = "probes") -> Path:
    folder = tmp_path / name
    folder.mkdir(parents=True, exist_ok=True)
    for name, count in (counts or {"alpha": 2, "beta": 2}).items():
        body = "".join(f"## {name} {i}\n{BODY} {name} {i}\n\n" for i in range(count))
        (folder / f"{name}.md").write_text(f"# {name}\nwhat it tries\n\n{body}", encoding="utf-8")
    return folder


def _project() -> Project:
    return Project(slug="demo", name="Demo", base_url="https://llm.test/",
                   allowed_domains=["llm.test"])


def _run(tmp_path: Path, approvals: list[RunApproval], send: Counting | None = None,
         **kw: object) -> tuple[ProbeRun, Counting]:
    store = ProjectStore("demo", root=tmp_path)
    for a in approvals:
        store.add_approval(a)
    transport = send or Counting()
    args: dict[str, object] = {
        "store": store, "project": _project(), "endpoint": URL, "send": transport,
        "redactor": Redactor({"KEY": SECRET}), "production": False, "clock": Clock(), "now": NOW,
        "probes_dir": kw.pop("probes_dir", None) or _probes(tmp_path, name="default")}
    args.update(kw)
    return run_adversarial(**args), transport  # type: ignore[arg-type]


def _tree(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*")}


def _refusals(tmp_path: Path) -> list[ProbeRefusal]:
    path = tmp_path / "projects" / "demo" / "ai" / "adversarial" / "refusals.jsonl"
    if not path.exists():
        return []
    return [ProbeRefusal.model_validate_json(x) for x in path.read_text("utf-8").splitlines()]


def _refused(tmp_path: Path, approvals: list[RunApproval], **kw: object) -> tuple[str, Counting]:
    transport = Counting()
    with pytest.raises(ApprovalRequired) as exc:
        _run(tmp_path, approvals, send=transport, **kw)
    return str(exc.value), transport


def test_a_covered_pass_records_every_probe_and_nothing_else(tmp_path: Path) -> None:
    approval = _approval()
    run, transport = _run(tmp_path, [approval])
    assert len(transport.calls) == 4 == run.planned_probes == len(run.records)
    assert {c[0] for c in transport.calls} == {URL}
    assert run.approval_id == approval.id and run.approved_probes == 4 and not run.cap_hit
    assert run.probe_sets == ["alpha", "beta"] and run.ceiling == PROBE_CEILING
    rec = run.records[0]
    assert rec.probe_set == "alpha" and rec.exchange.latency_s == pytest.approx(0.5)
    assert rec.exchange.response == "I cannot help with that." and rec.exchange.status == 200
    saved = tmp_path / "projects" / "demo" / "ai" / "adversarial" / run.run_id / "run.json"
    assert ProbeRun.model_validate_json(saved.read_text("utf-8")) == run
    assert _refusals(tmp_path) == []


@pytest.mark.parametrize("name", ["none", "expired", "unsigned", "edited", "project", "crawl",
                                  "live_case"])
def test_ad1_a_refused_run_sends_nothing_and_leaves_only_the_audit_row(
        tmp_path: Path, name: str) -> None:
    rows = {"none": [], "expired": [_approval(expires_at="2026-10-01")],
            "unsigned": [_approval().model_copy(update={"signature": ""})],
            "edited": [_approval().model_copy(update={"max_probes": 9})],
            "project": [_approval(project="other")],
            "crawl": [_approval(run_kind=ApprovalKind.CRAWL, max_actions=9)],
            "live_case": [_approval(run_kind=ApprovalKind.LIVE_CASE, max_actions=9)]}[name]
    store = ProjectStore("demo", root=tmp_path)
    (tmp_path / "projects" / "demo").mkdir(parents=True)
    for a in rows:
        store.add_approval(a)
    before = _tree(tmp_path)
    _, transport = _refused(tmp_path, [], probes_dir=_probes_outside(tmp_path))
    assert transport.calls == []
    new = _tree(tmp_path) - before
    adv = "projects/demo/ai/adversarial"
    assert new == {"projects/demo/ai", adv, f"{adv}/refusals.jsonl"}
    assert len(_refusals(tmp_path)) == 1


def _probes_outside(tmp_path: Path) -> Path:
    """Probe files live beside the project, so reading them is not a write under it."""
    return _probes(tmp_path.parent / f"{tmp_path.name}-probes")


def test_ad2_the_approval_must_cover_the_planned_probe_count(tmp_path: Path) -> None:
    message, transport = _refused(tmp_path, [_approval(max_probes=3)])
    assert "probes 4 > approved 3" in message and transport.calls == []


@pytest.mark.parametrize("target", [URL + "/", "https://LLM.test/chat", URL + "?x=1",
                                    "https://llm.test"])
def test_ad2_target_variants_are_distinct_targets(tmp_path: Path, target: str) -> None:
    message, transport = _refused(tmp_path, [_approval(target=target)])
    assert transport.calls == [] and "no approval exists for it" in message


def test_ad2_every_rejection_reason_is_listed(tmp_path: Path) -> None:
    message, _ = _refused(
        tmp_path, [_approval(max_probes=1), _approval(expires_at="2026-10-01")])
    assert "narrower than this run" in message and "expired" in message


def test_ad3_production_needs_a_production_grant(tmp_path: Path) -> None:
    message, transport = _refused(tmp_path, [_approval()], production=True)
    assert "production" in message and transport.calls == []
    run, sent = _run(tmp_path, [_approval(production=True)], production=True)
    assert run.production and len(sent.calls) == 4


def test_ad3_a_crawl_row_is_not_credited_with_the_production_grant(tmp_path: Path) -> None:
    row = _approval(run_kind=ApprovalKind.CRAWL, production=True, max_actions=9)
    _, transport = _refused(tmp_path, [row], production=True)
    assert transport.calls == []


def test_ad4_no_third_party_probe_framework_and_probes_come_from_files() -> None:
    needle = re.compile(r"garak|pyrit|deepteam", re.I)
    files = [*SRC.rglob("*.py"), *SRC.rglob("*.md"), ROOT / "pyproject.toml"]
    assert [f for f in files if needle.search(f.read_text("utf-8"))] == []
    shipped = SRC / "prompts" / "probes"
    sets = load_probe_sets(shipped)
    assert 1 <= len(sets) <= 5 and all(s.probes for s in sets)
    assert sum(len(s.probes) for s in sets) <= PROBE_CEILING


def test_ad4_a_missing_or_empty_probe_file_is_blocked_with_a_reason(tmp_path: Path) -> None:
    folder = _probes(tmp_path)
    (folder / "empty.md").write_text("# empty\nnothing here\n", encoding="utf-8")
    transport = Counting()
    with pytest.raises(AdversarialBlocked, match="empty"):
        _run(tmp_path, [_approval()], send=transport, probes_dir=folder)
    with pytest.raises(AdversarialBlocked, match="nope"):
        _run(tmp_path, [_approval()], send=transport, probes_dir=folder, probe_sets=["nope"])
    with pytest.raises(AdversarialBlocked):
        load_probe_sets(tmp_path / "does-not-exist")
    assert transport.calls == [] and len(_refusals(tmp_path)) == 2


def test_ad5_the_exerciser_records_and_never_judges() -> None:
    text = (SRC / "stages" / "adversarial.py").read_text("utf-8")
    assert not re.search(r"Result\.|Verdict\(", text)
    assert "grade" not in text.lower().replace("upgrade", "")
    names = set(ProbeRun.model_fields)
    assert not names & {"result", "verdict", "passed", "outcome", "score"}
    with pytest.raises(ValueError):
        ProbeRun.model_validate({"verdict": "pass"})


def test_ad6_the_code_ceiling_binds_even_when_the_approval_would_allow_more(
        tmp_path: Path) -> None:
    folder = _probes(tmp_path, {"big": PROBE_CEILING + 1})
    transport = Counting()
    with pytest.raises(ProbeCeilingExceeded) as exc:
        _run(tmp_path, [_approval(max_probes=10 * PROBE_CEILING)], send=transport,
             probes_dir=folder)
    assert str(PROBE_CEILING) in str(exc.value) and transport.calls == []
    assert f"ceiling {PROBE_CEILING}" in _refusals(tmp_path)[0].reason
    assert isinstance(adversarial.PROBE_CEILING, int) and PROBE_CEILING > 0


def test_ad7_a_refusal_row_names_target_time_count_reason_and_no_probe_text(
        tmp_path: Path) -> None:
    _refused(tmp_path, [_approval(max_probes=3)])
    (row,) = _refusals(tmp_path)
    assert row.target == URL and row.requested_probes == 4
    assert row.timestamp == NOW.isoformat() and "probes 4 > approved 3" in row.reason
    raw = (tmp_path / "projects/demo/ai/adversarial/refusals.jsonl").read_text("utf-8")
    assert BODY not in raw and set(json.loads(raw)) == {"target", "timestamp", "requested_probes",
                                                         "reason"}
    _refused(tmp_path, [_approval(max_probes=3)])
    assert len(_refusals(tmp_path)) == 2
    _run(tmp_path, [_approval()])
    assert len(_refusals(tmp_path)) == 2


def test_a_secret_in_a_probe_or_a_reply_never_travels_or_persists(tmp_path: Path) -> None:
    folder = _probes(tmp_path, {"one": 1})
    (folder / "one.md").write_text(f"# one\n\n## leak\nuse key {SECRET}\n", encoding="utf-8")
    transport = Counting()
    with pytest.raises(CaptureWithheld):
        _run(tmp_path, [_approval(max_probes=1)], send=transport, probes_dir=folder)
    assert transport.calls == [] and SECRET not in json.dumps([r.model_dump() for r in
                                                                _refusals(tmp_path)])
    run, _ = _run(tmp_path, [_approval()], send=Counting(f"my key is {SECRET}"))
    assert SECRET not in run.model_dump_json() and "[REDACTED]" in run.records[0].exchange.response


def test_the_endpoint_host_must_be_inside_allowed_domains(tmp_path: Path) -> None:
    other = "https://evil.test/chat"
    transport = Counting()
    with pytest.raises(AdversarialBlocked, match="allowed_domains"):
        _run(tmp_path, [_approval(target=other)], send=transport, endpoint=other)
    assert transport.calls == []


def test_the_wall_clock_cuts_the_run_and_the_cap_flag_says_so(tmp_path: Path) -> None:
    run, transport = _run(tmp_path, [_approval(wall_clock_s=1.0)], wall_clock_s=1.0,
                          clock=Clock(0.5))
    assert run.cap_hit and run.unsent_probes == run.planned_probes - len(run.records) > 0
    assert len(transport.calls) == len(run.records)


def test_a_transport_failure_is_recorded_not_raised(tmp_path: Path) -> None:
    def boom(endpoint: str, prompt: str) -> AiReply:
        raise OSError(f"connect failed using {SECRET}")

    run, _ = _run(tmp_path, [_approval()], send=boom)  # type: ignore[arg-type]
    assert {r.exchange.error for r in run.records} == {"transport_error"}
    assert SECRET not in run.model_dump_json()
