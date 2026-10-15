"""Upload a video to the Files API and wait until the service can actually read it.

The SDK's `files.upload` returns as soon as the bytes are accepted, while the
file is still `PROCESSING`. Passing that handle straight to `generate_content`
fails — sometimes immediately, sometimes as an empty reading that looks like the
model simply saw nothing, which is the worse outcome because it is
indistinguishable from a bad prompt. So the wait is not an optimisation; it is
the difference between an error and a plausible wrong answer.

Uploads are cached: the Files API keeps a file for ~48h, and re-uploading a 200MB
recording for every prompt in an ensemble is the single most expensive avoidable
thing this pipeline can do.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import httpx

from autotester.core.ids import file_sha256
from autotester.providers.attempts import AttemptBudgetExhausted, reserve_attempt
from autotester.providers.base import ProviderError


class GeminiDeadlineTransport(httpx.BaseTransport):
    """Account each wire request; apply remaining time and bound response bytes.

    HTTPX socket timeouts are inactivity limits. Deadline is checked per chunk;
    this is not a hard cancellation guarantee for an in-progress socket read.
    """

    def __init__(self, deadline: float, provider: Any, role: str, *,
                 inner: Any = None, clock: Any = time.monotonic,
                 prompt_file: str | None = None, fed_id: str | None = None) -> None:
        self.deadline, self.provider, self.role = deadline, provider, role
        self.prompt_file, self.fed_id = prompt_file, fed_id
        self.inner = inner if inner is not None else httpx.HTTPTransport(retries=0)
        self.clock = clock

    def remaining(self) -> float:
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise AttemptBudgetExhausted("Gemini shared deadline exhausted")
        return remaining

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        receipt, timeout = reserve_attempt(self.provider.label, self.role, self.remaining())
        self.deadline = min(self.deadline, self.clock() + timeout)
        request.extensions["timeout"] = dict.fromkeys(("connect", "read", "write", "pool"), timeout)
        started = self.clock()
        response = None
        failed = True
        try:
            response = self.inner.handle_request(request)
            body = bytearray()
            for chunk in response.iter_bytes():
                self.remaining()
                if len(body) + len(chunk) > 16 * 1024 * 1024:
                    raise ProviderError("Gemini response exceeded byte limit")
                body.extend(chunk)
            self.remaining()
            failed = response.status_code >= 400
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(response.status_code, headers=headers,
                                  content=bytes(body), request=request)
        finally:
            if response is not None:
                response.close()
            receipt.status = "failed" if failed else "succeeded"
            receipt.latency_s = self.clock() - started
            self.provider.record(self.role, None, None, failed=failed,
                                 latency_s=receipt.latency_s, prompt_file=self.prompt_file,
                                 fed_id=self.fed_id)

    def close(self) -> None:
        self.inner.close()


ACTIVE = "ACTIVE"
FAILED = "FAILED"
CACHE_TTL_S = 46 * 3600
"""Below the service's ~48h retention, so a cache hit is never a dead handle."""


def _state_of(file_obj: Any) -> str:
    state = getattr(file_obj, "state", None)
    return str(getattr(state, "name", state) or "")


def _load_cache(cache_path: Path) -> dict[str, Any]:
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _remember(cache_path: Path, key: str, name: str) -> None:
    cache = _load_cache(cache_path)
    cache[key] = {"name": name, "at": time.time()}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _cached_name(cache_path: Path, key: str) -> str | None:
    entry = _load_cache(cache_path).get(key)
    if not isinstance(entry, dict):
        return None
    if time.time() - float(entry.get("at", 0)) > CACHE_TTL_S:
        return None
    name = entry.get("name")
    return str(name) if name else None


def _cache_key(path: Path) -> str:
    """Content, not size (AT-128).

    The first version keyed on `resolve()::st_size`, which makes a recording
    re-exported in place at the same byte size a cache HIT — serving the OLD
    video under the new file's name, and producing a confident reading of
    footage nobody asked about. `core.ids.file_sha256` was two modules away."""
    return f"{path.resolve()}::{file_sha256(path)}"


def upload_and_wait(client: Any, path: Path, *, cache_path: Path | None = None,
                    timeout_s: float = 600.0, poll_s: float = 2.0,
                    clock: Any = time.monotonic, sleep: Any = time.sleep,
                    deadline: float | None = None) -> Any:
    """Upload `path`, poll until ACTIVE, and return the file handle.

    `clock` and `sleep` are injected so the timeout is testable without one."""
    if not math.isfinite(timeout_s) or timeout_s <= 0 or poll_s <= 0:
        raise ProviderError("Gemini upload limits must be positive and finite")
    deadline = min(deadline, clock() + timeout_s) if deadline is not None else clock() + timeout_s
    if clock() >= deadline:
        raise AttemptBudgetExhausted("Gemini shared deadline exhausted")
    if not path.is_file():
        raise ProviderError(
            f"nothing to upload: {path} is not a readable file")  # AT-135: typed, not FileNotFound
    key = _cache_key(path)
    if cache_path is not None and (name := _cached_name(cache_path, key)):
        try:
            cached = client.files.get(name=name)
            if _state_of(cached) == ACTIVE:
                return cached
        except ProviderError:
            raise
        except Exception:  # a dead handle is a cache miss, not an error
            pass

    try:
        file_obj = client.files.upload(file=str(path))
    except ProviderError:
        raise
    except Exception as exc:  # every SDK failure is a ProviderError (I9)
        raise ProviderError(f"Gemini upload failed: {type(exc).__name__}") from None

    file_obj = _wait_until_active(client, file_obj, deadline, poll_s, clock, sleep)

    if cache_path is not None:
        _remember(cache_path, key, str(file_obj.name))
    return file_obj


def _wait_until_active(client: Any, file_obj: Any, deadline: float, poll_s: float,
                       clock: Any, sleep: Any) -> Any:
    """Poll only within the same transport deadline, never restart it after upload."""
    while _state_of(file_obj) not in (ACTIVE, FAILED):
        if clock() >= deadline:
            raise AttemptBudgetExhausted("Gemini shared deadline exhausted")
        sleep(min(poll_s, max(0, deadline - clock())))
        if clock() >= deadline:
            raise AttemptBudgetExhausted("Gemini shared deadline exhausted")
        try:
            file_obj = client.files.get(name=file_obj.name)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"Gemini polling failed: {type(exc).__name__}") from None

    if clock() >= deadline:
        raise AttemptBudgetExhausted("Gemini shared deadline exhausted")
    if _state_of(file_obj) == FAILED:
        raise ProviderError("Gemini file processing failed")

    return file_obj
