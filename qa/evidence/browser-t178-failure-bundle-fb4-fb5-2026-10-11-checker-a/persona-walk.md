# T-178 FB4/FB5 dev persona walk (checker A, 2026-10-11)

Persona: developer-tester who knows the CLI and wants to review what the machine proposes before
paying for model calls. Code: pristine copy of a7d3fa6c. Throwaway root, project `demo`
(name `Demo <b>App</b>`, approved FlowSpec, 5 seeded cases p0/p1/p2/p3/pinned). No model
credentials present on the machine (providers: mock only).

| Screen | What the dev tried | What blocked or confused them | Severity |
|---|---|---|---|
| Project home, FlowSpec page (200, 0 console errors) | Looked for the Generate control | The control is on the FlowSpec page, not on a page called "Learn"; it is the only button of its card. Clear enough. | low |
| Refusal 1 (POST /cases/generate, 400, themed) | Clicked "Generate cases" with nothing approved | Title "Case proposals need human review", text "human approval of HAPPY proposal required; flow is pending", then the exact command `autotester expand demo --proposals` plus "use --approve or --prune with a proposal ID and --by your name." Themed, nav intact, no JSON or traceback. Gaps: the page has no onward button or link (only the sidebar), and the wording "flow is pending" is terse. Also nothing says that --approve needs a proposal ID that --proposals prints. | low |
| Cases page (200) | Checked the seeded cases appear | All 5 seeded cases listed (class, steps, rename/delete). The page does not show priority or the pinned flag, so a dev cannot confirm what `?priority=p0` will select from the UI. | low |
| CLI door | `expand demo --proposals`, 12 approvals, 1 prune, `--proposals` again, `expand demo` | Works as documented. 13 proposals listed (one line each: id, status, class, title); approve/prune print the full list each time (noisy but informative); `expand demo` with no provider exits 1 with "provider 'langchain-fallback' has no credentials -- run `autotester providers`" and nothing is generated (cases.jsonl stayed at 5 rows). A rejected approval attempt was not exercised. | low |
| Refusal 2 (after approvals, 400, themed) | Clicked "Generate cases" again | Now "No model provider configured": "Generating cases needs a model. No provider on this machine has credentials, so nothing was generated." with an "Add a credential" button. Button navigates to /projects/demo/env (200, 0 console errors). The gate order is right: human approval is checked before the credential. | low |
| POST /run?priority=p0 (and p0&p1, and no query) | Pressed run for p0 | 400 JSON `{"detail":"no AI provider is configured (set an API key in .env) -- cannot grade a run"}`. It is understandable, but it is raw JSON (a script-style endpoint, not a themed page) and it hides the consent gate behind the credential gate, so the dev cannot learn from this call whether the p0 selection would be accepted. `?priority=p9` gives 422 with a clear "Input should be 'p0', 'p1', 'p2' or 'p3'". | low |
| Report page (200) | Looked for queued rows | "no runs yet" (no run was queued by any refused request). | none |

No finding of severity medium or high. Escaping: the project name `<b>` is shown literally in the
sidebar, title and refusal pages; the slug appears only inside `<code>`.
