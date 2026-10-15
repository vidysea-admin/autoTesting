"""Offline SDK transport safety proofs; no claim of model audio understanding."""
import io
import itertools
import json
import wave
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from autotester.providers.attempts import AttemptBudgetExhausted, attempt_budget
from autotester.providers.base import ProviderError
from autotester.providers.gemini import GeminiProvider
from autotester.providers.gemini_files import GeminiDeadlineTransport, upload_and_wait
from autotester.schema.transcription import GeminiTranscription


@pytest.fixture(autouse=True)
def isolated_secret_guard(monkeypatch):
    from autotester.providers.litellm_provider import LiteLLMProvider

    monkeypatch.setattr(LiteLLMProvider, "_secret_values", lambda self: self._extra_secrets)


class GuardAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int


def sdk_fake(monkeypatch, answers, *, status=200):
    calls = []

    def handle(request):
        calls.append(request)
        if status != 200:
            return httpx.Response(status,
                json={"error": {"code": status, "message": "SECRET-ECHO"}})
        answer = answers[min(len(calls) - 1, len(answers) - 1)]
        return httpx.Response(200, json={"candidates": [{"content": {"role": "model",
            "parts": [{"text": json.dumps(answer)}]}, "finishReason": "STOP"}]})

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kw: httpx.MockTransport(handle))
    return calls


def test_sdk_json_repair_is_strict_and_bounded(monkeypatch):
    calls = sdk_fake(monkeypatch, [{"count": "3"}, {"count": 3}])
    provider = GeminiProvider(api_key="fake-test-key")
    with attempt_budget(3) as budget:
        assert provider.judge("count", GuardAnswer).count == 3
    assert len(calls) == budget.used == 2
    assert all(a.status == "succeeded" and a.input_tokens is None for a in budget.attempts)
    assert provider.usage[0].calls == 2 and provider.usage[0].input_tokens is None


def test_sdk_bad_json_stops_after_one_repair(monkeypatch):
    calls = sdk_fake(monkeypatch, [{"count": "wrong", "secret": "SECRET-ECHO"}])
    with pytest.raises(ProviderError, match="does not fit") as error:
        GeminiProvider(api_key="fake-test-key").act("count", GuardAnswer)
    assert len(calls) == 2 and "SECRET-ECHO" not in str(error.value)


def test_sdk_retries_disabled_failure_accounted_and_safe(monkeypatch):
    calls = sdk_fake(monkeypatch, [], status=503)
    provider = GeminiProvider(api_key="fake-test-key")
    with attempt_budget(5) as budget, pytest.raises(ProviderError) as error:
        provider.act("count", GuardAnswer)
    assert len(calls) == budget.used == 1
    assert budget.attempts[0].status == "failed"
    assert "SECRET-ECHO" not in str(error.value)
    assert provider.usage[0].failed_calls == 1


def test_sdk_global_budget_cannot_retry_or_send(monkeypatch):
    calls = sdk_fake(monkeypatch, [{"count": "bad"}])
    with attempt_budget(1) as budget, pytest.raises(ProviderError):
        GeminiProvider(api_key="fake-test-key").judge("count", GuardAnswer)
    assert len(calls) == budget.used == 1


def test_secret_and_system_instruction_guard_precedes_transport(monkeypatch):
    calls = sdk_fake(monkeypatch, [{"count": 1}])
    from autotester.schema.observation import VisionOptions

    provider = GeminiProvider(api_key="fake-test-key", secrets=["secret-canary-long"])
    with pytest.raises(ProviderError, match="withheld"):
        provider.act("secret-canary-long", GuardAnswer)
    with pytest.raises(ProviderError, match="withheld"):
        provider.see_video(Path("missing.wav"), "safe", GuardAnswer,
                           VisionOptions(system_instruction="secret-canary-long"))
    assert calls == []


def wav_bytes():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * 160)
    return stream.getvalue()


