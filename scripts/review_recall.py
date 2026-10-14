"""Write `recall.json` (TA16): stored video reviews scored against an oracle corpus.

    PYTHONPATH=src .venv/Scripts/python scripts/review_recall.py \
        --review review_a.json --review review_b.json --review review_c.json \
        --oracle .work/known-bugs/<oracle-corpus>.json [--matches override.json] \
        --out qa/evidence/t206-review-live/recall.json [--elapsed-s 412] [--request-log log.jsonl]

`--review` is a stored `VideoReview` JSON (one per source). `--oracle` is a `BenchCorpus` JSON
(gitignored, read locally). Matching is automatic (lexical, no model); optional `--matches`
overrides it: {"<oracle id>": ["<review item id>", ...]}. Oracle must hold 13 S1 rows.
The mapping is a human or checker judgement. No model call, no browser.
Exit 2 on any input that does not fit; no number is invented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.schema.bench import BenchCorpus
from autotester.schema.video_review import VideoReview
from autotester.stages.review_recall import EXPECTED_HIGH, HIGH, score_reviews
from autotester.store.filestore import write_json


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--review", type=Path, action="append", required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--matches", type=Path, default=None,
                    help="optional human override of the automatic matching")
    ap.add_argument("--expected-n", type=int, default=EXPECTED_HIGH)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--severity", default=HIGH)
    ap.add_argument("--elapsed-s", type=float, default=None, help="wall-clock time-to-review")
    ap.add_argument("--request-log", type=Path, default=None)
    args = ap.parse_args(argv)
    try:
        reviews = [VideoReview.model_validate_json(p.read_text(encoding="utf-8"))
                   for p in args.review]
        raw = args.oracle.read_bytes()
        oracle = BenchCorpus.model_validate_json(raw)
        matches = (json.loads(args.matches.read_text(encoding="utf-8"))
                   if args.matches else None)
        rec = score_reviews(reviews, oracle, raw, matches, args.severity, args.expected_n)
    except (OSError, ValueError) as exc:
        print(f"cannot score: {exc}", file=sys.stderr)
        return 2
    if args.elapsed_s is not None:
        rec.time_to_review_s = args.elapsed_s
    else:
        rec.time_to_review_note = "not supplied; no figure invented"
    if args.request_log:
        rec.request_log_ref = args.request_log.name
        rec.request_log_sha256 = hashlib.sha256(args.request_log.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, rec)
    print(f"{rec.claim}: recall {rec.k} of {rec.n} ({rec.oracle.recall_basis}); "
          f"missed {rec.missed_ids}; unconfirmed {rec.unconfirmed_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
