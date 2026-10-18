"""Deliver sanitized grading images; decide what privacy-driven visual shortfalls do to a verdict.

One job: the bridge between `core.image_privacy` (masks text bands, withholds an image it cannot
trust) and `grade()`. `judge_images` reports WHICH source images were actually delivered, and
`visual_decision` turns that into the fail-closed rules of T-136 (browser-and-secrets.md B11):

* a FAIL that cites a screenshot the judge never received, or has only a visual basis when no
  image was delivered, is INCONCLUSIVE (mirrors the PASS rule);
* masking alone does not downgrade a PASS (every site's text is masked, so no screenshot case
  could ever pass): a PASS stands only when every image was delivered AND at least one
  deterministic `assert ...: met` row backs it (the DOM, not the masked pixels, verified the
  asserted element). Otherwise the asserted text is not determinable and the PASS is held.
"""

from contextlib import ExitStack
from pathlib import Path

from autotester.core.image_privacy import sanitized_images
from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider
from autotester.schema.enums import Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Failure, Judgment

VISUAL_PRIVACY_NOTE = (
    "Visual evidence incomplete: screenshot text was masked or images were withheld for "
    "privacy; readable screenshot text is unavailable. Do not infer text from filenames."
)
UNSEEN_FAIL_NOTE = (
    "judge answered FAIL on a screenshot it never received ({why}): the failure is not trusted "
    "(fail closed, core-invariants C12, B11). Held as INCONCLUSIVE for a human to look at."
)
UNBACKED_PASS_NOTE = (
    "judge answered PASS but {why}: masked screenshots cannot establish that text is present "
    "(B11), so the PASS is held as INCONCLUSIVE for a human to look at."
)


def judge_images(judge: Provider, prompt: str, paths: list[Path], *,
                 prompt_file: str, fed_id: str) -> tuple[Judgment, list[Path]]:
    """Keep safe copies alive through the call; also return the SOURCE paths actually delivered
    (one sanitation batch per image, so a withheld image is identified, not just counted)."""
    with ExitStack() as stack:
        batches = [(src, stack.enter_context(sanitized_images([src]))) for src in paths]
        delivered = [(src, batch.paths[0]) for src, batch in batches if batch.paths]
        if paths:
            prompt += "\n\n" + (RepoDocs().prompts_dir / "image_privacy.md").read_text("utf-8")
        judgment = judge.judge(prompt, Judgment, images=[safe for _, safe in delivered],
                               prompt_file=prompt_file, fed_id=fed_id)
        return judgment, [src for src, _ in delivered]


def _cites(failure: Failure, image: Path) -> bool:
    name = image.name.lower()
    return any(name in ref.replace("\\", "/").lower() for ref in failure.evidence_refs)


def _unseen_basis(failures: list[Failure], unseen: list[Path], delivered: list[Path]) -> str | None:
    """Why a FAIL rests on a visual the judge never received, or None."""
    for image in unseen:
        if any(_cites(f, image) for f in failures):
            return f"{image.name} was withheld or absent"
    if not delivered and any(not f.evidence_refs for f in failures):
        return "no screenshot reached the judge and the failure cites no other evidence"
    return None


def _met_assertions(result: RawResult) -> int:
    return sum(1 for ev in result.evidence if ev.path.startswith("assert ") and ": met" in ev.path)


def _join(*parts: str | None) -> str | None:
    kept = [p for p in parts if p]
    return ". ".join(kept) if kept else None


def visual_decision(final: Result, failures: list[Failure], result: RawResult,
                    requested: list[Path], delivered: list[Path],
                    shortfall: str | None) -> tuple[Result, str | None]:
    """Apply the T-136 rules; returns the (possibly downgraded) result and the shortfall text,
    which `grade()` puts in both the scoreboard and the note. Only called when images were asked."""
    unseen = [p for p in requested if p not in delivered]
    why: str | None = None
    if final is Result.FAIL and (why := _unseen_basis(failures, unseen, delivered)):
        final, why = Result.INCONCLUSIVE, UNSEEN_FAIL_NOTE.format(why=why)
    elif final is Result.PASS:
        gap = (f"{len(unseen)} screenshot(s) were withheld or absent" if unseen
               else None if _met_assertions(result)
               else "no deterministic assertion was met to back the masked screenshots")
        if gap:
            final, why = Result.INCONCLUSIVE, UNBACKED_PASS_NOTE.format(why=gap)
    return final, _join(VISUAL_PRIVACY_NOTE, shortfall, why)
