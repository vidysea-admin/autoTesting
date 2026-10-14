# Verdict: scripts-env-bounds

Cycle checked: 1
Verdict: PASS
Commit: 80f7b6be

- (a) .env: scripts/run_real_acceptance.py calls core.env.load_repo_env(root), the same loader as cli.py, ui/app.py and check_crawl_approval.py. No duplicate loader.
- (b) Selection is local to stages/real_acceptance.py. core/consent.py is untouched. Rows are only reordered (newest first) and probed one at a time through require_project_approval, so a row is picked only if _reject_reason passes (target, kind, bounds, expiry, production, signature, revocation). Widest-first is applied only to rows that already cover.
- (c) Bounds = min(request or default, chosen row). A request above every row raises ApprovalRequired, never clamped. preflight re-checks the chosen bounds.
- (d) 232 scoped tests pass (real_acceptance, consent, all approval tests). ruff clean. doctor clean. merge-tree against master is clean.
