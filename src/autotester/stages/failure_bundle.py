"""Assemble and load one atomic failure bundle (T-178, qa/contracts/failure-bundle.md FB1-FB3).

One bundle per failing case run: the case, verdict, result, error, the failing step and
its neighbours, their masked screenshots and the redacted trace slice. It is written under
`<bundle_id>.partial` and renamed only once `manifest.json` (written last) is in place, so
a write that dies leaves the `.partial` marker and no complete-looking bundle (FB1).
Artifacts of more than one run are a hard refusal (FB2); every text part is scrubbed and
gated through `Redactor`, and an unmasked screenshot is refused (FB3).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from autotester.core.ids import content_id
from autotester.core.redact import Redactor
from autotester.schema.case import Case
from autotester.schema.enums import EvidenceKind
from autotester.schema.failure_bundle import (
    BundleFile,
    BundleFileKind,
    BundleManifest,
    BundleSource,
)
from autotester.schema.run import RawResult
from autotester.schema.trace import LLMSpan, StageSpan
from autotester.schema.verdict import Verdict

PARTIAL = ".partial"
MANIFEST = "manifest.json"
REQUIRED_KINDS = (BundleFileKind.CASE, BundleFileKind.VERDICT, BundleFileKind.RESULT,
                  BundleFileKind.ERROR, BundleFileKind.TRACE)


class BundleError(ValueError):
    """A bundle could not be built or was refused on load."""


class RunMixError(BundleError):
    """FB2: an artifact belongs to a different run than the bundle."""


class PartialBundleError(BundleError):
    """FB1: the bundle is a `.partial`, missing a part, or fails its own hashes."""


class UnmaskedScreenshotError(BundleError):
    """FB3: a screenshot was not captured with its secret inputs masked."""


def sources_from_result(run_id: str, run_dir: Path, result: RawResult) -> list[BundleSource]:
    """Screenshot evidence of one result as sources, stamped with the run they came from."""
    return [
        BundleSource(run_id=run_id, path=run_dir / ev.path, step_order=ev.step_order,
                     masked=ev.masked)
        for ev in result.evidence
        if ev.kind is EvidenceKind.SCREENSHOT and ev.step_order is not None
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_text(redactor: Redactor, text: str) -> str:
    clean = redactor.scrub(text)
    redactor.assert_clean(clean)
    return clean


def _dump(redactor: Redactor, payload: Any) -> str:
    """JSON of a model or dict: scrub the structure, serialise, then scrub + gate the text."""
    data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    text = json.dumps(redactor.scrub_obj(data), indent=2, ensure_ascii=False)
    return _clean_text(redactor, text) + "\n"


def _check_one_run(run_id: str, case: Case, result: RawResult, verdict: Verdict,
                   sources: Sequence[BundleSource],
                   spans: Sequence[StageSpan | LLMSpan]) -> None:
    """FB2: refuse before anything is written if any input belongs to another run."""
    stray = [f"verdict:{verdict.run_id}"] if verdict.run_id != run_id else []
    stray += [f"screenshot:{s.run_id}" for s in sources if s.run_id != run_id]
    stray += [f"trace:{s.trace_id}" for s in spans if s.trace_id != run_id]
    if stray:
        raise RunMixError(
            f"refusing to mix runs: bundle is for {run_id!r}, got {sorted(set(stray))}")
    if not (case.id == verdict.case_id == result.case_id):
        raise BundleError(f"case/verdict/result disagree: {case.id}, {verdict.case_id}, "
                          f"{result.case_id}")


def _failing_step(case: Case, result: RawResult, requested: int | None) -> int | None:
    orders = [s.order for s in case.steps]
    if requested is None:
        seen = [e.step_order for e in result.evidence if e.step_order is not None]
        requested = max(seen) if seen else (orders[0] if orders else None)
    if requested is not None and requested not in orders:
        raise BundleError(f"failing step {requested} is not a step of case {case.id}")
    return requested


def _window(case: Case, failing: int | None, neighbours: int) -> list[int]:
    """The failing step's order plus up to `neighbours` steps on each side, where they exist."""
    orders = sorted(s.order for s in case.steps)
    if failing is None:
        return []
    i = orders.index(failing)
    return orders[max(0, i - neighbours): i + neighbours + 1]


