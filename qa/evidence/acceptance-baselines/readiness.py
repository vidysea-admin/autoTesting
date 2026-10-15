"""Validate exact provenance and complete selected guard receipts before reviewer dispatch."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
PROOFS = EVIDENCE / "risk-proofs"


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def load(name):
    return json.loads((PROOFS / name).read_bytes())


def main():
    identity, spec, commands, proofs = (load(name) for name in (
        "identity.json", "mutations.json", "commands.json", "proofs.json"))
    assert len(spec["mutations"]) == len(proofs) == 13
    assert len({proof["name"] for proof in proofs}) == 13
    assert sha((EVIDENCE / "probe-riskgroups.py").read_bytes()) == identity["harness_sha256"]
    assert sha((ROOT / "uv.lock").read_bytes()) == identity["lock_sha256"]
    for path, expected in identity["source_sha256"].items():
        original = (ROOT / path).read_bytes()
        assert sha(original) == expected
        assert subprocess.check_output(["git", "show", identity["code_sha"]+":"+path], cwd=ROOT) == original
    inventory = load("inventory.json")
    assert sha((PROOFS / "inventory.json").read_bytes()) == identity["inventory_sha256"]
    for name, expected in inventory.items():
        assert sha((ROOT / name).read_bytes()) == expected
    for command in commands:
        assert command["identity_sha256"] == sha((PROOFS / "identity.json").read_bytes())
        assert command["spec_sha256"] == sha((PROOFS / "mutations.json").read_bytes())
        log = PROOFS / command["log"]
        assert sha(log.read_bytes()) == command["output_sha256"]
        if command["report_sha256"] is not None:
            assert sha(log.with_suffix(".report.json").read_bytes()) == command["report_sha256"]
    stage = "src/autotester/stages/acceptance_baseline.py"
    original = (ROOT / stage).read_bytes()
    for mutation, proof in zip(spec["mutations"], proofs, strict=True):
        assert mutation["name"] == proof["name"]
        assert mutation["kills"] == proof["nodes"]
        old, new = mutation["old"].encode(), mutation["new"].encode()
        assert original.count(old) == proof["anchor_count"] == 1
        mutated = original.replace(old, new, 1)
        assert mutated != original
        assert proof["original_sha256"] == proof["restored_sha256"] == sha(original)
        assert proof["mutated_sha256"] == sha(mutated)
        assert [commands[index]["exit_code"] for index in proof["command_indexes"]] == [0, 1, 0]
        for offset, index in enumerate(proof["command_indexes"]):
            command = commands[index]
            expected = dict(identity["source_sha256"])
            expected[stage] = sha(mutated if offset == 1 else original)
            assert command["source_sha256"] == expected
            assert all(node in command["argv"] for node in proof["nodes"])
            report = json.loads((PROOFS / command["log"]).with_suffix(".report.json").read_bytes())
            assert set(proof["nodes"]) <= set(report) if offset == 1 else report == []
        assert set(proof["nodes"]) <= set(proof["failed"])
    for label in ("shared-green", "scoped-lint", "scoped-shape", "preflight-init"):
        selected = [command for command in commands if command["label"] == label]
        assert len(selected) == 1 and selected[0]["exit_code"] == 0
    assert "22 passed" in (PROOFS / "shared-green.log").read_text(encoding="utf-8")
    nodes = {node for proof in proofs for node in proof["nodes"]}
    assert len(nodes) == 22
    result = dict(status="READY_FOR_INDEPENDENT_REVIEW", code_sha=identity["code_sha"],
                  groups=13, selected_cases=22, source_files=len(inventory),
                  current_candidate_command_seconds=sum(c["duration_s"] for c in commands),
                  historical_init_command_seconds=sum(c["duration_s"] for c in json.loads(
                      (EVIDENCE / "initial-init/commands.json").read_bytes())),
                  prior_successful_init_command_seconds=sum(c["duration_s"] for c in json.loads(
                      (EVIDENCE / "commands.json").read_bytes())),
                  maker_active_seconds=None, tokens=None, monetary_cost=None,
                  note="Historical unbound shell attempts retained separately; no unit PASS claimed")
    (EVIDENCE / "readiness.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
