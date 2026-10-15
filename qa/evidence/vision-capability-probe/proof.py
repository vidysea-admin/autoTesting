"""Serial, byte-exact capability-probe mutation bursts over self-contained tests."""

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
OUT = ROOT / ".work/probe-proof"
COPY = OUT / "subject"
VF = "src/autotester/providers/vision_probe.py"
SC = "src/autotester/schema/vision_probe.py"
CAP = "src/autotester/schema/video_frames.py"
TEST = "tests/test_vision_probe.py"
SCHEMA_TEST = "tests/test_vision_probe_schema.py"
TESTS = [TEST, SCHEMA_TEST]
MUTATIONS = []


def add(name, path, old, new, test, testfile=TEST):
    MUTATIONS.append({"name": name, "file": path, "old": old, "new": new,
                      "kills": [testfile + "::" + test]})


positive = "test_probe_bootstraps_from_actual_sanitized_pixels_and_binds_receipt"
randomized = "test_random_draws_are_independent_and_answers_are_not_in_prompt"
invalid = "test_invalid_sanitized_payload_cannot_become_filename_only_success"
add("sanitized-pixels", VF, "batch = stack.enter_context(sanitized_images([path]))",
    "batch = type('Unsafe', (), {'paths': [path], 'withheld': 0})()", positive)
add("fixture-binding", VF, "fixture_sha256=fixture_hash,", 'fixture_sha256="0" * 64,', positive)
add("output-binding", VF,
    "output_sha256=hashlib.sha256(observed.model_dump_json().encode()).hexdigest(),",
    'output_sha256="0" * 64,', positive)
add("prompt-binding", VF, "prompt_sha256=prompt_hash)", 'prompt_sha256="0" * 64)', positive)
add("protocol-binding", VF, "probe_protocol=PROTOCOL,", "probe_protocol=None,", positive)
add("model-binding", VF, "model=result.model,", 'model="wrong-model",', positive)
add("independent-draws", VF,
    "shapes, colors = rng.sample(_SHAPES, 2), rng.sample(tuple(_COLORS), 2)",
    "shapes, colors = _SHAPES[:2], tuple(_COLORS)[:2]", randomized)
add("no-answer-leak", VF, "observed = provider.judge(prompt, VisualProbeAnswer,",
    "observed = provider.judge(prompt + result.expected.model_dump_json(), VisualProbeAnswer,",
    randomized)
add("visual-mismatch", VF, "elif observed != expected:", "elif False:",
    "test_visual_mismatch_is_inconclusive_never_a_capability")
add("repair-cap", VF, "with attempt_budget(2, wall_clock_s=45) as budget:",
    "with attempt_budget(1, wall_clock_s=45) as budget:",
    "test_one_json_repair_shares_the_probe_physical_budget")
add("sanitation-withheld", VF, "if len(batch.paths) != 1 or batch.withheld:", "if False:",
    "test_sanitation_failure_withholds_every_request")
add("budget-propagation", VF,
    'except AttemptBudgetExhausted as exc:\n            result.reason = "budget_exhausted"\n'
    "            exc.probe_result = result\n            raise",
    'except AttemptBudgetExhausted as exc:\n            result.reason = "budget_exhausted"\n'
    "            exc.probe_result = result", "test_enclosing_zero_budget_stops_before_transport")
add("two-physical-calls", VF, "with attempt_budget(2, wall_clock_s=45) as budget:",
    "with attempt_budget(3, wall_clock_s=45) as budget:",
    "test_two_call_probe_cap_is_physical_and_raises_instead_of_falling_back")
add("deadline", VF, "with attempt_budget(2, wall_clock_s=45) as budget:",
    "with attempt_budget(2, wall_clock_s=None) as budget:", positive)
add("privacy-not-availability", VF, "except AvailabilityFailure:",
    "except (AvailabilityFailure, ProviderError):",
    "test_sdk_errors_are_safe_and_only_availability_is_unavailable")
add("endpoint-binding", VF, "if (provider._model != result.model\n"
    "            or endpoint_fingerprint(provider) != result.endpoint_sha256):", "if False:",
    "test_receipt_requires_physical_success_and_stable_route")
add("physical-success", VF,
    'elif (not budget.attempts or budget.attempts[-1].status != "succeeded"\n'
    '          or any(attempt.provider != label for attempt in budget.attempts)):',
    "elif False:",
    "test_receipt_requires_physical_success_and_stable_route")
add("physical-model-binding", VF,
    'or any(attempt.provider != label for attempt in budget.attempts)',
    "or False", "test_another_models_physical_attempt_cannot_certify_this_model")