def test_narration_inline_wav_no_files_upload_or_asr(monkeypatch, tmp_path):
    calls = sdk_fake(monkeypatch, [{"segments": [{"start": 0.0, "end": 0.01, "text": "hi"}]}])
    path = tmp_path / "narration.wav"
    path.write_bytes(wav_bytes())
    result = GeminiProvider(api_key="fake-test-key").see_video(
        path, "transcribe", GeminiTranscription)
    assert result.segments[0].text == "hi" and len(calls) == 1
    assert ":generateContent" in str(calls[0].url)
    body = json.loads(calls[0].content)
    assert body["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "audio/wav"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("suffix,data", [(".mp4", b"video"), (".wav", b"video"),
    (".wav", wav_bytes() + b"x" * (16 * 1024 * 1024 + 1))],
    ids=["raw-video", "invalid-wav", "oversized"])
def test_narration_rejects_raw_video_invalid_or_oversized_audio(
    monkeypatch, tmp_path, suffix, data,
):
    calls = sdk_fake(monkeypatch, [{"segments": []}])
    path = tmp_path / ("narration" + suffix)
    path.write_bytes(data)
    with pytest.raises(ProviderError):
        GeminiProvider(api_key="fake-test-key").see_video(path, "transcribe", GeminiTranscription)
    assert calls == []


def test_per_wire_deadline_decreases_and_records_failure():
    now = [0.0]
    timeouts = []

    def handle(request):
        timeouts.append(request.extensions["timeout"]["read"])
        now[0] += 2
        if len(timeouts) == 3:
            raise httpx.ReadTimeout("SECRET-ECHO")
        return httpx.Response(200, content=b"ok")

    provider = GeminiProvider(api_key="fake-test-key")
    transport = GeminiDeadlineTransport(10, provider, "vision",
        inner=httpx.MockTransport(handle), clock=lambda: now[0])
    with attempt_budget(4) as budget, httpx.Client(transport=transport) as client:
        client.post("https://example.test/upload")
        client.get("https://example.test/poll")
        with pytest.raises(httpx.ReadTimeout):
            client.post("https://example.test/generate")
    assert timeouts == [10, 8, 6]
    assert [a.status for a in budget.attempts] == ["succeeded", "succeeded", "failed"]
    assert provider.usage[0].failed_calls == 1


def test_expired_deadline_is_zero_request():
    transport = GeminiDeadlineTransport(0, GeminiProvider(api_key="fake"), "vision",
        clock=lambda: 1)
    with attempt_budget(3) as budget, pytest.raises(AttemptBudgetExhausted):
        transport.handle_request(httpx.Request("GET", "https://example.test"))
    transport.close()
    assert budget.used == 0


def test_upload_deadline_includes_upload_time(tmp_path):
    now = [0.0]

    class Files:
        def upload(self, **kwargs):
            now[0] = 5
            return type("Handle", (), {"name": "files/x", "state": "ACTIVE"})()

    path = tmp_path / "safe.mp4"
    path.write_bytes(b"safe")
    client = type("Client", (), {"files": Files()})()
    with pytest.raises(AttemptBudgetExhausted):
        upload_and_wait(client, path, timeout_s=4, clock=lambda: now[0])


