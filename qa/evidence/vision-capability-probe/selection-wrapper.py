"""Run an explicitly authorized risk selection without changing the frozen harness."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".work/probe-proof"
SPEC = ROOT / ".work/probe-selection.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


spec = json.loads(SPEC.read_bytes())
assert sha(Path(__file__).read_bytes()) == spec["wrapper_sha256"]
instrument = ROOT / "qa/evidence/vision-capability-probe/proof.py"
assert sha(instrument.read_bytes()) == spec["instrument_sha256"]
snapshot = OUT / "receipts-before-selection.json"
assert sha(snapshot.read_bytes()) == spec["initial_receipts_sha256"]
data = json.loads((OUT / "receipts.json").read_bytes())
assert sha(json.dumps(data["mutations"][:20], sort_keys=True).encode()) == spec["prefix_sha256"]
assert data["files"] == spec["source_inventory"]
for path, expected in spec["source_inventory"].items():
    assert sha((ROOT / path).read_bytes()) == expected, path
    assert sha((OUT / "subject" / path).read_bytes()) == expected, path
module_spec = importlib.util.spec_from_file_location("frozen_probe_proof", instrument)
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
assert [row["name"] for row in module.MUTATIONS] == spec["original_ids"]
by_name = {row["name"]: row for row in module.MUTATIONS}
module.MUTATIONS[:] = [by_name[name] for name in spec["selected_ids"]]
assert [row["name"] for row in data["mutations"]] == spec["selected_ids"][:len(data["mutations"])]
data["selection"] = {"spec_sha256": sha(SPEC.read_bytes()),
                     "original_count": 38, "selected_count": 30,
                     "deferred": spec["deferred"], "authority": spec["authority"]}
(OUT / "receipts.json").write_bytes(json.dumps(data, indent=2).encode())
module.burst(int(sys.argv[1]))
