# --output json on every exit path (real CLI)

| path | rc | provider calls | stdout is exactly one JSON doc | status | exit_code key in doc |
|---|---|---|---|---|---|
| 0 success | 0 | 2 | True | ok | absent |
| 0 dry-run | 0 | 0 | True | None | absent |
| 0 dry-run with redact | 0 | 0 | True | None | absent |
| 1 unknown project | 1 | 0 | True | usage_error | 1 |
| 1 unknown source | 1 | 0 | True | usage_error | 1 |
| 1 unknown provider | 1 | 0 | True | usage_error | 1 |
| 1 provider unavailable (gemini, keys stripped) | 1 | 0 | True | usage_error | 1 |
| 1 pointer file missing | 1 | 0 | True | usage_error | 1 |
| 1 pointer file is a directory | 1 | 0 | True | usage_error | 1 |
| 1 pointer file not utf-8 | 1 | 0 | True | usage_error | 1 |
| 1 bad --redact spec | 1 | 0 | True | usage_error | 1 |
| 1 --redact past the end | 1 | 0 | True | usage_error | 1 |
| 1 --redact approximate | 1 | 0 | True | usage_error | 1 |
| 1 --max-cost nan | 1 | 0 | True | usage_error | 1 |
| ? provider raises non-ProviderError (RuntimeError) | 1 | 1 | False | None | n/a |
| ? KeyboardInterrupt inside provider | 130 | 1 | False | None | n/a |
| 1 failed review (provider error on call 1) | 1 | 1 | True | failed | absent |
| 2 pointer errors | 2 | 0 | True | pointer_errors | 2 |
| 2 oversize pointer file | 2 | 0 | True | pointer_errors | 2 |
| 3 no approval for provider (mock) | 3 | 0 | True | refused | 3 |
| 4 zero-length source | 4 | 0 | True | unreadable | 4 |
| 4 audio-only source | 4 | 0 | True | unreadable | 4 |
| 4 source file missing | 4 | 0 | True | unreadable | 4 |
| click: missing source arg | 2 | 0 | False | None | n/a |
| click: --max-cost abc | 2 | 0 | False | None | n/a |
| click: unknown option | 2 | 0 | False | None | n/a |
| click: --output yaml | 1 | 0 | False | None | n/a |
| click: --output missing value | 2 | 0 | False | None | n/a |

Findings: rows with 'one JSON doc = False' in --output json mode: provider RuntimeError (traceback, rc 1), KeyboardInterrupt (rc 130), click usage errors (missing arg, --max-cost abc, unknown option, --output with no value: rc 2, empty stdout, same code as pointer_errors), `--output yaml` (rc 1, text only).
Docs without an exit_code key: success, dry-run, partial, failed review.
