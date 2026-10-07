"""Number lines by \n, \r\n and \r only, so a cited line is the physical editor line."""

import re

_BREAK = re.compile(r"\r\n|\r|\n")


def split_lines(text: str) -> list[str]:
    """Like str.splitlines, but U+2028, U+2029, U+0085, \f, \v and \x1c-\x1e stay in-line."""
    parts = _BREAK.split(text)
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def first_nonblank_line(text: str) -> int:
    """1-based physical line of the first non-blank line; the caller ensures one exists."""
    return next(i for i, value in enumerate(split_lines(text), 1) if value.strip())