add("unavailable", VF, "if not provider.available():", "if False:",
    "test_unavailable_or_non_explicit_provider_cannot_start_probe")
add("explicit-provider", VF, "if not isinstance(provider, LiteLLMProvider):", "if False:",
    "test_unavailable_or_non_explicit_provider_cannot_start_probe")
add("configuration-secret", VF, "provider.guard_text(provider._model)", "pass",
    "test_secret_model_config_is_withheld_before_artifact_or_transport")
add("safe-configuration-error", VF,
    'raise ProviderError("vision probe model configuration withheld") from None', "raise",
    "test_secret_model_config_is_withheld_before_artifact_or_transport")
add("image-byte-cap", VF, "if not path.is_file() or not 0 < path.stat().st_size <= 100_000:",
    "if False:", invalid + "[oversized]")
add("png-mime", VF, 'if image.format != "PNG" or image.size != _SIZE:',
    "if image.size != _SIZE:", invalid + "[jpeg]")
add("image-pixels", VF, 'if image.format != "PNG" or image.size != _SIZE:',
    'if image.format != "PNG":', invalid + "[dimensions]")
add("immutable-attempt-snapshot", VF,
    "[attempt.model_copy(deep=True) for attempt in budget.attempts]",
    "list(budget.attempts)", positive)
for name in ("left_shape", "right_shape", "left_color", "right_color"):
    old = next(line for line in (ROOT / SC).read_bytes().decode().splitlines()
               if line.startswith("    " + name + ":"))
    add("vocabulary-" + name, SC, old, "    " + name + ": str",
        "test_neutral_answer_vocabulary_is_closed", SCHEMA_TEST)
add("two-answers", SC, "Field(min_length=2, max_length=2)", "Field()",
    "test_exactly_two_images_and_no_extra_fields", SCHEMA_TEST)
text = (ROOT / SC).read_bytes().decode()
for node in ast.parse(text).body:
    if isinstance(node, ast.ClassDef) and node.name in {"VisualProbeAnswer", "VisualProbeReading"}:
        segment = ast.get_source_segment(text, node)
        add("extra-" + node.name, SC, segment,
            segment.replace('extra="forbid"', 'extra="ignore"'),
            "test_exactly_two_images_and_no_extra_fields", SCHEMA_TEST)
extension = "test_probe_status_is_explicit_and_capability_extension_is_backward_compatible"
add("probe-status", SC, 'Literal["verified", "unavailable", "inconclusive"]', "str",
    extension, SCHEMA_TEST)
add("receipt-protocol", CAP, 'Literal["sanitized-layout-pair-v1"] | None', "str | None",
    extension, SCHEMA_TEST)
add("receipt-prompt-hash", CAP,
    'prompt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")',
    "prompt_sha256: str | None = None", extension, SCHEMA_TEST)
add("legacy-prompt-default", CAP, 'default=None, pattern=r"^[0-9a-f]{64}$"',
    'default="0" * 64, pattern=r"^[0-9a-f]{64}$"', extension, SCHEMA_TEST)
add("legacy-protocol-default", CAP,
    'probe_protocol: Literal["sanitized-layout-pair-v1"] | None = None',
    'probe_protocol: Literal["sanitized-layout-pair-v1"] | None = "sanitized-layout-pair-v1"',
    extension, SCHEMA_TEST)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, tests):
    env = dict(os.environ, PYTHONPATH=str(COPY / "src"), PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", "-m", "pytest", "--noconftest", *tests, "--tb=short",
               f"--junitxml={OUT / (name + '.xml')}", f"--basetemp={OUT / ('tmp-' + name)}"]
    start, timestamp = time.monotonic(), datetime.now(UTC).isoformat()
    proc = subprocess.run(command, cwd=COPY, env=env, capture_output=True, timeout=90)
    log = OUT / (name + ".log")
    log.write_bytes(proc.stdout + proc.stderr)
    return {"phase": name, "command": command, "exit": proc.returncode,
            "started_at": timestamp, "ended_at": datetime.now(UTC).isoformat(),
            "duration_s": time.monotonic()-start, "log_sha256": digest(log)}


