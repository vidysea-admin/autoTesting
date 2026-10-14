# Verdict: approval-residual-callers

Cycle checked: 1
Commit: abeffb26
Verdict: PASS

## Findings
- (a) capture_run callers: src has none besides its definition (adversarial, ai_judge and ai_report import only CaptureWithheld/Send). The only calls are tests/test_ai_capture.py and tests/test_approval_signing.py (two), all pass a Project via project_of(). Repo-wide grep (py, md, ps1, json, toml) found no other caller.
- (b) discover: approved_roots resolves each root with strict=True and requires is_dir, so a URL string raises OSError/ValueError before the gate. The gate target is str(root) with kind READ, so a row for a live URL cannot satisfy it (tested). Video review: target is provider.id (a class constant of a registered provider, not user text) with kind VIDEO_REVIEW; LIVE_CASE/CRAWL/VIDEO_REVIEW rows for a live URL do not satisfy it (tested). Claims hold.
- (c) other bare require_approval callers: explore_consent._require is reached for a production project only through require_project_approval (production branch returns first), so non-production only; scripts/check_crawl_approval.py is a post-hoc verifier that explicitly rejects account-derived rows on production projects. No other src caller. consent.py internals and tests excluded.
- (d) Ran 11 test files (approval residual/signing/prod_gate/prod_gate_paths, consent, ai_capture, discover x2, cli_video_review x2, video_review_gates): 371 passed. ruff clean. doctor clean (2 known advisory). merge-tree vs master: clean (tree 86732783).

## Notes
- A wide `-k` pytest run hung/slowed under CPU load and was killed; scoped files used instead.
- Residual (non-blocking): the local-only claim for video review rests on provider ids staying non-URL; no test pins that.
