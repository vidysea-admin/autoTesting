"""Deliver sanitized grading images and expose privacy-driven visual evidence shortfalls."""

from pathlib import Path

from autotester.core.image_privacy import sanitized_images
from autotester.providers.base import Provider
from autotester.schema.verdict import Judgment

VISUAL_PRIVACY_NOTE = (
    "Visual evidence incomplete: screenshot text was masked or images were withheld for "
    "privacy; readable screenshot text is unavailable. Do not infer text from filenames."
)


def judge_images(judge: Provider, prompt: str, paths: list[Path], *,
                 prompt_file: str, fed_id: str) -> tuple[Judgment, int]:
    """Keep safe copies alive through the call and count actual delivered images."""
    with sanitized_images(paths) as batch:
        if paths:
            prompt += "\n\n" + VISUAL_PRIVACY_NOTE
        judgment = judge.judge(prompt, Judgment, images=batch.paths,
                               prompt_file=prompt_file, fed_id=fed_id)
        return judgment, len(batch.paths)
