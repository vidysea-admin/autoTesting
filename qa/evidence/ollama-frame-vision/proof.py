"""Byte-preserving isolated guard mutation proof with named pytest failures."""

import ast
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".work/vision-proof-r4"
COPY = OUT / "subject"
VF = "src/autotester/providers/video_frames.py"
SC = "src/autotester/schema/video_frames.py"
LP = "src/autotester/providers/litellm_provider.py"
MC = "src/autotester/providers/model_chain.py"
TESTS = ["tests/test_video_frames.py", "tests/test_video_frame_schema.py",
         "tests/test_litellm_provider.py", "tests/test_model_chain.py",
         "tests/test_provider_attempts.py"]
MUTATIONS = []


def add(name, path, old, new, test, testfile="tests/test_video_frames.py"):
    MUTATIONS.append((name, path, old.encode(), new.encode(), f"{testfile}::{test}"))


add("privacy", VF, "safe = stack.enter_context(sanitized_images([frame]))",
    "safe = type('Unsafe', (), {'paths': [frame]})()",
    "test_real_sanitized_bytes_and_clip_relative_timestamp_payload")
add("timestamps", VF, "{timestamp:.6f}", "{0:.6f}",
    "test_real_sanitized_bytes_and_clip_relative_timestamp_payload")
add("frame-cap", VF, "count = cap if limited else max(1, math.ceil(duration * fps))",
    "count = max(1, math.ceil(duration * fps))",
    "test_real_sanitized_bytes_and_clip_relative_timestamp_payload")
add("partial-index", VF, "index=index, timestamp_s=timestamp", "index=0, timestamp_s=0",
    "test_partial_withholding_retains_original_index_and_time")
add("empty-payload", VF, 'if not any(part["type"] == "image_url" for part in parts):',
    "if False:", "test_all_withheld_never_sends_text_only_success")
add("fps", VF, "if not math.isfinite(fps) or not 0 < fps <= 10:", "if False:",
    "test_invalid_sampling_fails_before_decode")
add("media", VF,
    "if not math.isfinite(duration) or duration <= 0 or width <= 0 or height <= 0:",
    "if False:", "test_decode_audio_and_source_pixel_limits")
add("source-pixels", VF, "if width * height > limits.max_pixels:", "if False:",
    "test_decode_audio_and_source_pixel_limits")
add("capability", VF, '''if not (isinstance(capability, VisionCapability) and capability.passed
            and capability.model == provider.options.get("model")
            and capability.endpoint_sha256 == endpoint_fingerprint(provider)):''',
    "if False:", "test_capability_requires_behavioral_receipt_bound_to_route")
add("attempt-budget", MC, "except AttemptBudgetExhausted:\n"
    "                self._sync_usage()\n                raise",
    "except AttemptBudgetExhausted:\n                self._sync_usage()\n                break",
    "test_repair_and_fallback_obey_shared_physical_budget")
add("fallback", MC, "except ProviderError as exc:\n                self._sync_usage()",
    "except ProviderError as exc:\n                raise\n                self._sync_usage()",
    "test_fallback_serves_configured_model_only")
add("secret-guard", VF, "provider.guard_text(prompt)", "prompt = 'Observe'",
    "test_prompt_secret_guard_precedes_media_processing")
add("png-bytes", VF,
    "if not path.is_file() or not 0 < path.stat().st_size <= limits.max_frame_bytes:",
    "if False:", "test_invalid_extracted_payload_cannot_reach_transport[oversized]")
add("png-format", VF, 'image.format != "PNG" or image.width * image.height > limits.max_pixels',
    "image.width * image.height > limits.max_pixels",
    "test_invalid_extracted_payload_cannot_reach_transport[jpeg]")
add("png-pixels", VF, 'image.format != "PNG" or image.width * image.height > limits.max_pixels',
    'image.format != "PNG"', "test_invalid_extracted_payload_cannot_reach_transport[pixels]")
add("total-bytes", VF, "if total + len(data) > limits.max_total_bytes:", "if False:",
    "test_total_bytes_bound_preserves_partial_coverage")
