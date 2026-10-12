"""A second, independent real browser session (own profile) used as 'another browser's identity'."""
import sys
import tempfile
from pathlib import Path

import h

tmp = Path(tempfile.mkdtemp(prefix="r2b-other-"))
s = h.mk(tmp)
s.start()
print(s.cdp_url.rsplit(":", 1)[1], flush=True)
sys.stdin.read() if False else None
import time
while True:
    time.sleep(1)
