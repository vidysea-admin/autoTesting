# ARCHITECTURE.md proposal (mongo-store U10) - sections the maker did NOT edit

Lab Protocol: `docs/ARCHITECTURE.md` prose changes only where a DECISIONS entry's `Changes-authorized` names the section.

## What U10 edited, and the authority

- **Security (item 1) and Storage** - D-120 `Changes-authorized` ("ARCHITECTURE.md prose (storage and security model sections) may change under this entry once the contract has passed", `docs/DECISIONS.md:2939`) and D-122 ("Later, under the docs unit, CLAUDE.md Credentials and ARCHITECTURE.md storage and security prose", `:2986`). Caveat for the checker: D-120 says "once the contract has passed"; at pickup U8 (migrate, dual) is still open, so I relied on D-122's narrower text (docs unit after the credential/session units U11/U12 pass, both merged with fixes U11f/U12f). If you read that as not yet satisfied, revert those two hunks; `git revert` of the code commit does it.
- Net 149 lines (cap 150, `ledger/render.py:22`).

## What U10 did not edit (no entry names these sections) - proposed text

1. **Pipeline, line 20**: `... per-stage RunState checkpoints over the filestore artifacts, no new DB (D-036):`
   M48 names this phrase as a falsifier ("no new DB (D-036)"). The Pipeline section is not named by D-120 or D-122. Proposed:
   `... per-stage RunState checkpoints over the state-store artifacts (files by default, MongoDB per area, D-120; D-036's "no new DB" means the orchestrator adds no store of its own):`
   Needs a DECISIONS entry whose `Changes-authorized` names "Pipeline" (Umesh), or a supersede of D-036's wording.
2. **Concept -> file, "Persistence" row (line 42)**: `Persistence: atomic JSON/JSONL primitives + the per-project artifact facade | store/filestore.py, store/project_store.py::ProjectStore`. Proposed (one row, same length class):
   `Persistence: backend seam (file default, MongoDB per area), atomic primitives, per-project facade | store/filestore.py, store/mongo_routes.py, store/mongo_guard.py (the only door), store/project_store.py::ProjectStore`
   The file is at 149/150 lines, so any added row must be paid for by folding another row; the generated `docs/MAP.md` already lists every `store/` and `auth/` module.
3. **Concept -> file, "Docker" row**: says "(local dev only)", which is no longer true (Cloud Run deploy, D-125). Proposed: drop the parenthesis and add `docker/DEPLOY.md`.

Each of 1-3 needs the same kind of authorizing entry. Nothing here touches a contract.
