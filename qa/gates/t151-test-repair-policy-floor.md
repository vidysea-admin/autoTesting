# T151 existing-test strengthening versus policy floor

Recorded: 2026-10-05. Status: unanswered.

Question: Under policy2026-10-05.2's maker-read-only test floor, does Umesh explicitly authorize the narrowly reviewed strengthening of existing tests/test_discover.py::test_model_reason_is_redacted_and_scanner_evidence_is_preserved?

Scope: replace the existing direct classification assignment with a ValueError-only capture and an explicit result-receipt assertion; preserve all original assertions and 63 cases. Reclaim five empty lines to keep 300 lines. Reviewed preview SHA256 4C302C698346F90F492C520B37D8B7C49E764B9F331D2E696E9CEF42CE033D8E. Independent post-edit verification remains mandatory.

Answer format: `T151 exact test strengthening: approve` or `T151 test floor: retain`.

Blocks: this exact test edit and its dependent persistent-test proof only. Does not waive native-junction, full-suite/browser, model-spend, credential or release gates. Does not authorize changing the policy or weakening tests. The code remains unapplied.

Evidence: current canonical policy floor says tests/graders/validators are read-only to maker. The plan was independently approved under prior policy.1, and its approval is not treated as overriding the new floor.

Answered: 2026-10-05 — Umesh explicitly approved exact test strengthening after
the scope explanation. Only the named existing test/ValueError-only capture/
result-receipt assertion and five-empty-line capacity recovery are authorized;
preserve all original assertions and63cases. Reconcile reviewed candidate/hash
before apply and independently verify afterward. No policy change, browser/
full-suite bypass, paid model, credential or release approval follows.
Current status: answered — exact test strengthening approved.
