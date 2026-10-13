"""Map an AI-assisted video-review findings list to a `BenchCorpus` (bench.md K12).

Only real bug rows are kept (severity High or Medium); praise rows ("Working well") and
summary rows (no severity) are dropped. The corpus is `known_bugs_ai_assisted`: a
KNOWN-BUGS oracle compiled by watching recordings with AI help -- never an independent
human tester's list, and its recall is always labelled so.
"""

from __future__ import annotations

from autotester.schema.bench import BenchCorpus, SeededBug
from autotester.schema.enums import Severity

SEVERITY = {"high": Severity.S1, "medium": Severity.S2}


def known_bugs_corpus(items: list[dict], slug: str, build_ref: str) -> BenchCorpus:
    """Build the corpus; ids are kept from the source rows so findings can cite them."""
    bugs = []
    for item in items:
        severity = SEVERITY.get(str(item.get("severity") or "").strip().lower())
        if severity is None:
            continue
        screen = str(item.get("screen/flow") or item.get("title") or "")
        bugs.append(SeededBug(
            id=str(item["id"]), description=str(item.get("title") or screen),
            severity=severity, location=screen,
            detect_hint=str(item.get("description") or item.get("title") or ""),
            provenance="ai_video_review",
        ))
    refs = sorted({str(i["video_ref"]).split(" @")[0] for i in items
                   if i.get("video_ref") and SEVERITY.get(str(i.get("severity") or "").lower())})
    return BenchCorpus(
        id=f"{slug}-acceptance", app=slug, build_ref=build_ref, seeded_bugs=bugs,
        material_refs=refs, mode="known_bugs_ai_assisted",
    )
