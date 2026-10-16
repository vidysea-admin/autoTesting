"""Filter: mask known secret VALUES in a stream with `Redactor`. One job, for shell scripts.

Usage: `python -m autotester.core.redact_cli VALUES_FILE < in > out`. VALUES_FILE holds one secret
value per line (blank lines ignored). The values are read, never printed. The masking itself is
`core.redact.Redactor.scrub` (exact value plus its encodings); this module only adapts it to
stdin/stdout so `scripts/container_diagnose.sh` reuses it instead of a second implementation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from autotester.core.redact import Redactor

_LABEL = re.compile(r"\[REDACTED\]:\d+")


def mask_stream(text: str, values: list[str]) -> str:
    """Return `text` with every value (and its encodings) masked as `<redacted>`."""
    redactor = Redactor({str(i): v for i, v in enumerate(values) if v})
    return _LABEL.sub("<redacted>", redactor.scrub(text)).replace("[REDACTED]", "<redacted>")


def filter_main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m autotester.core.redact_cli VALUES_FILE < in > out", file=sys.stderr)
        return 2
    raw = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    values = [v for v in raw.splitlines() if v]
    data = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    sys.stdout.buffer.write(mask_stream(data, values).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(filter_main(sys.argv))
