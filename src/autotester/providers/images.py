"""One job: turn a prompt plus screenshot files into OpenAI-style message content.

AT-049: a judge handed only a filename in its prompt grades blind, so real
screenshot files must travel as `image_url` parts. The format is understood by
LiteLLM for every vendor it routes to.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any


def image_url_parts(prompt: str, images: list[Path] | None) -> str | list[dict[str, Any]]:
    """The prompt string itself when no real image file exists (unchanged text
    path); otherwise a text part followed by one base64 PNG `image_url` part per
    file that exists on disk. A path that is not a file is skipped, never raised."""
    real = [p for p in (images or []) if p.exists()]
    if not real:
        return prompt
    parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for path in real:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    return parts
