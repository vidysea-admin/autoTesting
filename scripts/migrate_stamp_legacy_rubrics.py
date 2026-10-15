"""Stamp `Provenance` on legacy default rubrics, in stored project data.

Before provenance stamping existed (AT-059), `run_case_pipeline.default_rubric`
wrote a rubric with `provenance: null`. AT-059's own fix, `is_stale_default`,
treats an unprovenanced rubric as hand-authored and never touches it -- the
safe direction, but it also means those rubrics can never self-heal: if the
case's rationale is later corrected, AT-059's exact live failure recurs for
them and hand-deleting the file is again the only recovery (AT-065).

A rubric is a migration CANDIDATE only when its `criteria`/`no_fire` are
BYTE-IDENTICAL to what `run_case_pipeline._rubric_for_claim` would produce for
the claim embedded in its own criterion text -- shape alone, never a guess.
Every hand-written rubric in this repo differs in shape (a different criterion
id, different `no_fire` wording) and is never touched; a rubric a human has
since edited, even with `provenance: null` still on it, no longer matches the
template either and is left alone too.

DRY RUN BY DEFAULT. Writing to real project data is a human's call -- AT-065's
own fix direction says "reviewed by a human per file, not an automatic runtime
heuristic", so the dry run always lists every candidate file with the claim it
would be stamped with, and `--only` lets that review land one file at a time:

    uv run python scripts/migrate_stamp_legacy_rubrics.py            # report only
    uv run python scripts/migrate_stamp_legacy_rubrics.py --write    # stamp every candidate
    uv run python scripts/migrate_stamp_legacy_rubrics.py --write \
        --only projects/pathlynks/rubrics/rub_case_35b17ccece2d.json # stamp one file
    uv run python scripts/migrate_stamp_legacy_rubrics.py --root <dir>  # a sandbox

Idempotent: a stamped rubric is never a candidate again (its `provenance` is no
longer `None`), so a second run reports nothing left to stamp.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from autotester.schema.base import Provenance
from autotester.schema.verdict import Rubric
from autotester.stages.run_case_pipeline import GENERATOR, _rubric_for_claim

# The exact template `run_case_pipeline._rubric_for_claim` writes (reworded in 54cf364a) -- see that
# function. Matched with DOTALL so a claim containing its own newlines or
# periods still parses; the anchors on both ends are what make this shape-only
# rather than a guess.
_CLAIM_RE = re.compile(
    r"^The product behaved correctly for this case, whose stated purpose is: "
    r"(?P<claim>.*)\. Evidence of a defect \(an error or rejection where success was "
    r"expected, a wrong result, a missing element\) means this criterion is NOT met, "
    r"even when the purpose above is to catch that defect\. If you cite this as a "
    r"failure, use criterion id 'c1' exactly — do not invent a different id\.$",
    re.DOTALL,
)


def _embedded_claim(rubric: Rubric) -> str | None:
    """The claim `_rubric_for_claim` would have been built from, if this
    rubric's single criterion matches the generator's exact template --
    `None` otherwise (any hand-written shape, any criterion count)."""
    if len(rubric.criteria) != 1 or rubric.criteria[0].id != "c1":
        return None
    match = _CLAIM_RE.match(rubric.criteria[0].text)
    return match.group("claim") if match else None


def candidate(rubric: Rubric) -> str | None:
    """The claim to stamp with, or `None` when `rubric` is not a migration
    candidate: already provenanced (self-healing already works for it), or
    its shape is not byte-identical to what the generator would have written
    for the claim embedded in its own text."""
    if rubric.provenance is not None:
        return None
    claim = _embedded_claim(rubric)
    if claim is None:
        return None
    rebuilt = _rubric_for_claim(claim, rubric.case_id or "", rubric.id)
    if rubric.criteria != rebuilt.criteria or rubric.no_fire != rebuilt.no_fire:
        return None
    return claim


def scan(root: Path) -> list[tuple[Path, str]]:
    """Every rubric file under `root` that is a stamping candidate, with the
    claim it would be stamped with."""
    found: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("rub_*.json")):
        try:
            rubric = Rubric.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        claim = candidate(rubric)
        if claim is not None:
            found.append((path, claim))
    return found


def apply(path: Path, claim: str) -> None:
    """Stamp `path` in place with the same `Provenance` the generator writes
    at creation time today -- nothing else in the file changes."""
    rubric = Rubric.model_validate_json(path.read_text(encoding="utf-8"))
    stamped = rubric.model_copy(update={
        "provenance": Provenance(produced_by=GENERATOR, inputs=[rubric.case_id or ""], note=claim),
    })
    path.write_text(stamped.model_dump_json(indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=Path("projects"), type=Path)
    parser.add_argument("--write", action="store_true",
                        help="actually stamp files (default: report only)")
    parser.add_argument("--only", nargs="+", type=Path, default=None,
                        help="with --write, stamp only these paths "
                             "(default: every candidate found)")
    args = parser.parse_args(argv)

    if not args.root.exists():
        print(f"no such directory: {args.root}")
        return 2

    found = scan(args.root)
    if not found:
        print(f"{args.root}: nothing to stamp")
        return 0

    only = {p.resolve() for p in args.only} if args.only else None
    stamped = 0
    for path, claim in found:
        marker = ""
        if args.write and (only is None or path.resolve() in only):
            apply(path, claim)
            stamped += 1
            marker = " [stamped]"
        print(path.as_posix() + marker)
        print(f"    claim: {claim!r}")

    verb = "stamped" if args.write else "would stamp"
    count = stamped if args.write else len(found)
    print(f"\n{verb} {count} rubric(s) across {len(found)} candidate file(s)")
    if not args.write:
        print("dry run — re-run with --write to apply (or --write --only <path> for one file)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
