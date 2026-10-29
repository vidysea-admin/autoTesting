"""mongo-store M12: the mutation spec for the write fence names real text and real tests.

Kept out of the suite the spec itself runs (`qa/` is not copied into the mutation sandbox), and
cheap: it does not run the mutants, `scripts/mutation_check.py` does. This only stops the spec from
drifting off the code it mutates.
"""

from __future__ import annotations

import json

from autotester.core.paths import code_root

SPEC = code_root() / "qa" / "evidence" / "mongo-store-u1" / "mutations.json"


def test_the_mutation_spec_targets_real_text_and_real_tests() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    tests = {name: (code_root() / name).read_text(encoding="utf-8") for name in spec["tests"]}
    assert len(spec["mutations"]) >= 7
    for mutation in spec["mutations"]:
        source = (code_root() / mutation["file"]).read_text(encoding="utf-8")
        source = source.replace(chr(13) + chr(10), chr(10))
        assert source.count(mutation["old"]) == 1, mutation["name"]
        assert mutation["new"] != mutation["old"]
        assert mutation["kills"], mutation["name"]
        for kill in mutation["kills"]:
            function = kill.split("[")[0]
            assert sum(f"def {function}(" in text for text in tests.values()) == 1, kill
