"""A person's real / false-positive rulings on AutoTester findings (T-136 marks, bench.md K9).

One job: store the marks and overlay them on a trial. Nothing is scored here -- the overlay sets
`Finding.adjudication`, and `BenchTrial.score` (`stages.bench.scorecard`) reads it (bench.md K3).
A finding with no mark stays unadjudicated: it is neither a true nor a false positive in
`adjudicated_fp_rate`, and a finding already matched to a seeded bug is never re-ruled.

A mark is keyed by `finding_key`, a hash of the finding's source and its stable text, so it
survives `bench_from_run` replacing the trial and holds no finding text itself.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Literal

from autotester.core.file_lock import file_lock
from autotester.schema.base import utc_now
from autotester.schema.bench import BenchMarks, BenchTrial, Finding, Mark
from autotester.store.filestore import read_json, write_json
from autotester.store.project_store import ProjectStore

Verdict = Literal["real", "false_positive"]


def finding_key(finding: Finding) -> str:
    """Stable identity of a finding across conversions: source + text, minus a crawl's
    `(seen Nx on M screen(s))` tally, which changes with the set of crawls scanned."""
    core = finding.text.split(" (seen ", 1)[0] if finding.source == "crawl" else finding.text
    return hashlib.sha256(f"{finding.source}\n{core}".encode()).hexdigest()[:16]


def marks_id(corpus_id: str) -> str:
    return f"{corpus_id}-marks"


def load_marks(store: ProjectStore, corpus_id: str) -> BenchMarks:
    """The stored marks, or an empty set when nobody has marked anything."""
    found = read_json(store.paths.bench_marks(corpus_id), BenchMarks)
    return found or BenchMarks(id=marks_id(corpus_id), corpus_id=corpus_id)


def _write_with_retry(path: Path, marks: BenchMarks) -> None:
    """`write_json`, retried briefly: on Windows `os.replace` fails with PermissionError while a
    reader (the page, the comparison) has the file open for a moment."""
    for attempt in range(20):
        try:
            write_json(path, marks)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.02)


def set_mark(store: ProjectStore, corpus_id: str, key: str, verdict: Verdict | None,
             who: str) -> BenchMarks:
    """Record `verdict` for `key`, or undo the mark when `verdict` is None.

    The load-modify-write runs under a cross-process lock on a sidecar file, so two simultaneous
    requests (the route runs on a thread pool) never drop each other's ruling.
    """
    path = store.paths.bench_marks(corpus_id)
    store.paths.bench_dir.mkdir(parents=True, exist_ok=True)
    with file_lock(path.with_name(path.name + ".lock"), timeout_s=30.0, what="bench marks"):
        marks = load_marks(store, corpus_id)
        if verdict is None:
            marks.marks.pop(key, None)
        else:
            marks.marks[key] = Mark(verdict=verdict, marked_by=who, marked_at=utc_now())
        _write_with_retry(path, marks)
    return marks


def marked(findings: list[Finding], marks: BenchMarks) -> list[Finding]:
    """Each unmatched finding with its mark set; a matched or unmarked one is returned as is."""
    out = []
    for finding in findings:
        mark = marks.marks.get(finding_key(finding))
        if mark is None or finding.matched_bug_id is not None:
            out.append(finding)
        else:
            out.append(finding.model_copy(update={"adjudication": mark.verdict}))
    return out


def apply_marks(trial: BenchTrial, marks: BenchMarks) -> BenchTrial:
    """A copy of `trial` whose unmatched findings carry their mark; the stored one is untouched."""
    if not marks.marks:
        return trial
    return trial.model_copy(update={"findings": marked(trial.findings, marks)})
