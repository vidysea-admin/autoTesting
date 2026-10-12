"""Test doubles for the `gws` seam: a scripted runner that never starts a process or touches the
network. A script maps the argument list to a `GwsResult`; a download script may also write the
file `gws` would have written (`-o <name>` under the `cwd` it was given)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path

from autotester.sources.gws_runner import GwsResult

CANARY = "ya29.CANARY-TOKEN-do-not-print-0123456789"


def ok_json(payload: dict) -> GwsResult:
    return GwsResult(0, json.dumps(payload), "")


def meta(file_id: str, *, name: str = "demo.mp4", mime: str = "video/mp4",
         size: int | None = None, md5: str | None = None) -> dict:
    out: dict = {"id": file_id, "name": name, "mimeType": mime}
    if size is not None:
        out["size"] = str(size)  # Drive reports sizes as strings
    if md5 is not None:
        out["md5Checksum"] = md5
    return out


def error(code: int, message: str, reason: str = "") -> GwsResult:
    body = {"error": {"code": code, "message": message,
                      "errors": [{"reason": reason, "message": message}]}}
    return GwsResult(1, "", json.dumps(body))


class FakeRunner:
    """`run` answers metadata/list calls; `download` writes `body` as the downloaded file."""

    def __init__(self, on_run: Callable[[Sequence[str]], GwsResult] | None = None, *,
                 body: bytes | Callable[[], bytes] = b"", on_download: GwsResult | None = None):
        self.on_run, self.body, self.on_download = on_run, body, on_download
        self.run_calls: list[list[str]] = []
        self.download_calls: list[dict] = []

    def run(self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: float = 0
            ) -> GwsResult:
        self.run_calls.append(list(args))
        assert self.on_run is not None, "unexpected metadata/list call"
        return self.on_run(args)

    def download(self, args: Sequence[str], *, cwd: Path, out_name: str, max_bytes: int,
                 timeout_s: float) -> GwsResult:
        self.download_calls.append({"args": list(args), "cwd": cwd, "out_name": out_name,
                                    "max_bytes": max_bytes, "timeout_s": timeout_s})
        if self.on_download is not None:
            return self.on_download
        cwd.mkdir(parents=True, exist_ok=True)
        body = self.body() if callable(self.body) else self.body
        (cwd / out_name).write_bytes(body)
        return GwsResult(0, "{}", "")
