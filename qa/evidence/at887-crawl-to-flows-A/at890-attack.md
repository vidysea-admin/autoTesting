# AT-890 attack findings (sub-checker A), tree check-at887-a @ 6d70c0ec

Scripts: scratchpad/at890/attack.py (matrix, 79 cases x 3 entry points, MockProvider spy, store-backed
project with 3 declared SecretRefs + undeclared OTHER_KEY in repo .env) and gaps.py (gap 6/9, placeholder).
autotester.__file__ confirmed inside the check tree. Outputs: matrix2.txt, matrix.json, gaps.txt.

## Result (identical across expand / expand_flow / compile_evals for every case)
- 53 clean (value masked: [REDACTED] / <email> / <phone>), 16 refused before any provider call (ValueError), 24 raw rows = 8 cases x3 reached the spy.
- Declared + undeclared .env value in flow name, step value, target, navigate-URL query, any spelling the exact scrub
  or guard catches: CLEAN or refused. Case-changed, separators changed, no separators, spaced chars, zero-width,
  Cyrillic homoglyph, reversed, URL-encoded, base64, base64url, hex, HTML entity, split across target+value: all REFUSED.
  Plain / punctuation-wrapped / inside longer token / short plain (5 chars): scrubbed to [REDACTED]:KEY.
- Note, narration, on_screen_text, expected.*, preconditions, screen name/url are NOT rendered in the prompt
  (build_expand_prompt renders only flow name + "order action target = value"), so they cannot reach the provider.
- {{SECRET:ST_PASS}} in value, target and navigate URL reached the spy verbatim; raw value never substituted.
- Emails: plain, plus-tag, UPPER, subdomain, IDN, ?email= query, mailto:, in name, in target -> <email>.
- Phones: 10-digit, +91 spaces/dashes/none, 91-prefix, (+91), (98765) 43210, 5-5, dotted, 0-prefix, US, tel:, Devanagari,
  fullwidth digits, in URL query, in target, in flow name -> <phone>.

## Reached the provider unmasked (all outside exact-secret scope; heuristic masks)
1. 5-char declared secret, base64 spelling WnE5eEs= : the AT-607 disclosed boundary (<=7 raw chars get no encoding guard). Known, not new.
2. URL-encoded email ada.lovelace%40example.org (realistic in a crawled ?email= query): WARNING, mask_pii needs a literal '@'.
3. Fullwidth-at address, ada[at]example.org, "ada dot lovelace at example dot org": obfuscations, expected miss.
4. "9 8 7 6 5 4 3 2 1 0" and "nine eight seven ...": expected miss.
5. Person name "Ada Lovelace" in step value of a "First name" field: NOT masked (mask_name_value is not wired into the expand prompt;
   the docstring says names are only masked where a label says so). Recorded only, as asked.
No exact-secret (declared or undeclared) leak found.

## Placeholder side effect (availability, not a leak)
Declared value equal to "SECRET" turns {{SECRET:ST_PASS}} into {{[REDACTED]:ST_PASS:ST_PASS}} (placeholder-intact=False);
value "ST_PASS" -> refused. Degenerate secrets only.

## Gap 6 (no saved project)
gaps.py: store has flowspec + approved proposals but no project.json -> declared-looking secret Hunter2-Zebra-4411 and an
.env-only value reach the spy raw in all 3 entry points (12 prompts each); only the PII mask applies. Same if project.json exists
but .env lacks the key (nothing known to scrub: correct).
Callers: src cli.py:235 (expand_stage.expand(spec, model, store=store_)) preceded by cli.py:213 exit when load_project() is None;
ui/routes_learn.py:256 expand(spec, provider, RepoDocs(), store=store) preceded by _load_project_or_404 (:223). Both pass store=.
eval_compiler.py:107 expand_flow(..., store=store) passes store (no secrets=). compile_evals has no src caller (tests/evidence only).
No other src caller (grep stages.expand / expand_stage / compile_evals). RULING: not reachable from a real caller; a latent fail-open
for a direct library caller with a store lacking project.json. Low. Suggest raising (or loading .env with an empty Project) instead of skipping.
Side note: routes_learn.py:256 catches only ProviderError, so a guard ValueError there is uncaught (cli.py:236 does catch ValueError).

## Gap 9 (compile_evals spy)
gaps.py: compile_evals(spec, persona, [], spy, store=store) -> 12 provider prompts; value line rendered
"2. fill email field = <email> [REDACTED]:ST_PASS"; no raw secret or email. Covered through expand_flow(store=store). The 79-case matrix
also ran compile_evals. compile_evals has no secrets= parameter, so coverage depends on store.load_project().

## Provider calls
expand.py:184 only (provider.act(prompt, ExpandedSteps, prompt_file, fed_id=flow.id)): template + class + masked flow.name + masked
"order action target = value" lines. fed_id is the flow id (trace metadata). eval_compiler.py makes no direct call; its sole path is
expand_flow (:107). Scenario branches (_branch_case) are deterministic, no provider.
