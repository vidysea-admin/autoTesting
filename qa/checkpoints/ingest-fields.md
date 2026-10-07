# Checkpoint -- ingest-fields (cycle 0, single checker)

Env: win32, worktree .venv python, HEAD a902bc8d, uv.lock 931b7600ba1a

| check | command + scope | code hashes | result | attribution |
|---|---|---|---|---|
| affected tests | pytest tests/test_ingest.py tests/test_ingest_persist.py tests/test_ingest_real_cli.py (39 collected) | ingest.py 683c9bd7552f, test_ingest.py 3b35cc6881e6 | 39 passed | checker ingest-fields c0 |
| lint | ruff check src tests scripts | same | All checks passed | same |
| doctor (HEAD) | autotester doctor | same | 2 violations (docs/MAP.md, docs/SNAPSHOT.md stale) | same |
| doctor (base fe6eb98a, git archive copy) | autotester doctor | base tree | same 2 violations | same |
| falsification C1 | copy of HEAD, `fields=observed.fields` restored, node test_ingest_video_wraps_observed_field_labels_as_inputfields | same | green 1 passed / red 1 failed (InputField model_type error) | same |
| diff scope 4c | git diff fe6eb98a --name-only | same | 3 files, all listed in What changed | same |
