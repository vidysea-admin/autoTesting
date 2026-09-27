# Mode D notes -- at608-609-scrub-leftovers, checker cycle 1

Server: worktree venv uvicorn on 127.0.0.1:8097, AUTOTESTER_ROOT pointed at a
fresh scratch project seeded with:
- Project "demo" declaring secret DEMO_PASSWORD, .env DEMO_PASSWORD=hunter2
- flowspec.json broken and echoing the secret: {"project":"demo","screens":"hunter2"}
- an empty Crawl "crawl_demo" (no approval granted)

Driven with real headed (headless=False) Python Playwright from the worktree venv.

## 01-crawl-page.png
GET /projects/demo/crawls/crawl_demo -- "hunter2" absent from both page.content()
and inner_text("body"); "[REDACTED]" present in the "Against the FlowSpec" card.
Matches AT-608's fix. 0 console errors on this page load.

## 02-crawls-list-before-submit.png / 03-after-bounds-submit.png
The moved `crawl_view.bounds_form` renders on /projects/demo/crawls (the "New
bounded crawl" card) and is fillable/submittable: filled all four fields and
submitted the real POST to /projects/demo/explore. The route reached its normal
D-018 consent gate and returned "Crawl approval required" (403) because this
scratch project has no crawl-approval on file -- expected, correct behaviour for
an unapproved project, not a defect introduced by the _bounds_form -> bounds_form
move. One console error recorded: "Failed to load resource: ... 403 (Forbidden)",
which is the browser logging that same expected 403 response, not a page crash.

Full machine-readable results: report.json in this directory.