def init():
    names = [mutation["name"] for mutation in MUTATIONS]
    assert len(names) == len(set(names)), "duplicate mutation identity"
    for name in (VF, SC, CAP, TEST, SCHEMA_TEST):
        text = (ROOT / name).read_bytes().decode()
        assert len(text.splitlines()) <= 300, name
        assert all(node.end_lineno-node.lineno <= 50 for node in ast.walk(ast.parse(text))
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))), name
    assert not OUT.exists(), "preserve prior evidence and choose a fresh OUT for a retry"
    COPY.mkdir(parents=True)
    for name in ("src", "tests", "scripts"):
        shutil.copytree(ROOT / name, COPY / name,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    for name in ("pyproject.toml", "uv.lock"):
        (COPY / name).write_bytes((ROOT / name).read_bytes())
    (COPY / ".work").mkdir()
    assert (COPY / "tests/tests_mutation_fixtures.py").is_file()
    files = {str(p.relative_to(COPY)).replace("\\", "/"): digest(p)
             for p in COPY.rglob("*") if p.is_file()}
    expected = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p)
                for name in ("src", "tests", "scripts") for p in (ROOT / name).rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}
    assert all(files[path] == sha for path, sha in expected.items())
    command = [sys.executable, "C:/Users/product/.agents/skills/checker/scripts/review_budget.py",
               "preflight", "--root", str(COPY), "--import-name", "autotester",
               "--import-root", str(COPY / "src"), "--temp-parent", str(COPY / ".work")]
    proc = subprocess.run(command, cwd=COPY, capture_output=True, timeout=30,
                          env=dict(os.environ, PYTHONPATH=str(COPY / "src")))
    (OUT / "preflight.log").write_bytes(proc.stdout + proc.stderr)
    assert proc.returncode == 0
    data = {"root": str(ROOT), "python": sys.executable, "version": sys.version,
            "files": files, "instrument_sha256": digest(Path(__file__)),
            "preflight_sha256": digest(OUT / "preflight.log"), "mutations": [], "bursts": [],
            "dependencies": {name: importlib.metadata.version(name) for name in
                             ("pydantic", "Pillow", "pytest", "litellm", "python-dotenv")},
            "fixture_isolation": "Owner authorized --noconftest ONLY for these two new self-contained modules. "
            "test_vision_probe imports actual socket-denial no_network fixture from litellm_fake and applies "
            "it to every test; transport is local to this module. No auth/queue/consumer paths need global "
            "conftest; schema module makes no calls. Full src/tests/scripts inventory retained; integration "
            "must use normal pytest/security fixtures.", "baseline": run("baseline", TESTS)}
    (OUT / "receipts.json").write_text(json.dumps(data, indent=2))
    assert data["baseline"]["exit"] == 0
    print("BASELINE_GREEN", len(MUTATIONS), flush=True)


def burst(count):
    data = json.loads((OUT / "receipts.json").read_bytes())
    assert data["baseline"]["exit"] == 0
    assert data["instrument_sha256"] == digest(Path(__file__))
    assert all(digest(COPY / path) == sha for path, sha in data["files"].items())
    start = len(data["mutations"])
    for mutation in MUTATIONS[start:start+count]:
        name, path = mutation["name"], COPY / mutation["file"]
        original = path.read_bytes()
        old, new = mutation["old"].encode(), mutation["new"].encode()
        if original.count(old) == 0 and b"\r\n" in original:
            old, new = old.replace(b"\n", b"\r\n"), new.replace(b"\n", b"\r\n")
        assert original.count(old) == 1, name
        changed = original.replace(old, new)
        assert changed != original
        path.write_bytes(changed)
        assert path.read_bytes() == changed
        try:
            row = run(name, mutation["kills"])
            failures = [node.attrib["name"] for node in ET.parse(OUT / (name + ".xml")).iter("testcase")
                        if node.find("failure") is not None]
            expected = mutation["kills"][0].split("::")[-1].split("[")[0]
            row |= {**mutation, "source_sha256": digest(ROOT / mutation["file"]),
                    "mutated_sha256": digest(path), "failures": failures}
            assert row["exit"] == 1 and any(f.split("[")[0] == expected for f in failures), name
            data["mutations"].append(row)
        finally:
            path.write_bytes(original)
            assert path.read_bytes() == original
        (OUT / "receipts.json").write_text(json.dumps(data, indent=2))
        print(name, "KILLED", flush=True)
    restored = run(f"restored-{len(data['mutations'])}", TESTS)
    data["bursts"].append({"start": start, "end": len(data["mutations"]), "restored": restored})
    (OUT / "receipts.json").write_text(json.dumps(data, indent=2))
    assert restored["exit"] == 0
    assert all(digest(COPY / path) == sha for path, sha in data["files"].items())
    if len(data["mutations"]) == len(MUTATIONS):
        data["readiness"] = "VALID: complete named green/red/restored chains and byte-exact source"
        (OUT / "receipts.json").write_text(json.dumps(data, indent=2))
    print("RESTORED_GREEN", len(data["mutations"]), "of", len(MUTATIONS), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "init":
        init()
    elif sys.argv[1] == "burst":
        burst(int(sys.argv[2]))
