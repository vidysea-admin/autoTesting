# Gate: T-136 positive-path cases INCONCLUSIVE when the screenshot is withheld

Opened: 2026-10-19 (maker, from T-136 r5 live run run-01M5A1FTWZR0XV0WS0QHGDMBXY; report .work/t136-live-report-r5.md)

Question: the 2 correct-login cases met their assertions, but the post-login dashboard screenshot was withheld (mask_exceeds_limit), so the screenshot-grounded verdict rule keeps them INCONCLUSIVE. Should a met assertion rescue a PASS when the screenshot is withheld?

Options:
- A (recommended): No. Keep INCONCLUSIVE; raise the masking limit for the dashboard surface so the masked screenshot is kept and the case can PASS on evidence.
- B: Yes. A met DOM assertion is enough for PASS when the screenshot is withheld; the report marks it "PASS (no screenshot)".

Answer format: "A" or "B" in chat; the maker appends `Answered:` here before acting.
Blocks: T-136 acceptance close-out (the 2 INCONCLUSIVE cases).
