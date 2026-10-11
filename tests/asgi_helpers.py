"""Drive the real FastAPI app at the ASGI level with a body the test controls chunk by chunk.

`TestClient` reads a whole request body before the app sees it, so it cannot show that the
server STOPS READING an endless upload. These helpers feed `receive` from a generator, count how
many bytes the app actually pulled, and collect the response.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable, Iterator
from typing import Any

from autotester.ui.app import app

BOUNDARY = "----t198a-boundary"
CHUNK = 64 * 1024


def multipart_head(filename: str, *, label: str | None = "x", extra: dict[str, str] | None = None,
                   field: str = "recording") -> bytes:
    parts = []
    for name, value in {**({"label": label} if label is not None else {}), **(extra or {})}.items():
        parts.append(f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                     f"{value}\r\n")
    parts.append(f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{field}"; '
                 f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n')
    return "".join(parts).encode()


def multipart_tail() -> bytes:
    return f"\r\n--{BOUNDARY}--\r\n".encode()


def chunked(data: bytes, size: int = CHUNK) -> Iterator[bytes]:
    for start in range(0, len(data), size):
        yield data[start:start + size]


class Served:
    """How many request-body bytes the app pulled before it answered."""

    def __init__(self) -> None:
        self.bytes = 0


async def _post(path: str, chunks: Iterable[bytes], headers: dict[str, str], served: Served
                ) -> tuple[int, bytes]:
    iterator = iter(chunks)
    sent: list[dict[str, Any]] = []
    done = {"body": False}

    async def receive() -> dict[str, Any]:
        if done["body"]:
            await asyncio.sleep(0)
            return {"type": "http.disconnect"}
        try:
            chunk = next(iterator)
        except StopIteration:
            done["body"] = True
            return {"type": "http.request", "body": b"", "more_body": False}
        served.bytes += len(chunk)
        return {"type": "http.request", "body": chunk, "more_body": True}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
             "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
             "scheme": "http", "headers": raw_headers, "server": ("testserver", 80),
             "client": ("testclient", 50000), "state": {}}
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, body


def post_stream(path: str, chunks: Iterable[bytes], *, content_length: int | None = None,
                content_type: str | None = None, host: str = "testserver"
                ) -> tuple[int, bytes, Served]:
    """`host` is the Host header (the allow-list refuses none or a wrong one)."""
    headers = {"content-type": content_type or f"multipart/form-data; boundary={BOUNDARY}",
               "host": host}
    if content_length is not None:
        headers["content-length"] = str(content_length)
    served = Served()
    status, body = asyncio.run(_post(path, chunks, headers, served))
    return status, body, served


def endless(head: bytes, cap: int = 3 * 1024**3) -> Iterator[bytes]:
    """A body with no end: the head, then 64 KiB of filler forever (bounded only so a broken
    server fails the test instead of hanging it)."""
    yield head
    sent = 0
    while sent < cap:
        sent += CHUNK
        yield b"z" * CHUNK


__all__ = [
    "BOUNDARY",
    "CHUNK",
    "AsyncIterator",
    "Served",
    "chunked",
    "endless",
    "multipart_head",
    "multipart_tail",
    "post_stream",
]
