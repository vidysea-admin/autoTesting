"""Get a recording's narration — reusing a sidecar first, transcribing last.

Two hard facts shape this module.

**Sidecars are reused byte-for-byte, never regenerated.** The corpus already
carries `<video>.transcript.json` files produced by a known-good run. Re-running
whisper over them would spend GPU minutes to produce a *different* transcript,
and the narration is injected into the ingest prompt as ground truth — so a
regenerated line is a changed quote from a real person (I8).

**Local ASR is explicit opt-in, never a default or automatic fallback.**
Whisper runs in a subprocess or not at all. ctranslate2's teardown can take
the parent process down with it, and a media-prep crash that loses the whole
run because the *optional* half failed is the wrong trade.

Measured on this host 2026-09-11: `faster_whisper` is **not installed in the
project venv, and `pyproject.toml` has no `[project.optional-dependencies]`
block at all** — there is no `media` extra to install it from (AT-169; a prior
version of this docstring claimed one existed). So the no-whisper path is the
DEFAULT here, not a rare fallback — which is exactly why it returns an empty
`Transcript` rather than raising. Declaring `faster_whisper` as an extra is
tracked separately (AT-130's sibling) for the unit that first calls a model
for real.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from autotester.schema.media import Transcript

SIDECAR_SUFFIX = ".transcript.json"
WHISPER_TIMEOUT_S = 3600.0
MODEL = "large-v3-turbo"


def find_sidecar(video: Path) -> Path | None:
    """The `<video>.transcript.json` beside the recording, if it is there."""
    sidecar = video.with_suffix(SIDECAR_SUFFIX)
    return sidecar if sidecar.exists() else None


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return True


def transcribe(video: Path, source_id: str, *, use_whisper: bool = False) -> Transcript:
    """Narration for `video`. Sidecar first; local ASR only with explicit opt-in.

    "Then silence" is a real outcome, not a failure: `Transcript(engine="none")`
    is a recording with no narration on record, and `stages/ingest.py` renders
    that honestly rather than asserting the video is silent (AT-134)."""
    sidecar = find_sidecar(video)
    if sidecar is not None:
        # A malformed sidecar must not stop media prep; an unreadable one is not a
        # claim of silence, and it keeps its cause (AT-466).
        return Transcript.read_sidecar(sidecar, source_id)

    if not use_whisper or not whisper_available():
        return Transcript(source_id=source_id, engine="none")
    return transcribe_subprocess(video, source_id)


def transcribe_subprocess(video: Path, source_id: str) -> Transcript:
    """Run this module as `__main__` so ctranslate2 cannot take us with it."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "autotester.media.transcribe", str(video)],
            check=True, capture_output=True, text=True, timeout=WHISPER_TIMEOUT_S).stdout
        raw = json.loads(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        return Transcript(source_id=source_id, engine="none")
    return Transcript(source_id=source_id, engine=MODEL,
                      segments=raw.get("segments", []),
                      speech_seconds=float(raw.get("speech_seconds", 0.0)))


def _main(argv: list[str]) -> int:
    """Transcribe and print the sidecar shape on stdout. Isolated by design."""
    from faster_whisper import WhisperModel

    video = Path(argv[0])
    try:
        model = WhisperModel(MODEL, device="cuda", compute_type="int8_float16")
    except Exception:
        model = WhisperModel(MODEL, device="cpu", compute_type="int8")

    segments, _info = model.transcribe(str(video), vad_filter=True)
    rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segments]
    speech = round(sum(r["end"] - r["start"] for r in rows), 2)
    print(json.dumps({"segments": rows, "speech_seconds": speech}))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
