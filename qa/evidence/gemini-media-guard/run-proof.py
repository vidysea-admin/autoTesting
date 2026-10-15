"""Byte-bound isolated mutations for Gemini media guards; offline only."""
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "qa/evidence/gemini-media-guard"
COPY = ROOT / ".work/gemini-mutation"
for name in ("src", "tests", "scripts"):
    shutil.copytree(ROOT / name, COPY / name, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
shutil.copy2(ROOT / "pyproject.toml", COPY / "pyproject.toml")
(COPY / ".work").mkdir(exist_ok=True)
env = dict(os.environ, PYTHONPATH=str(COPY / "src"))
results = []


def run(label, args):
    start = time.monotonic()
    result = subprocess.run([sys.executable, *args], cwd=COPY, env=env,
                            capture_output=True, timeout=60)
    log = OUT / (label + ".log")
    log.write_bytes(result.stdout + result.stderr)
    row = dict(label=label, command=args, exit=result.returncode,
               duration_s=time.monotonic()-start, log=str(log),
               log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    results.append(row)
    (OUT / "results.json").write_bytes(json.dumps(results, indent=2).encode())
    return result


run("preflight", ["C:/Users/product/.agents/skills/checker/scripts/review_budget.py", "preflight",
    "--root", str(COPY), "--import-name", "autotester", "--import-root", str(COPY / "src"),
    "--temp-parent", str(COPY / ".work")]).check_returncode()
TEST = "tests/test_gemini_media_guard.py"
base = run("mutation-green", ["-m", "pytest", TEST, "tests/test_gemini_truncation_guard.py", "--basetemp", ".work/base"])
base.check_returncode()
G = "src/autotester/providers/gemini.py"
F = "src/autotester/providers/gemini_files.py"
mutations = [
    ("truncation-diagnostic", G, '== "MAX_TOKENS" for c in candidates):',
     '== "NEVER" for c in candidates):', "TRUNCATION"),
    ("global-deadline-clamp", F, 'self.deadline = min(self.deadline, self.clock() + timeout)',
     'pass', "test_nested_global_deadline_rejects_late_response"),
    ("wire-reservation", F, 'receipt, timeout = reserve_attempt(self.provider.label, self.role, self.remaining())',
     'from autotester.schema.provider_attempt import ProviderAttempt; receipt, timeout = ProviderAttempt(provider="gemini", role=self.role), self.remaining()',
     "test_sdk_global_budget_cannot_retry_or_send"),
    ("remaining-timeout", F, 'timeout)', '120.0)', "test_per_wire_deadline_decreases_and_records_failure"),
    ("response-byte-cap", F, 'if len(body) + len(chunk) > 16 * 1024 * 1024:', 'if False:',
     "test_transport_closes_and_rejects_late_or_large_response"),
    ("deadline-expiry", F, 'if remaining <= 0:', 'if False:', "test_stream_chunk_and_terminal_deadline_close_failed_receipt"),
    ("sdk-retries", G, 'HttpRetryOptions(attempts=1)', 'HttpRetryOptions(attempts=2)',
     "test_sdk_retries_disabled_failure_accounted_and_safe"),
    ("strict-json", G, 'strict=True', 'strict=False', "test_sdk_json_repair_is_strict_and_bounded"),
    ("repair-cap", G, 'for _ in range(2):', 'for _ in range(3):',
     "test_sdk_bad_json_stops_after_one_repair"),
    ("prompt-guard", G, 'guard.guard_text(prompt)', 'pass',
     "test_secret_and_system_instruction_guard_precedes_transport"),
    ("system-guard", G, 'guard.guard_text(options.system_instruction)', 'pass',
     "test_secret_and_system_instruction_guard_precedes_transport"),
    ("raw-video-refusal", G, 'if schema is GeminiTranscription and (video_path is None or',
     'if False and (video_path is None or',
     "test_narration_rejects_raw_video_invalid_or_oversized_audio[raw-video]"),
    ("audio-byte-cap", G, 'if len(data) > 16 * 1024 * 1024:', 'if False:',
     "test_narration_rejects_raw_video_invalid_or_oversized_audio[oversized]"),
    ("audio-format", G, 'with wave.open(io.BytesIO(data), "rb") as audio:',
     'with __import__("contextlib").nullcontext(type("FakeAudio", (), {"getcomptype": lambda self: "NONE"})()) as audio:',
     "test_narration_rejects_raw_video_invalid_or_oversized_audio[invalid-wav]"),
    ("safe-errors", G, 'request failed: {type(exc).__name__}', 'request failed: {type(exc).__name__}: {exc}',
     "test_sdk_retries_disabled_failure_accounted_and_safe"),
]
for index, (label, relative, old, new, node) in enumerate(mutations, 1):
    path = COPY / relative
    original = path.read_bytes()
    assert old.encode() in original, label
    changed = original.replace(old.encode(), new.encode())
    assert changed != original
    ast.parse(changed)
    path.write_bytes(changed)
    assert path.read_bytes() == changed
    result = run(f"mutation-{index:02}-{label}", ["-m", "pytest", ("tests/test_gemini_truncation_guard.py::test_gemini_truncated_response_is_not_json_repair"
                 if node == "TRUNCATION" else f"{TEST}::{node}"),
                 "--basetemp", f".work/m{index}"])
    results[-1].update(source=relative, original_sha256=hashlib.sha256(original).hexdigest(),
        mutated_sha256=hashlib.sha256(changed).hexdigest(), mutation_old=old, mutation_new=new,
        attributable=result.returncode == 1 and b"FAILED" in result.stdout and (b"test_gemini_truncated_response_is_not_json_repair"
            if node == "TRUNCATION" else node.encode()) in result.stdout)
    path.write_bytes(original)
    assert path.read_bytes() == original
    (OUT / "results.json").write_bytes(json.dumps(results, indent=2).encode())
    if not results[-1]["attributable"]:
        raise RuntimeError("mutation missing named red: " + label)
run("mutation-restored-green", ["-m", "pytest", TEST, "tests/test_gemini_truncation_guard.py", "--basetemp", ".work/restored"]).check_returncode()
print(json.dumps({"mutations": len(mutations), "all_named_red": True, "restored_green": True}))
