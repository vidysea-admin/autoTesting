# Checkpoint — t154-adversarial-pass, coordinator A (dual check)

Checked HEAD 575a7c3f9f6b9dea45fd9464eeed8a3c2bd268ed (product fd7362a8, base ff901f72 = T-153 product commit, unmerged). Policy-Version: proportional-verification/2026-10-10.9. Tier L. Fix cycle 0. Resume 0 of 2. Retry 0.
Environment: Windows, worktree D:/autoTesting/.worktrees/t154-adversarial-pass, its own .venv; lane code cap=0 (binding=ram), so one pytest process at a time; free RAM 1.5-4.4 GB at runs.
Code hashes (blobs per manifest, matched on disk): tests/test_adversarial.py 20490ed, src/autotester/stages/adversarial.py 2d286b7; `git status --porcelain` empty in the worktree.

## Completed checks (evidence identity: command + scope + result)
| Check | Command / scope | Result |
|---|---|---|
| Affected tests, all criteria | `uv run pytest tests/test_adversarial.py` (25 collected) in the worktree | 25 passed |
| done_check (run directly, no allowlist entry) | `uv run python scripts/adversarial_proof.py` | exit 0; 10 lines HELD (1 in-scope pass sends 4; 9 refusals send 0 and log 1 row); "ADVERSARIAL PROOF OK" |
| AD4 grep | `grep -rniE "garak\|pyrit\|deepteam" src/ pyproject.toml` | no output, exit 1 |
| Lint | `uv run ruff check src tests scripts` | All checks passed |
| Doctor | `uv run autotester doctor` | 1 violation: stale-generated docs/SNAPSHOT.md (known, from master); no duplicate-concept, size or drift violation |
| 4c diff scope | `git diff ff901f72..575a7c3f --name-status` | 12 files, all added or modified, none deleted or renamed; every file named in the manifest; no T-153 file, no consent.py, no adapter, no contract touched; MAP.md diff has no removed line |
| Falsification AD1..AD7 | own throwaway copies under scratchpad/check-t154-a/AD*, PYTHONPATH on the copy, anchor asserted unique, bytes asserted changed, green before, red after | AD1 7p->7f; AD2 6p->2f; AD3 2p->1f; AD4 2p->1f; AD5 1p->1f; AD6 1p->1f; AD7 1p->1f (see verdict) |
| Live-path grep | no endpoint URL, HTTP client, socket, subprocess, CLI, pathlynks/vidysea string in adversarial.py, ai_probe.py, probe files, proof script | none |

## Remaining
- ONE checker full suite (L via the security trigger). Started `shard_suite.py --repo ... --ref 575a7c3f --shards 1 -- -o addopts=` at 2026-10-11T01:44:39; the machine-wide suite lock was held by other checkers (t167, then land-integrate-combined). Result recorded in the verdict; if it says CONTINUE-NEEDED, this is the only item left and everything above is reusable by evidence identity.
