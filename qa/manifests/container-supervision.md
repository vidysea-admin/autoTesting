# Production container supervision: bounded source unit

**Status:** ready-for-check
**Fix cycle:** 2
**Root:** C:/Users/product/.codex/worktrees/container-supervision/autoTesting
**Base SHA:** 40299c04cc1c7e9cc247a14cd1a4da89d6f58377
**Source candidate SHA:** 326bf0a7ffa5296a81bcbe0bc5a112903bb68787 (unchanged).
**Review candidate SHA:** exact evidence-wrapper SHA is in `.work/container-supervision/packet-cycle2.json`.
**Risk:** high_risk (production runtime, secret-log and viewer boundaries).

## Scope and behavior

Dockerfile, docker/entrypoint.sh, docker/supervise.py, docker/DEPLOY.md and
tests/test_container_supervision.py only, plus this manifest and raw unit evidence.
The independent supervisor module belongs under docker/ because it manages only container
process lifecycle, uses stdlib only and defines no domain shape or application behavior.
No contract, enforcement, credential, queue/provider/schema or Windows task changes.
The human's build-essential dependency is preserved.

The container runs as UID/GID10001 with root-owned source and frozen /opt/venv;
home/cache, /data and temporary sockets are writable. Runtime uv synchronization and
bytecode writes are disabled. The administrator prepares private data volume ownership;
entrypoint never gains root or changes mounted ownership. The dev bind mount must likewise
permit writes by the runtime UID; Linux dev mount acceptance remains a Docker-host check.

The shell execs the supervisor. Display, two VNC servers, two websocket proxies and app
start in socket-readiness order. Any child exit (including zero), spawn failure or readiness
timeout fails the whole container. Signals drain children; process groups receive TERM then
KILL after two seconds; tracked exits and adopted orphans are reaped. Commands/environment
and OS exception text are excluded from supervisor diagnostics. Existing loopback-only raw
VNC, view-only listener and --no-access-log behavior remain in the actual entrypoint.

## Clauses and evidence

Cycle2 repairs provenance only, following independent cycle1 HOLD verdicts. Windows
`Path.write_text` translated LF to CRLF in the throwaway copy: converting candidate
supervisor bytes to CRLF yields exactly f038efbc2d7803f6e831a70715a3733e101a910a5771c7982e39b7a00ef03dd3;
entrypoint yields exactly 17d0bed7d27021d3a81ad900e5009aa4db8351e4fe599392573f67c634c9209a.
The rejected old receipts are retained byte-intact and are not retroactively certified.
Production/test bytes remain identical to326bf0a7; no logic or test change is made.

New `qa/evidence/container-supervision/cycle2/` uses byte-preserving edits/restores.
Its `self-audit.json` compares every primary before/after phase against exact candidate
source; a red phase permits only its declared mutation. It verifies interpreter,
dependency versions, lock, environment/temp parent, command, exit, log hash and named
failure attribution. Each mutation has green baseline and immediate exact restored-green.
All14 primary anchors match once. The historical four-return exit mutation remains as
supplemental evidence; the primary exit guard now uses one unique-context branch edit.
The source-identical cycle1 lint, Bash syntax and five unchanged consumer checks retain
their original receipts; incompatible cycle1 mutation/restored receipts are superseded.

core-invariants C2/C3/C5/C7/C9/C10/C11/C12; hosting HO2/HO3/HO5/HO6/HO7/HO10/HO12/HO38;
docker D1-D3/D6. D-093 leaves Windows boot/restart deferred; D-100 allows scoped review.
This is source-unit evidence only, never certification of live/build-host rows.

Raw logs and before/after fingerprints: `qa/evidence/container-supervision/cycle2/`.
Repeatable cycle2 proof/narrowing/self-audit harnesses are saved beside those receipts.
Primary guard-to-mutation definitions: `qa/evidence/container-supervision/cycle2/mutations.json`.
Every named introduced test/guard has an applied semantic mutation with named failure,
an asserted green baseline and restored-green receipt; no collection error counts as a kill.
15 focused tests passed, scoped ruff passed, Bash syntax passed; final isolated restored copy
has 10 new-test passes. The five unchanged consumer tests cover viewer separation, compose
hardening, secret scan, Playwright pin and LF entrypoint attributes.

Doctor exits1 only on pre-existing stale-generated docs/MAP.md and docs/SNAPSHOT.md.
Generator inputs src/, scripts/, architecture, decisions, ledger and goal are unchanged from
base. The diff is outside every input to render_map/render_snapshot; raw output is retained.
Do not regenerate these in this unit; the integration owner reconciles the combined candidate.

Initial setup retries: temp permission denial, missing parametrized test argument,
Windows AF_UNIX selection, incorrect mutation-anchor count, unsupported mocked platform
attributes, and unsupported `python -m autotester` doctor entrypoint were corrected. Early
baseline files were overwritten by the final baseline; those earlier outcomes are not reused
as proof. Final fingerprinted receipts remain complete. Maker active seconds/tokens/cost are
unknown; individual command durations are measured. Efficiency ratios remain unverified.

## Remaining gates

Fresh dual independent review of secret/exposure boundaries; reviewer helper assess/preflight
and representative mutation. Parent owns dispatch and persisted verdict; maker never PASSes.
Full pytest/ruff/doctor on exact combined integration candidate remains mandatory.
Docker/hadolint unavailable locally: Ubuntu image build/run, real Linux process groups,
15-second kill/restart/healthz recovery for each child, signal/reaping, writable-volume and
read-only-source proof, dev-compose behavior, viewer operation, reboot and exposure acceptance
remain explicitly unproven. No D1-D3, HO5, HO6 BUILD-HOST or live deployment PASS is claimed.
