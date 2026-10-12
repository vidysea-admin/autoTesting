"""Credential-free, network-free proof that the adversarial pass refuses to exceed its scope.

T-154 / qa/contracts/adversarial.md AD1-AD7, D-052 Part 3: the primary evidence is that the bound
holds. A counting transport stands in for the target, a throwaway project directory holds the
approvals, and a throwaway signing key signs them: no real approval row is read, minted or edited,
and no byte leaves the process. Exits 0 only if every refusal sent zero probes through the same
gate and the one in-scope pass sent exactly its planned probes.

    uv run python scripts/adversarial_proof.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["AUTOTESTER_APPROVAL_KEY"] = "adversarial-proof-throwaway-key-not-a-secret"

from autotester.core.consent import ApprovalRequired
from autotester.core.redact import Redactor
from autotester.schema.ai_check import AiReply
from autotester.schema.ai_probe import ProbeRefusal
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.schema.project import Project
from autotester.stages.adversarial import PROBE_CEILING, run_adversarial
from autotester.store.project_store import ProjectStore

URL = "https://fixture.test/chat"
NOW = datetime(2026, 10, 11, tzinfo=UTC)
PROJECT = Project(slug="fixture", name="Fixture", base_url="https://fixture.test/",
                  allowed_domains=["fixture.test"])


class Counting:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, endpoint: str, prompt: str) -> AiReply:
        self.calls += 1
        return AiReply(status=200, text="fixture reply")


def _row(**kw: object) -> RunApproval:
    fields: dict[str, object] = {
        "project": "fixture", "run_kind": ApprovalKind.ADVERSARIAL, "target": URL,
        "scope": "fixture proof", "max_probes": 4, "wall_clock_s": 120.0, "granted_by": "proof",
        "granted_at": "2026-10-10", "expires_at": "2026-12-01"}
    return RunApproval(**{**fields, **kw}).sign()  # type: ignore[arg-type]


def _probes(root: Path, count: int) -> Path:
    folder = root / "probes"
    folder.mkdir()
    body = "".join(f"## p{i}\nfixture probe {i}\n\n" for i in range(count))
    (folder / "fixture.md").write_text("# fixture\nproof set\n\n" + body, encoding="utf-8")
    return folder


def _attempt(label: str, rows: list[RunApproval], *, count: int = 4, endpoint: str = URL,
             production: bool = False) -> tuple[str, bool, str]:
    """(label, held, detail): a refusal holds only if it raised, sent 0 and logged one row."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store, transport = ProjectStore("fixture", root=root), Counting()
        for row in rows:
            store.add_approval(row)
        try:
            run_adversarial(store=store, project=PROJECT, endpoint=endpoint, send=transport,
                            redactor=Redactor({}), production=production, now=NOW,
                            probes_dir=_probes(root, count))
        except ApprovalRequired:
            log = root / "projects" / "fixture" / "ai" / "adversarial" / "refusals.jsonl"
            logged = [ProbeRefusal.model_validate_json(x) for x in log.read_text().splitlines()]
            runs = [p for p in log.parent.iterdir() if p.is_dir()]
            held = transport.calls == 0 and len(logged) == 1 and not runs
            return label, held, f"refused; sent={transport.calls}; log rows={len(logged)}"
        return label, False, f"NOT refused; sent={transport.calls}"


def _in_scope() -> tuple[str, bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store, transport = ProjectStore("fixture", root=root), Counting()
        store.add_approval(_row())
        run = run_adversarial(store=store, project=PROJECT, endpoint=URL, send=transport,
                              redactor=Redactor({}), production=False, now=NOW,
                              probes_dir=_probes(root, 4))
        held = transport.calls == 4 == len(run.records) and not run.cap_hit
        return "in-scope pass sends exactly its planned probes", held, f"sent={transport.calls}"


def main() -> int:
    results = [
        _in_scope(),
        _attempt("no approval", []),
        _attempt("expired approval", [_row(expires_at="2026-10-01")]),
        _attempt("probes over the approval", [_row(max_probes=3)]),
        _attempt("wrong endpoint (trailing slash)", [_row(target=URL + "/")]),
        _attempt("wrong endpoint (host case)", [_row(target="https://FIXTURE.test/chat")]),
        _attempt("wrong endpoint (query string)", [_row(target=URL + "?x=1")]),
        _attempt("wrong kind (crawl row)", [_row(run_kind=ApprovalKind.CRAWL, max_actions=9)]),
        _attempt("production without the flag", [_row()], production=True),
        _attempt(f"probes over the code ceiling ({PROBE_CEILING})",
                 [_row(max_probes=100 * PROBE_CEILING)], count=PROBE_CEILING + 1),
    ]
    for label, held, detail in results:
        print(f"{'HELD  ' if held else 'BROKEN'} {label}: {detail}")
    ok = all(held for _, held, _ in results)
    print("ADVERSARIAL PROOF " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
