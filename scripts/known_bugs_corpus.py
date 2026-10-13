"""Convert an AI-assisted review findings list to a known-bugs bench corpus (bench.md K12).

    uv run python scripts/known_bugs_corpus.py pathlynks --from .work/mail-intake/karun-bugs.json

The source is internal feedback and the output is internal: it is written under `.work/`
(gitignored) and refused anywhere git would track. Read it back with
`scripts/check_acceptance_comparison.py <slug> --corpus <that file>`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.stages.known_bugs import known_bugs_corpus
from autotester.store.filestore import write_json

ROOT = Path(__file__).resolve().parents[1]


def _ignored(path: Path) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=ROOT,
                          capture_output=True).returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slug")
    parser.add_argument("--from", dest="source", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None,
                        help="default: .work/known-bugs/<slug>-acceptance.json")
    parser.add_argument("--build-ref", default="live production at review date")
    args = parser.parse_args(argv)
    out = args.out or ROOT / ".work" / "known-bugs" / f"{args.slug}-acceptance.json"
    if not _ignored(out):
        print(f"refusing to write {out}: not gitignored (internal feedback must not be "
              "committed to the public repo)", file=sys.stderr)
        return 2
    items = json.loads(args.source.read_text(encoding="utf-8"))
    corpus = known_bugs_corpus(items, args.slug, args.build_ref)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, corpus)
    print(f"{len(corpus.seeded_bugs)} bugs of {len(items)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
