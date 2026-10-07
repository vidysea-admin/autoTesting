# d:/autoTesting — AutoTester

An AI system that does the automated-tester job end to end: ingest a product's videos and docs,
derive a reviewed FlowSpec, generate best/worst/edge-case evals, run them as regression in a real
visible browser, and ask for new videos when it meets a screen it does not know.

**North star:** an expert human tester and AutoTester get the same material and the same build;
AutoTester wins on bugs found, false-positive rate, and time.

## Read first, always

1. **`docs/ARCHITECTURE.md`** — the concept→file map. Read before touching any code.
2. **`src/autotester/schema/`** — every data shape in the system. Nothing else defines one.
3. **`qa/contracts/core-invariants.md`** — the rules every unit is judged against.
4. `.goal/goal.json` — the task backlog; `.goal/dashboard.html` for the view.

Plan of record: `C:/Users/Lenovo/.claude/plans/great-when-you-really-iridescent-ocean.md`.

## Where to look (router — every `docs/` file, checked by `autotester doctor`)

| Open | When |
|---|---|
| `docs/SNAPSHOT.md` | every session start (the hook injects it) and before picking a unit — the whole project in one screen |
| `docs/intent.md` | you need the numbered outcomes (O1–O15) a capability must serve, or a criterion cites `serves: intent#O*` |
| `docs/spec.md` | you are deriving a contract criterion, or need the requirement (R1–R65) and the user types a flow touches |
| `docs/features/team-loop/intent.md` | you are building or checking Group 10 (T-197..T-201): the feature-level intent, outcomes O8-O15, its four user types and Umesh's 2026-10-07 answers |
| `docs/plan.md` | you are picking the next unit or wave — the remaining units in dependency order, with what is held on a human gate |
| `target.md` | you want the roadmap: what's shipped (✅) vs target (🎯), the milestone checklist, and the two-layer goal — open at session start to stay on track |
| `docs/ARCHITECTURE.md` | you need where a concept lives, how stages fit, the data model, execution or security model |
| `docs/MAP.md` | you need the generated directory map (module → one job) or schema summary (model → meaning) |
| `docs/FEATURES.jsonl` | you need a feature's history, its reason, or whether it was retired (append only via `autotester ledger add`) |
| `docs/DECISIONS.md` | you are about to change an approach or revive one — read the *why* first (append only via `scripts/append_decision.ps1`) |
| `docs/archive/INDEX.md` | the quarterly archive, or checking whether an old approach was REJECTED |
| `docs/research/market-2026-09.md` | choosing a library to reuse or positioning against a competitor |
| `docs/research/schema-2026-09.md` | changing a schema model, adding an interop adapter, or wiring a benchmark |
| `docs/research/testsprite-2026-09.md` | choosing a mechanism for the oracle, the failure bundle or the CLI contract — how the funded competitors do it, and the verified gaps between our execution-model claims and our code |
| `docs/research/crawl-reuse-2026-09.md` | designing T-165 crawl units (hybrid BFS/DFS, incremental crawl, change tracking, permission surface, API capture) — licence + ADOPT/PORT/AVOID per tool |
| `qa/contracts/*.md` | building or checking a unit — the criteria it is judged against |
| `.work/grill-*.md` | the reasoning behind a design (grill captures); not committed |


## Design rules (enforced by `uv run autotester doctor`, not by memory)

These exist because `d:/erp` shipped without an upfront schema and became unreadable to humans and
expensive for agents to hold in context. The rules are cheap now and unaffordable later.

- File ≤ 300 lines · function ≤ 50 lines · module docstring states its one job.
- Every domain shape is a Pydantic model in `schema/`, with `extra="forbid"`.
- One concept, one place — a class or function defined in two modules is a bug.
- No `*_v2.py` / `*_new.py` — edit in place.
- Scratch, logs, and evidence go to `.work/`, never the repo root.
- All model calls go through `providers.base.Provider`; prompts are files, not inline strings.

## Credentials (hard boundary)

- Values live only in **one gitignored `.env` at the REPO ROOT**, shared by every project
  (`core/paths.py` `ProjectPaths.env_file`, Umesh 2026-09-03; `core/env.py::load_repo_env` is the
  shipped loader). There is **no `projects/<slug>/.env`** — do not look for one or write one.
  Scoping is by **key namespacing**: keys are prefixed per project (`PATHLYNKS_*`) and a project can
  resolve **only** the keys it declares in its `SecretRef[]`. `SecretRef` holds the **key** and its
  domain scope — never a value.
- Prompts carry `{{SECRET:KEY}}`; substitution happens at `page.fill()` time only, scoped to the
  project's `allowed_domains`. `core.redact.assert_no_raw_secrets` is the gate before any model call.
  Note `browser/secrets.py::_host_matches` is a **suffix** match (`host == domain` or
  `host.endswith("." + domain)`), so declaring `vidysea.com` also admits every subdomain of it.
- Screenshots mask secret inputs before capture; logs pass `Redactor.scrub`.
- Testing against a real product requires a **test account** — never a live user's credentials.
- `RunApproval` (D-018) is **enforced where the code enforces it, which is not everywhere.** A crawl /
  explore run checks a signed approval (`stages/explore_consent.py`; HMAC-SHA256 over the bound
  payload keyed from `AUTOTESTER_APPROVAL_KEY` in the same repo-root `.env`, so a row cannot be forged
  without the key — AT-110). **UI case runs (`ui/routes_runs.py::trigger_run`) check none today —
  AT-570, open.** Do not write or repeat "every run needs an approval" as though it were implemented;
  say which path enforces it.
