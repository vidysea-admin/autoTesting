# Verdict — diagnose-redaction-hardening

Verdict: FAIL
Status: FAIL
Cycle checked: 1
Reviewed SHA: ba5735e73525dd27019acbf14addea4312c93b71
Base SHA: 3f081243030be35f856a57286ffa0efc5602d6d7
Prior verdict: FAIL cycle 0 at 4bdb3437 (verdict commit edca4583)
Checker: independent, fresh context (Opus 5.5), 2026-10-16
Final hashes (sha256): scripts/container_diagnose.sh 9d430e6d41ce0ce7c70f704f8e6c2846cc3ab01975ec88a355914740b2a426e9; src/autotester/core/redact_cli.py 7889d0cdf3a233bc1ab7abd0b2e1055bab1943fb70bff3d5e1bc82c1de361efb; tests/test_container_redaction.py e34c055e7a9a87814b1794b8a77f257ed2ae6afcba7c99cd90b3532c2279bd2a; tests/test_container_ci_workflow.py a7d4885d3ebf0146b828b48beff8fab2bfafdb8fe28e6e8c7ca3634ec2f56a76

## Why FAIL (proven, one narrow blocker)
Manifest layer 1 says: "real secret values from the repo-root `.env` ... and `--secrets-file` ... Every exact occurrence is masked under any key name." The repo reads `.env` with `python-dotenv` (`core/env.py::load_repo_env` -> `dotenv_values`), but `_redact_assignments` parses it in awk with different rules. For three valid dotenv forms the value the app actually uses is never put in the value file, so it leaks wherever it is not next to a secret-looking name.
Probe: `.work/checker-diagnose-redaction-hardening/c1/dotenv_shapes.sh`, output `dotenv_shapes.out`.
- `ZA=Inl1neSecret # test account`: dotenv gives `Inl1neSecret`, the script loads `Inl1neSecret # test account`. `a Inl1neSecret b` LEAKS.
- `ZB = Sp4cedSecret` (spaces around `=`): the whole line is loaded as the value. LEAKS.
- `ZC="Qu0teSecret" # c`: the script loads `Qu0teSecret" # c`. LEAKS.
- `ZD='Sq1Secret'` and `export ZE=...` are masked.
Real-world exposure today: none. A counts-only parity check (`parity.py` / `parity.out`, no values printed) on the real repo-root `.env` gives dotenv_values=17 and missing=1, a 3-digit number that the numeric skip rule drops by design. So this is a latent leak, triggered as soon as someone adds an inline comment. It is still a contract mismatch on the boundary.
Narrow repair:
- Build the `.env` candidates with the same parser the repo uses (dotenv / core.env, when python imports), or have the awk path also emit the comment-stripped, trimmed and unquoted form. Masking both forms is safe.
- Add tests for the three shapes above.

## Verified OK (independent)
- All 72 cycle-0 probe shapes are masked by the name layer alone, with no value file: 72 ok, 0 LEAK (`c1/probe72_namelayer.out`). The tricky outputs were inspected; escaped-quote JSON is now masked to the closing quote.
- Fresh shapes through the value layer, python and no-python (`c1/fresh_probe.sh`, `fresh_py.out`, `fresh_nopy.out`):
  - masked: a value under a bizarre key or in free text, every occurrence; a value in a URL path segment, in a query string and in JSON; the 6- and 7-char boundary values; a value full of regex metacharacters (`a.b*c[d]~e/f\g&h#1`); a value starting with `-`; a multi-word quoted value
  - masked with python only, as designed: the `%58` and `&#88;` encodings
- Expected or accepted residuals (advisory, not blocking):
  - line-wrapped halves leak (inherent to line-based masking)
  - base64 of a secret is not masked: `Redactor.scrub` masks only exact, percent, entity and plus forms; `contains_folded` only detects
  - 5-char values are skipped. This diverges from Redactor's no-minimum policy (AT-002); the floor is a brief-sanctioned over-redaction trade-off.
  - values skipped by design: numeric (e.g. an 8-digit PIN), values starting with `/`, and any value containing `localhost`. They are masked only when the name or URL-userinfo layer sees them.
- Value secrecy:
  - Values reach the filters only through stdin and files: sed via `-f "$vf.sed"`, python via a path in argv, never a value in argv.
  - The temp dir is `mktemp -d` plus `chmod 700` and is removed by the EXIT trap. The trap was verified to run on TERM and INT.
  - Advisory: the files inside follow the umask (not 0600 themselves); the 0700 dir is the protection.
- redact_cli.py: 38 lines with a one-job docstring. It reuses `core.redact.Redactor.scrub` with no duplicate masking logic and works stdin to stdout. When python fails the pipe yields empty output, never raw text, though without a notice (advisory).
- Fail-safe: fake non-GNU sed on PATH (`c1/fakebin/sed`, passthrough that rejects `--version`). Probes `failsafe_nopy.out` and `failsafe_py.out` (python present). Both keep only the header, READINESS, PermissionError, RESULT, [FAIL] and uid lines, plus `[5 line(s) withheld ...]`; every secret line is withheld.
- Over-redaction:
  - `test_diagnosis_signatures_survive_redaction` passes.
  - Image Env values `noninteractive`, `only-managed` and `manual` will be masked as words (benign).
  - `8000`, `true` and paths stay readable.
- Advisory: `scripts/container_diagnose.sh` is 356 lines, over the 300-line design rule. doctor does not scan .sh, so it is not a doctor failure.
- Advisory: each `redact` call spawns python. On this saturated CPU that took about 20 s per call.

## Commands (independent, exit codes captured under .work/checker-diagnose-redaction-hardening/c1/)
- preflight `review_budget.py preflight`, venv python 3.11.16, import root = worktree src: PREFLIGHT_OK (`preflight.out`)
- `python -m pytest tests/test_container_redaction.py tests/test_container_ci_workflow.py` (PYTHONPATH=worktree/src): 89 passed, rc=0 (`pytest.out`, `pytest.rc`)
- `bash -n scripts/container_diagnose.sh`: rc=0; `ruff check src tests scripts`: All checks passed, rc=0
- `python -c "from autotester.cli import app; app()" doctor`: doctor: clean, rc=0 (advisories only)
- No maker evidence reused; all results produced here.

## Metrics
- Maker (brief, unverified): ~116k tokens, >=3,400 s across both cycles.
- Checker c1: ~600 s wall (launch to verdict, includes background waits). Target was <=500 s: OVERRUN of about 100 s, recorded and not waived. Runtime tokens unknown (null). Budget inputs and results: `c1/phase1b-input.json`, `c1/phase1b-result.json` (BOOTSTRAP_REVIEW, ratio unverified).

## Remaining gates
After the fix: re-check of the dotenv-parity repair, plus the full suite post-merge. A real docker run and Cloud Run log shapes are still unverified.
