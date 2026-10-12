| case | exit | stdout docs | status | doc exit_code | = real exit | stderr (last line) | calls | left under reviews/ |
|---|---|---|---|---|---|---|---|---|
| ok-json | 0 | 1 | ok | 0 | True | reviewing src_a94a8334f929 with fake (cap $0.5) | 1 | reviews/rv_cc908f4e6c15.json |
| ok-text | 0 | 0 | NO-DOC | NO-DOC | n/a (text) | reviewing src_a94a8334f929 with fake (cap $0.5) | 1 | reviews/rv_cc908f4e6c15.json |
| dryrun-json | 0 | 1 | - | 0 | True |  | 0 | empty |
| dryrun-text | 0 | 0 | NO-DOC | NO-DOC | n/a (text) |  | 0 | empty |
| partial-cap-json | 0 | 1 | ok | 0 | True | reviewing src_a94a8334f929 with fake (cap $1e-09) | 1 | reviews/rv_cc908f4e6c15.json |
| failed-cap0-json | 1 | 1 | failed | 1 | True | reviewing src_a94a8334f929 with fake (cap $0) | 0 | reviews/rv_cc908f4e6c15.json |
| pointer-errors-json | 2 | 1 | pointer_errors | 2 | True |   line 2: reversed or empty range: end 750s is not after start 840s | 0 | empty |
| pointer-errors-text | 2 | 0 | NO-DOC | NO-DOC | n/a (text) |   line 2: reversed or empty range: end 750s is not after start 840s | 0 | empty |
| pointer-oversize-json | 2 | 1 | pointer_errors | 2 | True |   line 1: pointer file is 33008 bytes, over the 32768 byte limit | 0 | empty |
| refused-no-approval-json | 3 | 1 | refused | 3 | True |   uv run autotester approve demo --kind video_review --target "fake" - | 0 | empty |
| refused-no-approval-text | 3 | 0 | NO-DOC | NO-DOC | n/a (text) |   uv run autotester approve demo --kind video_review --target "fake" - | 0 | empty |
| unreadable-json | 4 | 1 | unreadable | 4 | True | src_1ed5a3d24b70: recording is corrupt or has no video track | 0 | empty |
| unreadable-text | 4 | 0 | NO-DOC | NO-DOC | n/a (text) | src_1ed5a3d24b70: recording is corrupt or has no video track | 0 | empty |
| unknown-source-json | 1 | 1 | usage_error | 1 | True | demo has no recording src_nope — try `autotester ingest list`. | 0 | empty |
| unknown-project-json | 1 | 1 | usage_error | 1 | True | no project 'ghost' yet | 0 | empty |
| provider-unavailable-json | 1 | 1 | usage_error | 1 | True | provider 'gemini' is not available here (no credentials or binary) | 0 | empty |
| missing-pointer-file-json | 1 | 1 | usage_error | 1 | True | cannot read the pointer file (FileNotFoundError) | 0 | empty |
| nan-cap-json | 1 | 1 | usage_error | 1 | True | --max-cost must be a finite number of dollars, 0 or more | 0 | empty |
| inf-cap-json | 1 | 1 | usage_error | 1 | True | --max-cost must be a finite number of dollars, 0 or more | 0 | empty |
| neg-cap-json | 1 | 1 | usage_error | 1 | True | --max-cost must be a finite number of dollars, 0 or more | 0 | empty |
| u-cap-abc-spaced-after | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': 'abc' is not a valid float. | 0 | empty |
| u-cap-abc-spaced-before | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': 'abc' is not a valid float. | 0 | empty |
| u-cap-abc-equals-after | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': 'abc' is not a valid float. | 0 | empty |
| u-cap-abc-equals-before | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': 'abc' is not a valid float. | 0 | empty |
| u-cap-abc-text | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | Error: Invalid value for '--max-cost': 'abc' is not a valid float. | 0 | empty |
| u-cap-empty-spaced-after | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '' is not a valid float. | 0 | empty |
| u-cap-empty-spaced-before | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '' is not a valid float. | 0 | empty |
| u-cap-empty-equals-after | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '' is not a valid float. | 0 | empty |
| u-cap-empty-equals-before | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '' is not a valid float. | 0 | empty |
| u-cap-empty-text | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | Error: Invalid value for '--max-cost': '' is not a valid float. | 0 | empty |
| u-cap-0x10-spaced-after | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '0x10' is not a valid float. | 0 | empty |
| u-cap-0x10-spaced-before | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '0x10' is not a valid float. | 0 | empty |
| u-cap-0x10-equals-after | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '0x10' is not a valid float. | 0 | empty |
| u-cap-0x10-equals-before | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '0x10' is not a valid float. | 0 | empty |
| u-cap-0x10-text | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | Error: Invalid value for '--max-cost': '0x10' is not a valid float. | 0 | empty |
| u-unknown-opt-spaced-after | 1 | 1 | usage_error | 1 | True | Error: No such option: --bogus | 0 | empty |
| u-unknown-opt-spaced-before | 1 | 1 | usage_error | 1 | True | Error: No such option: --bogus | 0 | empty |
| u-unknown-opt-equals-after | 1 | 1 | usage_error | 1 | True | Error: No such option: --bogus | 0 | empty |
| u-unknown-opt-equals-before | 1 | 1 | usage_error | 1 | True | Error: No such option: --bogus | 0 | empty |
| u-unknown-opt-text | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | Error: No such option: --bogus | 0 | empty |
| u-output-novalue-spaced-after | 1 | 1 | usage_error | 1 | True | Error: Option '--output' requires an argument. | 0 | empty |
| u-output-novalue-spaced-before | 1 | 1 | usage_error | 1 | True | Error: Option '--output' requires an argument. | 0 | empty |
| u-output-novalue-equals-after | 1 | 1 | usage_error | 1 | True | Error: Option '--output' requires an argument. | 0 | empty |
| u-output-novalue-equals-before | 1 | 1 | usage_error | 1 | True | Error: Missing argument 'source_id'. | 0 | empty |
| u-output-novalue-text | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | Error: Option '--output' requires an argument. | 0 | empty |
| u-missing-arg-json | 1 | 1 | usage_error | 1 | True | Error: Missing argument 'source_id'. | 0 | empty |
| u-missing-arg-equals | 1 | 1 | usage_error | 1 | True | Error: Missing argument 'source_id'. | 0 | empty |
| u-missing-arg-text | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | Error: Missing argument 'source_id'. | 0 | empty |
| u-no-args-json | 1 | 1 | usage_error | 1 | True | Error: Missing argument 'project'. | 0 | empty |
| u-output-xml | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | --output must be text or json | 0 | empty |
| u-output-JSON-upper | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | --output must be text or json | 0 | empty |
| u-bare-output-only | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | Error: Option '--output' requires an argument. | 0 | empty |
| u-cap-eats-output-flag | 1 | 1 | usage_error | 1 | True | Error: Invalid value for '--max-cost': '--output' is not a valid float | 0 | empty |
| u-pointers-eats-output-flag | 1 | 1 | usage_error | 1 | True | Error: Got unexpected extra argument(s) (json) | 0 | empty |
| u-extra-positional-json | 1 | 1 | usage_error | 1 | True | Error: Got unexpected extra argument(s) (extra) | 0 | empty |
| u-redact-malformed-json | 1 | 1 | usage_error | 1 | True | --redact takes START-END windows inside the recording, like 12:30-14:0 | 0 | empty |
| u-help-json | 0 | 0 | NO-DOC | NO-DOC | n/a (text) |  | 0 | empty |
| provider-runtime-json | 1 | 1 | internal_error | 1 | True | unexpected RuntimeError during the review: [REDACTED]:DEMO_PASSWORD at | 1 | empty |
| provider-oserror-json | 1 | 1 | internal_error | 1 | True | unexpected OSError during the review: [REDACTED]:DEMO_PASSWORD at <rec | 1 | empty |
| provider-runtime-text | 1 | 0 | NO-DOC | NO-DOC | n/a (text) | unexpected RuntimeError during the review: [REDACTED]:DEMO_PASSWORD at | 1 | empty |
| provider-runtime-redact-json | 1 | 1 | internal_error | 1 | True | unexpected RuntimeError during the review: [REDACTED]:DEMO_PASSWORD at | 1 | empty |
| sig-ctrlC-json | 130 | 1 | interrupted | 130 | True | interrupted; nothing stored | 1 | empty |
| sig-ctrlC-text | 130 | 0 | NO-DOC | NO-DOC | n/a (text) | interrupted; nothing stored | 1 | empty |
| sig-ctrlBREAK-json | 3221225786 | 0 | NO-DOC | NO-DOC | n/a (text) | reviewing src_a94a8334f929 with fake (cap $0.5) | 1 | 9 scratch files + dir |
| sig-ctrlBREAK-text | 3221225786 | 0 | NO-DOC | NO-DOC | n/a (text) | reviewing src_a94a8334f929 with fake (cap $0.5) | 1 | 9 scratch files + dir |
| x-partial-multibatch | 0 | 1 | partial | 0 | True | reviewing src_a94a8334f929 with fake (cap $1e-09) | 1 | reviews/rv_354df1b04a35.json |
| x-ok-multibatch | 0 | 1 | ok | 0 | True | reviewing src_a94a8334f929 with fake (cap $0.5) | 2 | reviews/rv_354df1b04a35.json |
