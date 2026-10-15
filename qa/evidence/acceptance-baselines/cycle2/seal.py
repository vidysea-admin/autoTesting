"""Validate retained cycle 2 command and source receipts without rerunning tests."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[4]
out = root / "qa/evidence/acceptance-baselines/cycle2"
sha = lambda blob: hashlib.sha256(blob).hexdigest()
identity = json.loads((out / "identity.json").read_bytes())
spec = json.loads((out / "mutation.json").read_bytes())
proof = json.loads((out / "proof.json").read_bytes())
commands = json.loads((out / "commands.json").read_bytes())
assert [c["label"] for c in commands] == ["preflight", "green", "red", "restored", "lint", "shape"]
for c in commands:
    path = out / (c["label"] + ".log")
    assert sha(path.read_bytes()) == c["output_sha256"]
    assert c["identity_sha256"] == sha((out / "identity.json").read_bytes())
    assert c["spec_sha256"] == sha((out / "mutation.json").read_bytes())
    if c["report_sha256"]:
        assert sha(path.with_suffix(".report.json").read_bytes()) == c["report_sha256"]
    assert c["exit_code"] == (1 if c["label"] == "red" else 0)
stage = spec["file"]
before = (root / stage).read_bytes()
assert before.count(spec["old"].encode()) == 1
mutated = before.replace(spec["old"].encode(), spec["new"].encode(), 1)
assert proof["original_sha256"] == proof["restored_sha256"] == sha(before)
assert proof["mutated_sha256"] == sha(mutated)
assert proof["failed"] == spec["kills"]
for c in commands:
    assert c["source_sha256"][stage] == sha(mutated if c["label"] == "red" else before)
for path, fingerprint in identity["source_sha256"].items():
    assert sha((root / path).read_bytes()) == fingerprint
    blob = subprocess.check_output(["git", "show", identity["code_sha"] + ":" + path], cwd=root)
    assert blob == (root / path).read_bytes()
assert identity["harness_sha256"] == sha((out / "probe.py").read_bytes())
assert identity["inventory_sha256"] == sha((out / "inventory.json").read_bytes())
assert identity["lock_sha256"] == sha((root / "uv.lock").read_bytes())
entries = json.loads((out / "inventory.json").read_bytes())
copy = root / ".work/baseline-proofs-cycle2"
for path, fingerprint in entries.items():
    assert sha((root / path).read_bytes()) == sha((copy / path).read_bytes()) == fingerprint
verdict = subprocess.check_output(["git", "show", identity["base_fail_sha"] + ":qa/verdicts/acceptance-baselines.md"], cwd=root)
assert verdict == (out / "cycle1-verdict.git.md").read_bytes()
result = dict(kind="maker-readiness-only", code_sha=identity["code_sha"],
              complete_source_entries=len(entries), bound_commands=len(commands),
              named_guard_proofs=1, historical_proofs_reused=13,
              command_seconds=proof["command_seconds"], active_seconds=None, tokens=None, cost=None)
(out / "readiness.json").write_bytes(json.dumps(result, indent=2).encode())
print(json.dumps(result))
