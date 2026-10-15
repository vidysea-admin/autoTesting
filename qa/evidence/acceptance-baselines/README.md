# Isolated acceptance baseline preparation

This prepares local input artifacts only. It does not run acceptance, contact the product,
authenticate a real account, verify a remote build, copy credentials or grant consent.

`scripts/prepare_acceptance_baselines.py` accepts `--plan`, `--source-root`, `--input-root`
and a **new** `--destination`. Run it under the retained Python interpreter with this checkout's
`src` on `PYTHONPATH`. All input paths are relative to `--input-root`.

The explicit `BaselinePlan` JSON contains:

- `source_slug`: existing project's slug, used only to read `project.json`;
- `source_config_sha256`: SHA256 of those exact configuration bytes;
- `baseline_slug`: the new pair's slug prefix;
- `target_build`: the owner's immutable build identifier (recorded as declared/unverified);
- `credential_keys`: selected test-account **key names**, already declared and scoped in the project;
- `teaching_inputs`: approved redacted video and document files, each with `path`, byte `sha256`,
  `kind` (`video` or `doc`) and the owner's existing `approval_ref`.

The output has `baseline-plan.json`, `baseline-receipt.json`, and distinct `teaching/` and
`url_only/` roots. Project slugs are `<baseline_slug>-teaching` and `<baseline_slug>-url-only`.
Both preserve URL, domain scope, production/write policy and explicit provider settings.
Only teaching gets the declared, hash-checked input bytes and source provenance. Historical
truth, cases, proposals, crawls, runs, login-case pointers, schedules, tracker state, approvals
and `.env` files are excluded. A pre-existing or partial destination refuses; use a new path.

Later execution must explicitly bind an authorized existing credential environment without
duplicating keys. Each new project's production run still requires a covering human-signed
approval. Both modes must confirm the same actual target build before any serial live run.
The existing rich-input caller is a separate dependency; this preparation unit does not
certify rich teaching dispatch or T-169/T-206/T-136 completion.

Evidence: `probe.py` and the prior 20-case INIT/draft spec are preserved. The final
`probe-riskgroups.py` verifies the complete raw-byte `src`/`tests`/`scripts` inventory, binds its
immutable code/test SHA and environment, and runs coordinator-granted phases only under
`risk-proofs/`. `--init-only` runs preflight, all 22 focused cases, scoped lint and AST shape;
`--start N --count K` runs selected guard GREEN/RED/restored triplets. `risk-selection.md`
records the approved 13 behavioral groups and omitted redundant draft mutants. Prior receipts
are never overwritten by a repeated completed guard. An unexpected write failure leaves a
visible incomplete destination with no receipt; retry refuses. Automatic cleanup is not provided.
