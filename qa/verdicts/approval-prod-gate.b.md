# Verdict B (adversarial security) - approval-prod-gate

Cycle checked: 2
Head reviewed: be2f0bd3
Verdict: PASS

Verified safe (live-target paths all reach require_project_approval, which drops account-derived rows and demands signed production:true; missing key fails closed via SigningKeyMissing):
- covering_approval production branch precedes the credential-derived mint (explore_consent.py:60-63); no account row minted for production.
- crawl CLI/UI (require_consent), run_launcher (UI Run, queue, Test button, scheduler tick via schedule_gate), release.py, orchestrate_gate.release_preflight, agents/guards.py, adversarial._gate.
- check_crawl_approval.py: production fails without key, rejects account-derived and production:false rows, verifies signature and bounds.
- 57 targeted tests pass (tests/test_approval_prod_gate*.py).

No bypass found. Residual (non-blocking):
1. The production flag lives in editable projects/<slug>/project.json; flipping it false (and forging summary project_production) downgrades the gate. Same trust level as editing code.
2. ai_capture.py:95, discover.py:49, cli_video_review.py:76 still call bare require_approval. Not reachable for a project's live target today (adversarial gates first; READ and VIDEO_REVIEW are not the live target), but a future direct caller of ai_capture would skip the production rule.
