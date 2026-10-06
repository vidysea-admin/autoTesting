# GATE — t191-video-download-route

**Opened:** 2026-09-27 (by /maker, cycle 1 of `t191-video-reachable`, dispatched to close
`ISS-t191-run-video-2`)
**Blocks:** nothing (this unit's fix for the live UI does not depend on the answer below) --
this is a follow-on decision, not a blocker for this unit's PASS.
**Approver:** Umesh (Lab Protocol)

## The question in one line

`GET /projects/{slug}/report.html` (`ui/routes_report.py::download_report_html`) still emits a
video `<a href>` that provably cannot resolve wherever the browser saves the download. Now that
the live per-run page has a working video route (this unit), should the download get fixed too,
and how?

## Why it needs a decision, not a quiet fix

The dispatch that opened this unit named this as a mandatory decision: leaving a known-broken
link in shipped output is worse than emitting none, but it also explicitly forbade "option (b)"
(repackaging the download as a zip or a stable path so the video sits beside the export) as a
scope increase for THIS unit. That leaves a real tension for the two remaining directions:

- Making the link resolve requires `export_html` (or the download route) to know a live-server
  base URL to point at instead of a bare run-relative path -- a real code change.
- `stages/report_export.py` is at **exactly 300 lines**, `autotester doctor`'s hard file-length
  cap, with **zero headroom** (confirmed this cycle: `wc -l` -> 300, same file the checker
  flagged in the T-191 cycle-2 verdict as needing a future split). Threading a new parameter
  through `export_html` -> `_case_section` -> `_video_link_html` needs roughly 8-10 new lines by
  the most compact design tried, which does not fit without first splitting the file -- a
  separate, wider-blast-radius refactor this unit was not scoped to do.
- `qa/contracts/ui-report.md` UR3 ("stream the exact same file `export_html` would produce ...
  never a second, UI-only reimplementation of the export logic") and `qa/contracts/report-export.md`
  RE3 (self-contained HTML, video linked not embedded; named video exception quoted below)
  are both checker-owned. Rewriting the download's HTML bytes in the UI route after export --
  the only fix that avoids the line-cap problem -- sits in real tension with UR3's letter even
  though it would not touch the export's screenshots, styling, or case sections. A maker cannot
  self-authorize reading that tension as acceptable; only the checker amends its own contracts.

Decision claim D-050: "It also amends qa/contracts/report-export.md RE3 with one named exception. A kept run video (EvidenceKind.VIDEO, T-191) is linked from the exported HTML by a path relative to the run directory, never embedded. The HTML stays self-contained for everything else: screenshots are still base64-embedded, and the page still opens with no server or network." <!-- decision-claim: {"id":"D-050","what":"It also amends qa/contracts/report-export.md RE3 with one named exception. A kept run video (EvidenceKind.VIDEO, T-191) is linked from the exported HTML by a path relative to the run directory, never embedded. The HTML stays self-contained for everything else: screenshots are still base64-embedded, and the page still opens with no server or network."} -->

## What this unit did instead

Left `download_report_html` byte-for-byte unchanged. Its video link stays exactly as broken as
`ISS-t191-run-video-2` found it. This is deliberate, not an oversight:

1. The unit's actual deliverable -- a live route that serves a kept video from its real
   location, linked from `/projects/{slug}/runs/{run_id}` -- gives every user a working path to
   the same video regardless of whether they ever click the download button. The download was
   never the only way to reach a video; it was the only way that was *supposed* to work and
   didn't.
2. Any fix at the export layer needs either a `report_export.py` split (real, separate unit) or a
   checker-authorized UR3/RE3 amendment (not a maker's call) -- both bigger than "add a route and
   link it," which is what this dispatch actually scoped.
3. The failure mode today is benign: a browser opening the dead link gets an ordinary
   "file not found," not a wrong file, not leaked data, not a crash.

## Options for Umesh / the checker

- **A -- Leave it, permanently.** The live route is the one supported way to watch a video; the
  download's own video link is deprecated in place (maybe replaced with plain text noting "view
  video in the live report" instead of a dead `<a>`, which is a same-file-budget-cost change,
  not free, but far cheaper than a working redirect).
- **B -- Split `report_export.py` first**, then parameterize `export_html`/`_video_link_html`
  with an optional `video_href_base` so `download_report_html` can pass the live route's URL and
  get a download whose video link actually resolves. Real fix, real scope: a file-length refactor
  plus the parameter-threading described above.
- **C -- Checker amends UR3 with a named video-link exception** (the same shape RE3 already got
  under D-050), explicitly allowing a post-export rewrite of just the video `<a href>` in the
  download route, without touching screenshots/styling/case sections. Smaller than B, but the
  amendment is the checker's call, not something this gate can pre-decide.

## How to answer

Add `Answered: YYYY-MM-DD — A | B | C` below, or tell the checker or maker session.

## Answer

Answered: 2026-09-28 -- ROOT-CAUSE FIX, not A and not deprecation -- Umesh, direct instruction.
Verbatim: "fix krro issue, jab link working hai tho break kyu ho rhaa hai find root cause and fix it".

This explicitly rejects option A (leave it / deprecate the link). The download must carry a video
link that resolves. The report_export.py 300-line cap is a constraint to work through, not a reason
to ship a dead link -- split the file as its own unit first if that is what it takes.
The checker owns any UR3/RE3 amendment that the chosen mechanism needs; ask for it, do not assume it.