class _Writer:
    """Writes parts into the `.partial` directory and records each in the manifest."""

    def __init__(self, root: Path, run_id: str) -> None:
        self.root, self.run_id = root, run_id
        self.files: list[BundleFile] = []

    def add(self, name: str, kind: BundleFileKind, *, text: str | None = None,
            copy_from: Path | None = None, step_order: int | None = None) -> None:
        dest = self.root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if text is not None:
            dest.write_text(text, encoding="utf-8")
        else:
            shutil.copyfile(copy_from, dest)  # type: ignore[arg-type]
        self.files.append(BundleFile(name=name, kind=kind, run_id=self.run_id,
                                     sha256=_sha256(dest), step_order=step_order))


def _write_parts(w: _Writer, redactor: Redactor, case: Case, result: RawResult,
                 verdict: Verdict, sources: Sequence[BundleSource],
                 spans: Sequence[StageSpan | LLMSpan], steps: list[int]) -> None:
    w.add("case.json", BundleFileKind.CASE, text=_dump(redactor, case))
    w.add("verdict.json", BundleFileKind.VERDICT, text=_dump(redactor, verdict))
    w.add("result.json", BundleFileKind.RESULT, text=_dump(redactor, result))
    w.add("error.txt", BundleFileKind.ERROR,
          text=_clean_text(redactor, result.error or "") + "\n")
    for step in (s for s in case.steps if s.order in steps):
        w.add(f"steps/{step.order}.json", BundleFileKind.STEP, text=_dump(redactor, step),
              step_order=step.order)
    for n, src in enumerate(s for s in sources if s.step_order in steps):
        suffix = src.path.suffix or ".png"
        w.add(f"screenshots/{src.step_order}-{n}{suffix}", BundleFileKind.SCREENSHOT,
              copy_from=src.path, step_order=src.step_order)
    lines = [_clean_text(redactor, sp.model_dump_json()) for sp in spans]
    w.add("trace.jsonl", BundleFileKind.TRACE, text="".join(f"{ln}\n" for ln in lines))


def build_failure_bundle(
    *, out_dir: Path, run_id: str, case: Case, result: RawResult, verdict: Verdict,
    sources: Sequence[BundleSource], spans: Sequence[StageSpan | LLMSpan],
    redactor: Redactor, failing_step: int | None = None, neighbours: int = 1,
) -> Path:
    """Build `out_dir/<bundle_id>` for one failing case run, or raise and leave only a `.partial`.

    The id is content-addressed on (run, case), so a repeat call returns the existing complete
    bundle. Every refusal that can be decided from the inputs (FB2, FB3 unmasked) happens
    before the first byte is written.
    """
    _check_one_run(run_id, case, result, verdict, sources, spans)
    failing = _failing_step(case, result, failing_step)
    steps = _window(case, failing, neighbours)
    kept = [s for s in sources if s.step_order in steps]
    if any(not s.masked for s in kept):
        raise UnmaskedScreenshotError("refusing a screenshot not captured with secrets masked")
    bundle_id = content_id("fb", {"run": run_id, "case": case.id})
    final, partial = out_dir / bundle_id, out_dir / f"{bundle_id}{PARTIAL}"
    if final.exists():
        try:
            load_bundle(final)
            return final
        except BundleError:
            shutil.rmtree(final)
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    w = _Writer(partial, run_id)
    _write_parts(w, redactor, case, result, verdict, kept, spans, steps)
    manifest = BundleManifest(bundle_id=bundle_id, run_id=run_id, case_id=case.id,
                              failing_step=failing, steps_included=steps, files=w.files)
    (partial / MANIFEST).write_text(_dump(redactor, manifest), encoding="utf-8")
    partial.rename(final)
    return final


def load_bundle(path: Path) -> BundleManifest:
    """FB1: the manifest of a complete bundle, else raise `PartialBundleError`/`RunMixError`."""
    if path.name.endswith(PARTIAL):
        raise PartialBundleError(f"{path.name} is a .partial: its write did not complete")
    manifest_path = path / MANIFEST
    if not manifest_path.is_file():
        raise PartialBundleError(f"{path} has no {MANIFEST}")
    manifest = BundleManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    for f in manifest.files:
        if f.run_id != manifest.run_id:
            raise RunMixError(
                f"{f.name} belongs to run {f.run_id!r}, bundle is {manifest.run_id!r}")
        target = path / f.name
        if not target.is_file() or _sha256(target) != f.sha256:
            raise PartialBundleError(f"{f.name} is missing or does not match its recorded hash")
    missing = [k.value for k in REQUIRED_KINDS if not any(f.kind is k for f in manifest.files)]
    if missing:
        raise PartialBundleError(f"bundle lacks required parts: {missing}")
    return manifest
