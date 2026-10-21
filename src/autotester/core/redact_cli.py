"""Filter for shell scripts: mask known secret VALUES in a stream, or list a `.env` file's values.

Two modes, one job (give `scripts/container_diagnose_lib.sh` the repo's own secret handling):
- `python -m autotester.core.redact_cli VALUES_FILE < in > out`: VALUES_FILE holds one secret
  value per line (blank lines ignored). The masking is `core.redact.Redactor.scrub` (exact value
  plus its encodings); this module only adapts it to stdin/stdout.
- `python -m autotester.core.redact_cli --values-from-env ENV_FILE > values`: print every value
  of ENV_FILE, one line each (a multiline value prints each of its lines), parsed by
  `core.env.read_dotenv` (literal, no interpolation), the reader `core.env.load_repo_env` uses.
  Values go to stdout (a pipe), never argv; the caller writes them only into its own 0600 file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from autotester.core.env import read_dotenv
from autotester.core.redact import Redactor

_LABEL = re.compile(r"\[REDACTED\]:\d+")
_USAGE = ("usage: python -m autotester.core.redact_cli VALUES_FILE < in > out\n"
          "       python -m autotester.core.redact_cli --values-from-env ENV_FILE > values")


def mask_stream(text: str, values: list[str]) -> str:
    """Return `text` with every value (and its encodings) masked as `<redacted>`."""
    redactor = Redactor({str(i): v for i, v in enumerate(values) if v})
    return _LABEL.sub("<redacted>", redactor.scrub(text)).replace("[REDACTED]", "<redacted>")


def env_values(path: Path) -> list[str]:
    """Every non-empty value line of the dotenv file at `path`, as `dotenv_values` reads it."""
    out: list[str] = []
    for value in read_dotenv(path).values():
        out.extend(line for line in (value or "").splitlines() if line.strip())
    return out


def filter_main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--values-from-env":
        lines = env_values(Path(argv[2]))
        sys.stdout.buffer.write("".join(f"{v}\n" for v in lines).encode("utf-8"))
        return 0
    if len(argv) != 2 or argv[1].startswith("--"):
        print(_USAGE, file=sys.stderr)
        return 2
    raw = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    values = [v for v in raw.splitlines() if v]
    data = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    sys.stdout.buffer.write(mask_stream(data, values).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(filter_main(sys.argv))
