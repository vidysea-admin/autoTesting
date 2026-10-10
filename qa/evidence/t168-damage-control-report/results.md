# t168 checker probe results (checker-built records; scripts in this directory)

probe_honesty.py (run on 56d24768, worktree venv): 24 of 25 checks PASS.
- H1 no baseline: "No trusted baseline, so no regression claim"; no Regressed/Fixed lists.
- H2 not-run case = `not run` (+reason), executed-but-ungraded = `no verdict`, planless flow = `not run`, unfinished release warned.
- H3 every non-completed crawl status, a bounded crawl with 100%/no holes, and a completed crawl with no coverage record are all "Incomplete"; holes listed; `not_visited` appears only in coverage.
- H4 missing release/persona/crawl/cases render `Unavailable: <reason>`.
- H5 persona counts equal the rows listed.
- FAIL H4b: a run with results but ZERO NETWORK evidence renders "No failing first-party response in the evidence read (run r1)." (reads clean; capture-never-ran is indistinguishable).

probe_secret.py: a secret planted in 15 text fields (flow id/title, issue detail, flagged reason, baseline note, git sha, verdict criterion/reason/fix_hint, API url, persona summary/screens, crawl hole name, stop reason, case title).
- plain secret `Zq9-plainChecker7`: 0 in HTML, 0 in CLI output, scanner 0 leaks.
- secret containing `& < > '` (`p&ss<w>o'rdQ9`, redactor verified to hold it, probe_env.py): ABSENT raw but PRESENT HTML-escaped (`p&amp;ss&lt;w&gt;o&#x27;rdQ9`) in 15 places; scripts/check_no_secrets.py exits 0 "0 leak(s)" on that file.
  Cause: stages/unified_report.py unified_html scrubs AFTER render_html escapes (the Redactor matches exact bytes).
- XSS `<script>`/`<img onerror>` in issue detail, title, reason: escaped; browser: window.__xss undefined, 0 dialogs, 0 script elements.
Falsification (single-hunk, own copies, green before / red after): dc1 incomplete=False -> red on `incomplete is True`; dc2 history loader bypass -> red (SENTINEL-HISTORY); dc3 history section dropped -> red; dc4 `_load_redactor` stubbed to an empty Redactor (one hunk) -> red (secret in artifact). Single-layer mutants (final scrub only, workflow redactor only) SURVIVE: two redundant layers.
