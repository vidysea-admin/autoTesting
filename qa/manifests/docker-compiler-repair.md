# Manifest — docker-compiler-repair

**Status:** checked-PASS
**Fix cycle:** 1
**Branch:** codex/docker-compiler-repair
**Unit:** Restore Dockerfile RUN continuations while preserving the concurrent human compiler addition.
**Local baseline:** abc4a0ef49406936dd0047b7986b449bf3771ee2
**Remote input:** 81c84bac9f7f48280b190cf5cfdc1d96479e542a
**Merged baseline:** c76cfd115a771b30aea728a2b1ead52d20926eab

## What changed

- Dockerfile: exactly three trailing backslashes restored in the apt-install RUN. Retains build-essential, existing runtime packages and apt-list cleanup.
- qa/manifests/docker-compiler-repair.md: this handshake.
- The remote human commit is an ancestor, preserved through a real merge. No force, reset, cherry-pick, dependency or application change.

## Evidence and acceptance

- Both baseline and repaired structural probes exit 0 using the existing root .venv Python. Probe path: .work/docker-repair-evidence/probe.py in this worktree.
- Probe establishes synthetic repaired GREEN first; unchanged remote then fails the named logical-instruction assertion with `unknown instruction: build-essential`. Repaired checkout is byte-identical to remote plus exactly three backslashes, then GREEN.
- Probe verifies one logical apt RUN, compiler and all six runtime packages, and cleanup in the same RUN. This is a narrow independent-reproducible structural check, NOT the official Docker parser or an image build.
- `git diff --check`: exit 0, no diagnostics. No new runtime guard or test added; no pytest needed for shell continuation-only source change.
- Docker and Hadolint executables unavailable. Real image build/runtime remains deferred to Docker-capable deployment acceptance; this unit must not certify D1-D3 or Ubuntu deployment.
- No browser, model, network inference, image build or full suite executed. Existing worktree environments reused.

## Reviewer packet

Review immutable branch candidate against merged baseline c76cfd11. Check Dockerfile diff exactly restores the three continuations; both abc4a0ef and remote81c84bac must be ancestors. Independently rerun the discriminating structural probe or equivalent; inspect shell command shape and compiler preservation. Persist matching cycle-1 verdict at qa/verdicts/docker-compiler-repair.md. No integration/push authorized within this maker unit.

## Measured limits

Observed probe-phase timestamps: 2026-10-15T07:44:13.7439154Z through 07:44:23.0204101Z; these are observations, not total maker active time. Maker total active seconds, host tokens and cost unavailable/null. Fresh checker uses finite bootstrap allocation; efficiency ratio unverified. Root master and existing untracked product evidence were not changed by this repair branch.
