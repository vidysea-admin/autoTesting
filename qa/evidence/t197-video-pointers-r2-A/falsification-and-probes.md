# t197-video-pointers r2 checker A: falsifications and probes (b59dda0d, product 28035c82)

Copy: git archive b59dda0d on C: (session scratchpad t197r2a/copy), venv there, `git init` added only so
the `check-ignore` tests can run (an archive has no .git; without it 8 cleanup tests fail for that reason alone).
`autotester.__file__` printed inside the copy. Probe file: `probe_r2a.py` (this directory).

## Falsification rows (one per repaired item; each its own copy, PYTHONPATH at the copy, anchor unique)

| Row | Edit | Green before | Red after (first failing assertion) |
|---|---|---|---|
| F2a usage errors | `app.command("review", cls=ReviewCommand)` -> `app.command("review")` (cli_video.py) | 13 passed | 8 failed, `assert 2 == 1` (exit code) |
| F2b unexpected exception | `except Exception as exc:` -> `except ZeroDivisionError as exc:` | 2 passed | 2 failed, JSONDecodeError in `_doc` (no document) |
| F2c Ctrl-C | `except KeyboardInterrupt:` -> `except ZeroDivisionError:` | 1 passed | 1 failed, JSONDecodeError (no document) |
| F2d exit_code on review doc | `"exit_code": code` removed from `_finish` | 5 passed | 4 failed, `KeyError: 'exit_code'` |
| F3 32769 boundary | `size > MAX_POINTER_FILE_BYTES` -> `... + 1` (video_pointers.py:98) | 1 passed | 1 failed, `assert 0 == 1` (no error for 32769 bytes) |
| internal_error redaction | `Redactor(...).scrub(str(exc))` -> `str(exc)` | 2 passed | 2 failed, canary `hunter2-canary-xyz` in stdout and stderr |

## Probe results (in-process CliRunner, fake provider, 22 probes)

- Every argv shape in the json family gave exit 1 and, when `--output json`/`--output=json` was in argv, exactly one document
  `{"status":"usage_error","reason","exit_code":1}`: `--bogus`, `--max-cost abc`, `--max-cost --output json` (cap swallows the flag),
  `--output json --output` (bare after json), extra positional, missing arguments, NaN/inf/negative cap. Provider calls: 0.
- Text-only outcomes (stdout empty, stderr note, exit 1, never 2): `--output JSON`, `--output xml`, `-o json` (no `-o` exists), `--out json`
  (no prefix matching), bare `--output` with no earlier json. `--help` exits 0.
- Detection is "any `--output json` pair / `--output=json` anywhere in argv", not click's last-wins and not `--`-aware:
  `--output json --output text --bogus` and `--bogus -- --output json` both emit a json document while click's effective format is text
  (harmless over-emit, low).
- internal_error: a RuntimeError/OSError message with the recording path as `str(path)`, posix form, or bare name is masked to `<recording>`.
  Leaks: (a) a genuine `FileNotFoundError` carries the path as `repr` (doubled backslashes); the directory part is not masked, only the name
  (`'C:\\Users\\Lenovo\\...\\cliv0\\rec.nope'`); (b) an upper-cased path/name is not masked (case-sensitive replace on Windows).
  No secret leak (Redactor), no traceback, scratch removed (`rv_*` rglob empty), last-resort path (secret loading itself raising) drops the message.
- `KeyboardInterrupt` in `--dry-run` preview: exit 130, one `interrupted` document. `SystemExit(7)` from a provider is not caught: exit 7,
  empty stdout, scratch still removed (low).
