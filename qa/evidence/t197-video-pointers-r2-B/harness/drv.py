"""Subprocess entry for the REAL CLI with a wrapped mock provider (no live model call).

Env: R2B_MODE = ok | runtime | oserror | hang | unavailable ; R2B_ROOT is AUTOTESTER_ROOT.
Every judge() call appends a JSON line to $R2B_ROOT/_calls.jsonl and copies the stills it was
handed to $R2B_ROOT/_recv/. In hang mode it also snapshots the live redacted derivative's
frame inside the redaction window to _recv/ and signals readiness via a file, then sleeps.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from autotester import providers
from autotester.providers.base import Provider
from autotester.schema.video_review import ReplyItem, ReviewReply

ROOT = Path(os.environ["R2B_ROOT"])
MODE = os.environ.get("R2B_MODE", "ok")
SECRET_CANARY = "hunter2-canary-xyz"


class Mock(Provider):
    id = "fake"

    def available(self) -> bool:
        return MODE != "unavailable"

    def judge(self, prompt, schema, images=None, *, prompt_file=None, fed_id=None):
        recv = ROOT / "_recv"
        recv.mkdir(exist_ok=True)
        paths = [Path(p) for p in images or []]
        n = len(list(recv.glob("*.png")))
        for i, p in enumerate(paths):
            shutil.copyfile(p, recv / f"{n + i:04d}_{p.name}")
        with (ROOT / "_calls.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"mode": MODE, "n": len(paths),
                                 "names": [p.name for p in paths],
                                 "dirs": sorted({str(p.parent) for p in paths})}) + "\n")
        if MODE in ("runtime", "oserror"):
            video = next(ROOT.rglob("rec.mp4"), None)
            msg = f"{SECRET_CANARY} at {video} and {video.name if video else ''} in {ROOT}"
            raise (RuntimeError if MODE == "runtime" else OSError)(msg)
        if MODE == "hang":
            # snapshot the live redacted derivative inside the window (1:00-1:10 => t=65)
            for red in ROOT.rglob("redacted.mp4"):
                out = ROOT / "_recv" / "live_redacted_t65.png"
                subprocess.run(["ffmpeg", "-y", "-ss", "65", "-i", str(red), "-frames:v", "1",
                                str(out)], capture_output=True, timeout=60)
            (ROOT / "_ready").write_text(str(os.getpid()), encoding="utf-8")
            time.sleep(120)
        item = ReplyItem(time_s=70, screen="Login", seen="Button looks disabled",
                         suggestion="Check the state", severity="S2",
                         source_id=os.environ.get("R2B_SRC", "src_x"), origin="visual")
        self.record("judge", 10, 10)
        return ReviewReply(summary="A user logs in.", items=[item])


mock = Mock()
providers.get = lambda _id, **_kw: mock

from autotester.cli import app  # noqa: E402

if __name__ == "__main__":
    sys.argv[0] = "autotester"
    app()