def test_transport_closes_and_rejects_late_or_large_response():
    class Stream(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield b"x" * (16 * 1024 * 1024 + 1)

        def close(self):
            self.closed = True

    stream = Stream()
    inner = httpx.MockTransport(lambda req: httpx.Response(200, stream=stream))
    transport = GeminiDeadlineTransport(20, GeminiProvider(api_key="fake"), "vision",
        inner=inner, clock=lambda: 0)
    with attempt_budget(1) as budget, pytest.raises(ProviderError, match="byte limit"):
        transport.handle_request(httpx.Request("GET", "https://example.test"))
    transport.close()
    assert stream.closed and budget.attempts[0].status == "failed"


def test_real_sdk_resumable_upload_poll_generate_each_counted(monkeypatch, tmp_path):
    import autotester.providers.gemini_files as files_module

    requests = []

    def handle(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, headers={"x-goog-upload-url": "https://example.test/chunk"},
                                  json={"file": {"name": "files/test", "mimeType": "video/mp4"}})
        if len(requests) == 2:
            return httpx.Response(200, headers={"x-goog-upload-status": "final"},
                json={"file": {"name": "files/test", "state": "PROCESSING",
                               "mimeType": "video/mp4", "uri": "https://example.test/file"}})
        if len(requests) == 3:
            return httpx.Response(200, json={"name": "files/test", "state": "ACTIVE",
                "mimeType": "video/mp4", "uri": "https://example.test/file"})
        return httpx.Response(200, json={"candidates": [{"content": {"role": "model",
            "parts": [{"text": '{"count":1}'}]}, "finishReason": "STOP"}]})

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kw: httpx.MockTransport(handle))
    # Keep the SDK upload/poll logic real; shorten only the local polling sleep.
    original = files_module.upload_and_wait
    monkeypatch.setattr("autotester.providers.gemini.upload_and_wait",
        lambda *a, **kw: original(*a, **kw, poll_s=0.001))
    path = tmp_path / "safe.mp4"
    path.write_bytes(b"sanitized-test-fixture")
    with attempt_budget(4) as budget:
        assert GeminiProvider(api_key="fake-test-key").see_video(
            path, "count", GuardAnswer).count == 1
    assert len(requests) == budget.used == 4
    timeouts = [r.extensions["timeout"]["read"] for r in requests]
    assert all(0 < b <= a <= 120 for a, b in itertools.pairwise(timeouts))


def test_upload_poll_deadline_sends_no_late_poll(tmp_path):
    now = [0.0]

    class Files:
        def upload(self, **kwargs):
            return type("Handle", (), {"name": "files/x", "state": "PROCESSING"})()

        def get(self, **kwargs):
            pytest.fail("poll crossed the shared deadline")

    path = tmp_path / "safe.mp4"
    path.write_bytes(b"safe")
    client = type("Client", (), {"files": Files()})()
    with pytest.raises(AttemptBudgetExhausted):
        upload_and_wait(client, path, timeout_s=1, clock=lambda: now[0],
                        sleep=lambda delay: now.__setitem__(0, now[0] + delay))


def test_stream_chunk_and_terminal_deadline_close_failed_receipt():
    now = [0.0]

    class LateStream(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            now[0] = 3
            yield b"late"

        def close(self):
            self.closed = True

    stream = LateStream()
    transport = GeminiDeadlineTransport(2, GeminiProvider(api_key="fake"), "vision",
        inner=httpx.MockTransport(lambda req: httpx.Response(200, stream=stream)),
        clock=lambda: now[0])
    with attempt_budget(1) as budget, pytest.raises(AttemptBudgetExhausted):
        transport.handle_request(httpx.Request("GET", "https://example.test"))
    transport.close()
    assert stream.closed and budget.attempts[0].status == "failed"


def test_nested_global_deadline_rejects_late_response(monkeypatch):
    import autotester.providers.attempts as attempts_module

    now = [0.0]
    monkeypatch.setattr(attempts_module.time, "monotonic", lambda: now[0])

    def handle(request):
        assert request.extensions["timeout"]["read"] == 1
        now[0] = 2
        return httpx.Response(200, content=b"late")

    transport = GeminiDeadlineTransport(120, GeminiProvider(api_key="fake"), "vision",
        inner=httpx.MockTransport(handle), clock=lambda: now[0])
    # Rejection covers the transport and the enclosing logical-completion deadline.
    with pytest.raises(AttemptBudgetExhausted), attempt_budget(2, 1) as budget:
        transport.handle_request(httpx.Request("GET", "https://example.test"))
    transport.close()
    assert budget.used == 1 and budget.attempts[0].status == "failed"