- **The boundary is the supplied account's own permissions, and that is Umesh's to set, not an
  agent's to second-guess** (`qa/gates/write-policy-tier.md`, D-018, D-053). `write_policy` still
  *defaults* to `read_only` in the schema, but `ALLOW_WRITES` is authorized on every target including
  production: the account Umesh provisions **is** the scope, so a tester presses the buttons and
  enters the data that account may. Narrowing a run below the account's rights does not make it
  safer — it makes the report incomplete, which is the failure this project refuses (O4). Do not
  re-litigate this gate; report what a run actually did instead.

## Maker-checker discipline (installed 2026-09-03)

This project runs dev work through the maker-checker pair:

- **Substantive dev work** (feature, module, schema change, multi-file edit) → route through
  `/maker`. Announce in one line; the user can say "normal" to opt out.
- **Trivial work** (typo, single command, read-only) → normal mode, no ceremony.
- Ground truth lives in `qa/contracts/` — **maker never edits it**; feedback goes verbatim into
  `qa/feedback-inbox.md`; `/checker` folds it in.
- Only `/checker` can PASS a unit. "Done" claims without a checker verdict are invalid.
- Open issues: `qa/issues.jsonl` (canonical). Adapter: `qa/adapter.json` (coding; verify =
  `uv run pytest`, `uv run ruff check src tests scripts`, `uv run autotester doctor` — no CLI
  `-q` on pytest; see Commands below, AT-503).
- **The maker↔checker handshake is files, never memory:** maker's request = manifest at
  `Status: ready-for-check` (with `Fix cycle: N`); checker's reply = `qa/verdicts/<same-slug>.md`
  (with `Cycle checked: N`); maker's close-out = manifest flip to `checked-PASS`.
- **AUTO-CONTINUE (no human hand-crank):** on session start, if the hook line or `qa/` shows
  pending state (unchecked manifest · PASS not closed out · open issues · stale `.last-tick`), run
  `/maker continue "d:/autoTesting"` **before anything else**. The maker self-continues via
  `ScheduleWakeup` and dispatches its own checker subagents and sweeps; the only human actions are
  `/maker init` (once) and answering HUMAN_GATE decisions.
- **Ledger on PASS:** when a goal task with `user_value: high` closes on a checker PASS, the maker appends a `docs/FEATURES.jsonl` row (`autotester ledger add … --unit T-NNN --verdict qa/verdicts/<slug>.md`) with a **prefilled** reason (task note + originating instruction) shown to Umesh to confirm or edit; `normal` tasks auto-stamp `update`. Before picking a unit, run `autotester ledger relitigation "<unit title + description>"` — a gate means a HUMAN_GATE. Rules decide only where certain (D-004).
- **Push on PASS (D-007, standing exception to confirm-first):** after every checker-PASS commit,
  the checker pushes `origin master` itself — no confirmation asked. This repo is public
  (github.com/umeshsugara-ai/autoTesting); commits reaching this point are already narrowly
  scoped and independently verified. Known residual: the harness safety classifier may still
  block a `git push`/`gh` call regardless of this authorization — if so, report the block and
  hand it to Umesh exactly as before, do not attempt to route around it.
- Manual overrides (never required): `/checker sweep` · `/loop /maker continue "d:/autoTesting"`.

## Commands

```bash
uv run pytest                   # tests — no -q here: pyproject's addopts already sets -q;
                                 # stacking another -q makes pytest -qq, which prints NO summary
                                 # line at all (AT-503, measured 2026-09-18)
uv run ruff check src tests scripts  # lint
uv run autotester doctor        # design rules
uv run autotester providers     # which model providers have credentials
```

## Lab Protocol (installed 2026-09-03, D-000) — decision drift, not just file drift

- **Approver:** Umesh — sole owner of PROCEED/ROLLBACK/PIVOT verdicts, freezes, and enforcement-path changes.
- **History:** `docs/DECISIONS.md` is APPEND-ONLY. Only write path: `powershell -File scripts/append_decision.ps1 -EntryFile <entry.md>` (direct Edit/Write is denied by the hook). Replacement = a new entry with `**Supersedes:** D-NNN -- <why old removed AND why new better>`. Old entries are never touched; effective status is computed.
- **State:** `docs/ARCHITECTURE.md` prose changes only under a DECISIONS entry whose `Changes-authorized` names the section. Generated sections are regenerated by `autotester map`, never hand-edited.
- **Enforcement paths** (`.claude/hooks/*`, `scripts/append_decision.ps1`, `.claude/settings.json`, `qa/hooks/*`) need `Approved-by: Umesh` on the authorizing entry.
- **Validators:** `qa/contracts/` judged by `/checker` + `uv run autotester doctor` + `uv run pytest` (no CLI `-q`, AT-503). No separate `contracts/verify_contracts.py`.
- **Task tracking:** `.goal/goal.json` (stable ids `T-NNN`); DECISIONS entries cite them in `Links`.
- Re-proposing anything REJECTED/SUPERSEDED in the injected decision index without flagging it is a protocol violation. End a protocol session with `/landplane`.