add("decode-status", VF, 'evidence.reason = "frame_decode_failed"',
    'evidence.reason = "ignored"', "test_failed_frame_decode_is_explicitly_withheld")
add("generation", VF, '''if (options.system_instruction is not None or options.thinking_level != "high"
            or options.media_resolution != "high" or not 0 < options.max_output_tokens <= 65536
            or (options.temperature is not None
                and (not math.isfinite(options.temperature) or not 0 <= options.temperature <= 2))):''',
    "if False:", "test_unsupported_generation_controls_reject_explicitly")  # noqa: E501
add("generation-forward", LP, "kwargs.update(generation_options or {})", "pass",
    "test_real_sanitized_bytes_and_clip_relative_timestamp_payload")
add("limits-shape", VF, "if not isinstance(limits, FrameLimits):", "if False:",
    "test_invalid_limit_shape_and_transport_failures_retain_evidence")
add("failure-coverage", VF, "exc.coverage = coverage", "pass",
    "test_invalid_limit_shape_and_transport_failures_retain_evidence")
add("chain-failure-coverage", MC, "failure.coverage = coverage", "pass",
    "test_chain_failure_retains_visual_shortfall")
add("blocked-before-delivery", LP, "self._require_ready()", "return schema()",
    "test_budget_refusal_preserves_inclusion_without_claiming_delivery")
add("unverified-regression", VF, 'raise FrameVisionError("capability_unverified", coverage)',
    'raise FrameVisionError("wrong_reason", coverage)',
    "test_see_video_without_behavioral_capability_is_unavailable", "tests/test_litellm_provider.py")
schema_test = "tests/test_video_frame_schema.py"
for field, default, _upper in [("max_frames", 16, 64), ("max_pixels", 4000000, 16000000),
                              ("max_frame_bytes", 2000000, 20000000),
                              ("max_total_bytes", 16000000, 64000000)]:
    source = (ROOT / SC).read_bytes().decode()
    line = next(line for line in source.splitlines() if f"    {field}:" in line)
    add(f"schema-{field}", SC, line, f"    {field}: int = {default}",
        "test_frame_limits_are_finite_bounded", schema_test)
for field in ("index", "timestamp_s", "duration_s"):
    source = (ROOT / SC).read_bytes().decode()
    line = next(line for line in source.splitlines() if f"    {field}:" in line)
    add(f"schema-{field}", SC, line, line.replace(", ge=0", "").replace("ge=0", ""),
        "test_coverage_rejects_invalid_duration" if field == "duration_s" else
        "test_frame_evidence_rejects_invalid_index_time_and_status", schema_test)
add("schema-status", SC, 'status: Literal["included", "withheld"]', 'status: str',
    "test_frame_evidence_rejects_invalid_index_time_and_status", schema_test)
for field in ("endpoint_sha256", "fixture_sha256", "output_sha256"):
    add(f"schema-{field}", SC, f'{field}: str = Field(pattern=r"^[0-9a-f]{{64}}$")',
        f'{field}: str', "test_capability_requires_hashes_and_rejects_unknown_fields", schema_test)
source = (ROOT / SC).read_bytes().decode()
for node in ast.parse(source).body:
    if isinstance(node, ast.ClassDef):
        segment = "\n".join(source.splitlines()[node.lineno-1:node.end_lineno])
        add(f"schema-extra-{node.name}", SC, segment,
            segment.replace('extra="forbid"', 'extra="ignore"'),
            "test_capability_requires_hashes_and_rejects_unknown_fields", schema_test)
        if "allow_inf_nan=False" in segment and node.name != "FrameLimits":
            add(f"schema-finite-{node.name}", SC, segment,
                segment.replace("allow_inf_nan=False", "allow_inf_nan=True"),
                "test_coverage_rejects_invalid_duration" if node.name == "FrameCoverage" else
                "test_frame_evidence_rejects_invalid_index_time_and_status", schema_test)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, tests):
    env = dict(os.environ, PYTHONPATH=str(COPY / "src"), PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", "-m", "pytest", *tests, "--tb=short",
               f"--junitxml={OUT / (name + '.xml')}",
               f"--basetemp={OUT / ('tmp-' + name)}"]
    started = time.monotonic()
    started_at = datetime.now(UTC).isoformat()
    result = subprocess.run(command, cwd=COPY, env=env, capture_output=True, timeout=90)
    (OUT / (name + ".log")).write_bytes(result.stdout + result.stderr)
    return {"exit": result.returncode, "duration_s": time.monotonic()-started,
            "started_at": started_at, "ended_at": datetime.now(UTC).isoformat(),
            "command": command, "log_sha256": digest(OUT / (name + ".log"))}


