# Cycle 2 proof authentication

Feature bytes remain exactly c1f67d93. The missing 21 proof receipts were reproduced in one
complete source/test/script fixture copy. Context was persisted before the first probe;
each raw output has a command receipt, source hashes before/after and real command duration.
The context environment records the driver environment; the inspected, fingerprinted repository
`_run_pytest` prepends the sandbox parent to PYTHONPATH solely for its report plugin. The
effective pytest import search is that sandbox parent plus sandbox `src`; preflight independently
confirmed the source import origin before probes. Temporary paths can be absent after cleanup.

The mutation input/old-new strings remain historical in the cycle-1 spec. New result rows verify
exactly one anchor, changed bytes, named assertion failures, byte restoration and full tree
restoration. Green union: 12 missing defender tests, then 21 named red runs, then the same
restored-green 12. The prior checker independently proved the excluded sanitation mutation.

Run `validate_receipts.py` with the existing main-checkout Python to recheck code, binary, tool,
dependency, raw-output, mutation and restoration fingerprints. `readiness.json` records its
result; `seal.json` binds every supplementary artifact except itself. Source/test/config files
were not edited. No broader suite, browser, model request or key access occurred in cycle 2.
