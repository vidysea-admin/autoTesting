"""Cheap readiness validation of authenticated PDF proof bytes before reviewer dispatch."""

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

OUT = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def tree_hash(manifest):
    return sha(json.dumps(manifest, sort_keys=True).encode())


def check_receipt(name, expected_tree, exit_code):
    receipt = load(name)
    assert receipt["before_tree_sha256"] == expected_tree
    assert receipt["after_tree_sha256"] == expected_tree
    assert receipt["exit_code"] == exit_code
    assert receipt["output_sha256"] == sha((OUT / receipt["output"]).read_bytes())
    assert receipt["command"][0] == sys.executable
    assert receipt["elapsed_s"] > 0
    return receipt


context = load("context.json")
manifest = context["source_manifest"]
assert all(sha((ROOT / path).read_bytes()) == checksum for path, checksum in manifest.items())
assert tree_hash(manifest) == context["source_tree_sha256"]
assert sha(Path(sys.executable).read_bytes()) == context["python_sha256"]
assert all(importlib.metadata.version(name) == version
           for name, version in context["dependencies"].items())
assert all(sha(Path(tool["path"]).read_bytes()) == tool["sha256"]
           for tool in context["tools"].values())
results = load("results.json")
assert len(results) == 21
elapsed = 0.0
for name in ("00-green.receipt.json", "99-restored-green.receipt.json"):
    elapsed += check_receipt(name, tree_hash(manifest), 0)["elapsed_s"]
for row in results:
    assert row["killed"] and row["exit"] == 1 and row["anchor_matches"] == 1
    assert set(row["expected"]) <= set(row["actual_failed"])
    assert row["before_sha256"] == row["restored_sha256"] == manifest[row["file"]]
    original = (ROOT / row["file"]).read_bytes()
    assert original.decode("utf-8").count(row["old"]) == 1
    altered = original.decode("utf-8").replace(row["old"], row["new"], 1).encode("utf-8")
    assert altered != original and sha(altered) == row["mutated_sha256"]
    mutated = {**manifest, row["file"]: sha(altered)}
    receipt = check_receipt(row["command_receipt"], tree_hash(mutated), 1)
    assert set(row["expected"]) <= set(receipt["failed_nodeids"])
    assert row["restored_tree_sha256"] == tree_hash(manifest)
    elapsed += receipt["elapsed_s"]
completion = load("completion.json")
assert completion["all_killed"] and completion["bound_worktree_unchanged"]
assert completion["restored_tree_sha256"] == tree_hash(manifest)
result = {"status": "READY_FOR_INDEPENDENT_CHECK", "proofs": 21,
          "feature_candidate": context["feature_candidate"], "cycle": 2,
          "source_tree_sha256": tree_hash(manifest), "measured_command_elapsed_s": elapsed,
          "maker_active_s": None, "tokens": None, "cost": None}
(OUT / "readiness.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
sealed = {path.name: sha(path.read_bytes()) for path in sorted(OUT.iterdir())
          if path.is_file() and path.name != "seal.json"}
(OUT / "seal.json").write_text(json.dumps(sealed, indent=2), encoding="utf-8")
print(json.dumps(result))
