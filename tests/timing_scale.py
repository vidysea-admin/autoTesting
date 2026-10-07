"""AT-757: the one place a load-sensitive test bound is scaled for a busy host.

Test-only helper (no `src/` module). A wall-clock bound that a saturated machine
can overrun is written `BASE * timing_scale()`. The scale comes from
`AUTOTESTER_TIMING_SCALE`: default 1.0, so an idle run keeps exactly today's
bound; it can only LOOSEN (anything below 1.0, empty, or unparseable is 1.0) and
is capped at 4.0. Sweep shards run with `AUTOTESTER_TIMING_SCALE=2`.
"""

from __future__ import annotations

import math
import os

TIMING_SCALE_ENV = "AUTOTESTER_TIMING_SCALE"
MIN_SCALE = 1.0
MAX_SCALE = 4.0


def timing_scale() -> float:
    raw = os.environ.get(TIMING_SCALE_ENV, "").strip()
    try:
        value = float(raw)
    except ValueError:
        return MIN_SCALE
    if not math.isfinite(value):
        return MIN_SCALE
    return min(max(value, MIN_SCALE), MAX_SCALE)