def main():
    assert not OUT.exists(), "use a fresh evidence directory"
    OUT.mkdir(parents=True)
    COPY.mkdir()
    for name in ("src", "tests", "scripts"):
        shutil.copytree(ROOT / name, COPY / name,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    for name in ("pyproject.toml", "uv.lock"):
        (COPY / name).write_bytes((ROOT / name).read_bytes())
    assert (COPY / "tests/tests_mutation_fixtures.py").is_file()
    (COPY / ".work").mkdir()
    preflight = subprocess.run([sys.executable,
        "C:/Users/product/.agents/skills/checker/scripts/review_budget.py", "preflight",
        "--root", str(COPY), "--import-name", "autotester", "--import-root", str(COPY / "src"),
        "--temp-parent", str(COPY / ".work")], cwd=COPY,
        env=dict(os.environ, PYTHONPATH=str(COPY / "src"), PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, timeout=30)
    (OUT / "preflight.log").write_bytes(preflight.stdout + preflight.stderr)
    assert preflight.returncode == 0
    fingerprints = {str(p.relative_to(COPY)): digest(p) for p in COPY.rglob("*") if p.is_file()}
    evidence = {"python": sys.executable, "version": sys.version, "files": fingerprints,
                "proof_sha256": digest(Path(__file__)),
                "preflight_sha256": digest(OUT / "preflight.log"),
                "dependencies": {p: importlib.metadata.version(p) for p in
                                 ("pytest", "pydantic", "Pillow", "litellm", "python-dotenv")},
                "mutations": []}
    evidence["green"] = run("green", TESTS)
    (OUT / "receipts.json").write_text(json.dumps(evidence, indent=2))
    assert evidence["green"]["exit"] == 0
    for name, relative, old, new, test in MUTATIONS:
        path = COPY / relative
        original = path.read_bytes()
        # Worktree bytes may be CRLF; all matching and restoration remain byte exact.
        old, new = old.replace(b"\n", b"\r\n"), new.replace(b"\n", b"\r\n")
        if b"\r\n" not in original:
            old, new = old.replace(b"\r\n", b"\n"), new.replace(b"\r\n", b"\n")
        assert original.count(old) == 1, name
        changed = original.replace(old, new)
        assert changed != original
        path.write_bytes(changed)
        assert path.read_bytes() == changed
        try:
            receipt = run(name, [test])
            tree = ET.parse(OUT / (name + ".xml"))
            failures = [n.attrib["name"] for n in tree.iter("testcase")
                        if n.find("failure") is not None]
            expected = test.split("::")[-1].split("[")[0]
            assert receipt["exit"] == 1 and any(n.split("[")[0] == expected for n in failures), name
            evidence["mutations"].append({"name": name, "source": relative, "test": test,
                "old": old.decode(), "new": new.decode(),
                "source_sha256": hashlib.sha256(original).hexdigest(),
                "mutated_sha256": digest(path), "failures": failures, **receipt})
        finally:
            path.write_bytes(original)
            assert path.read_bytes() == original
        (OUT / "receipts.json").write_text(json.dumps(evidence, indent=2))
        print(name, "KILLED", flush=True)
    evidence["restored"] = run("restored", TESTS)
    assert evidence["restored"]["exit"] == 0
    assert all(digest(COPY / p) == sha for p, sha in fingerprints.items())
    evidence["readiness"] = "all source identities and named green-red-restored receipts verified"
    (OUT / "receipts.json").write_text(json.dumps(evidence, indent=2))
    print(evidence["readiness"], len(MUTATIONS), flush=True)


if __name__ == "__main__":
    main()
