"""at438 cycle-3 re-derivation, checker re-rule, 2026-09-26.

Independent re-run of the cycle-3 checker's own 60-layout + attack corpus
(qa/evidence/browser-at438-display-contents-2026-09-16-checker-c3/moded3.py,
attack3.py), reused verbatim for case construction (same pages, same ground
truth method: full-page screenshot hash before/after replacing the sentinel
text node with same-length glyphs, monospace, positive control per page),
but:
  - REAL HEADED Chromium (headless=False), via the repo venv's Playwright.
  - Only three detector versions: OLD = c687b73^ (pre-AT-438, the true
    pre-unit baseline per the answered gate at438-u14b-baseline.md option a),
    C3 = 9fc937d (cycle 3), MASTER = HEAD. C3 and MASTER text are verified
    byte-identical before running (no commit has touched visual_order.js
    since 9fc937d), so this also directly proves the MASTER answer.
  - Evidence written only under
    D:/autoTesting/qa/evidence/browser-at438-rerule-2026-09-26-checker/.
  - Never touches the working tree; detector text is read via `git show`
    into this scratch dir once, then read from disk here.
"""
import hashlib
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
ROOT = Path("D:/autoTesting")
EVID = ROOT / "qa/evidence/browser-at438-rerule-2026-09-26-checker"
EVID.mkdir(parents=True, exist_ok=True)

VERS = {
    "OLD": (HERE / "OLD_c687b73^.js").read_text(encoding="utf-8"),
    "C3": (HERE / "C3_9fc937d.js").read_text(encoding="utf-8"),
    "MASTER": (HERE / "MASTER_HEAD.js").read_text(encoding="utf-8"),
}
assert VERS["C3"] == VERS["MASTER"], "C3 and MASTER text must be identical (checked separately too)"

POS = '<p style="margin:0 0 30px">POSCTRL_OK</p>'
HEAD = ('<!doctype html><meta charset=utf-8><style>body{margin:8px;font:20px monospace}{css}</style>'
        '<body>' + POS + '{body}</body>')
S = "SENTZQ_KEY"
C = f'<div id="c" style="display:contents">{S}</div>'


def jsbuild(parent_sel, tag="div"):
    return (f"const c=document.createElement('{tag}');c.id='c';c.style.display='contents';c.textContent='{S}';"
            f"document.querySelector('{parent_sel}').appendChild(c)")


def shadow(inner, light=C):
    return (f'<div id="host">{light}</div>',
            f"document.getElementById('host').attachShadow({{mode:'open'}}).innerHTML={json.dumps(inner)}")


# --- 60-layout table (verbatim from the cycle-3 checker's moded3.py CASES) ---
CASES = [
    ("plain contents", "", C, None),
    ("open details", "", f"<details open><summary>s</summary>{C}</details>", None),
    ("closed details", "", f"<details><summary>s</summary>{C}</details>", None),
    ("closed details, contents nested twice", "", f'<details><summary>s</summary><div style="display:contents">{C}</div></details>', None),
    ("cv:hidden block", "", f'<div style="content-visibility:hidden">{C}</div>', None),
    ("display:none", "", f'<div style="display:none">{C}</div>', None),
    ("hidden attribute", "", f"<div hidden>{C}</div>", None),
    ("visibility:hidden ancestor", "", f'<div style="visibility:hidden">{C}</div>', None),
    ("opacity:0 ancestor", "", f'<div style="opacity:0">{C}</div>', None),
    ("closed dialog", "", f"<dialog>{C}</dialog>", None),
    ("contents inside ul", "", f"<ul><li>a</li>{C}</ul>", None),
    ("author span:empty{display:none}", "span:empty{display:none}", C, None),
    ("author *:empty{display:none}", "*:empty{display:none}", C, None),
    ("summary itself display:contents, closed details", "", f'<details><summary id="c" style="display:contents">{S}</summary><p>body</p></details>', None),
    ("summary contents > contents span, closed", "", f'<details><summary style="display:contents"><span id="c" style="display:contents">{S}</span></summary></details>', None),
    ("SECOND summary display:contents, closed details", "", f'<details><summary>first</summary><summary id="c" style="display:contents">{S}</summary></details>', None),
    ("contents wrapping a summary, closed details", "", f'<details><div style="display:contents"><summary>{S}</summary></div></details>', None),
    ("hidden=until-found on block box", "", f'<div hidden="until-found">{C}</div>', None),
    ("hidden=until-found on inline span box", "", f'<p><span hidden="until-found">{C}</span></p>', None),
    ("open dialog (non-modal)", "", f"<dialog open>{C}</dialog>", None),
    ("modal dialog (showModal)", "", f'<dialog id="d">{C}</dialog>', "document.getElementById('d').showModal()"),
    ("fieldset > legend display:contents", "", f'<fieldset><legend id="c" style="display:contents">{S}</legend><p>f</p></fieldset>', None),
    ("fieldset > legend > contents", "", f'<fieldset><legend>{C}</legend><p>f</p></fieldset>', None),
    ("fieldset > contents", "", f'<fieldset><legend>L</legend>{C}</fieldset>', None),
    ("table with display:contents tr", "", f'<table><tbody><tr id="c" style="display:contents"><td>{S}</td></tr></tbody></table>', None),
    ("table: contents td text", "", f'<table><tr><td id="c" style="display:contents">{S}</td><td>x</td></tr></table>', None),
    ("table: tbody+tr contents, JS text in tr", "", '<table><tbody style="display:contents"><tr id="tr" style="display:contents"><td>x</td></tr></tbody></table>', jsbuild('#tr')),
    ("slot display:contents: slotted contents child", "", *shadow('<slot style="display:contents"></slot>')),
    ("slot inside visible div: slotted contents child", "", *shadow('<div><slot></slot></div>')),
    ("slot inside CLOSED details in shadow", "", *shadow('<details><summary>s</summary><slot></slot></details>')),
    ("slot inside cv:hidden div in shadow", "", *shadow('<div style="content-visibility:hidden"><slot></slot></div>')),
    ("slot inside display:none in shadow", "", *shadow('<div style="display:none"><slot></slot></div>')),
    ("unslotted light child (no slot)", "", *shadow('<p>shadow</p>')),
    ("flex container contain:paint height:0", "", f'<div style="display:flex;height:0;contain:paint">{C}</div>', None),
    ("grid container contain:paint height:0", "", f'<div style="display:grid;grid-template-rows:0;height:0;contain:paint">{C}</div>', None),
    ("flex container clip-path hides all", "", f'<div style="display:flex;clip-path:inset(0 0 100% 0)">{C}</div>', None),
    ("grid 0-size track overflow visible", "", f'<div style="display:grid;grid-template-columns:0;grid-template-rows:0">{C}</div>', None),
    ("nested closed>closed, contents at L1", "", f'<details><summary>o</summary>{C}<details><summary>i</summary><p>x</p></details></details>', None),
    ("nested closed>closed, contents at L2", "", f'<details><summary>o</summary><details><summary>i</summary>{C}</details></details>', None),
    ("nested closed>closed, contents in inner summary", "", f'<details><summary>o</summary><details><summary>{C}</summary></details></details>', None),
    ("nested closed>open, contents at L2", "", f'<details><summary>o</summary><details open><summary>i</summary>{C}</details></details>', None),
    ("nested open>closed, contents in inner summary", "", f'<details open><summary>o</summary><details><summary>{C}</summary></details></details>', None),
    ("nested open>closed, contents at L2", "", f'<details open><summary>o</summary><details><summary>i</summary>{C}</details></details>', None),
    ("closed details, contents wrapper x3", "", f'<details><summary>o</summary><div style="display:contents"><div style="display:contents">{C}</div></div></details>', None),
    ("closed details with ::details-content visible", "details::details-content{content-visibility:visible}", f"<details><summary>s</summary>{C}</details>", None),
    ("details itself display:contents, closed", "", f'<details style="display:contents"><summary>s</summary>{C}</details>', None),
    ("open details display:contents inside closed details", "", f'<details><summary>o</summary><details open style="display:contents"><summary>i</summary>{C}</details></details>', None),
    ("video fallback child", "", '<video id="p" width="200" height="50"></video>', jsbuild('#p')),
    ("video controls fallback child", "", '<video id="p" controls width="200" height="50"></video>', jsbuild('#p')),
    ("audio controls fallback child", "", '<audio id="p" controls></audio>', jsbuild('#p')),
    ("audio (no controls) fallback child", "", '<audio id="p"></audio>', jsbuild('#p')),
    ("canvas fallback child", "", '<canvas id="p" width="200" height="50"></canvas>', jsbuild('#p')),
    ("iframe child (JS)", "", '<iframe id="p" width="200" height="50"></iframe>', jsbuild('#p')),
    ("object (no data) fallback child", "", f'<object>{C}</object>', None),
    ("object with svg data fallback child", "", f'<object type="image/svg+xml" width="20" height="20" data="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2210%22 height=%2210%22/%3E">{C}</object>', None),
    ("textarea element child (JS)", "", '<textarea id="p"></textarea>', jsbuild('#p')),
    ("select element child (JS)", "", '<select id="p"><option>o</option></select>', jsbuild('#p')),
    ("img element child (JS)", "", '<img id="p" width="20" height="20" alt="">', jsbuild('#p')),
    ("input element child (JS)", "", '<input id="p">', jsbuild('#p')),
    ("slotted child, plain slot (must report)", "", *shadow('<slot></slot>')),
]

GT = ("(s) => { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);"
      " let n; while ((n = w.nextNode())) { if (n.nodeValue.includes(s)) {"
      " n.nodeValue = n.nodeValue.replace(s, 'MMMMMMMMMM'); return true; } } return false; }")
MO = ("() => { window.__recs = []; const f = rs => { for (const r of rs) window.__recs.push(r.type + ':' + (r.target.id || r.target.nodeName)); };"
      " new MutationObserver(f).observe(document, {subtree:true, childList:true, attributes:true, characterData:true});"
      " const c = document.getElementById('c'); if (c) new MutationObserver(f).observe(c, {subtree:true, childList:true, attributes:true, characterData:true}); }")
RECS = "() => new Promise(r => setTimeout(() => r(window.__recs), 30))"


def shot(page):
    return hashlib.sha1(page.screenshot(full_page=True)).hexdigest()


def new_page(browser):
    page = browser.new_page(viewport={"width": 900, "height": 600})
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    return page, errors


def run_case(browser, label, css, body, setup, shot_id=None):
    row = {"case": label}
    for tag, js in VERS.items():
        page, errors = new_page(browser)
        page.set_content(HEAD.replace("{css}", css).replace("{body}", body))
        if setup:
            page.evaluate(setup)
        page.wait_for_timeout(150)
        page.evaluate(MO)
        seen = page.evaluate(js)
        row[tag] = {"reported": S in seen, "pos_ctrl": "POSCTRL_OK" in seen, "mutations": page.evaluate(RECS),
                    "console_errors": len(errors)}
        if tag == "MASTER":
            page.evaluate("() => window.scrollTo(0,0)")
            b = shot(page)
            row["gt_found"] = page.evaluate(GT, S)
            page.wait_for_timeout(80)
            row["painted"] = b != shot(page)
            if shot_id:
                page.evaluate(GT, S)  # no-op safety; screenshot already taken pre-mutation below
        page.close()
    for tag in VERS:
        r = row[tag]["reported"]
        row[tag]["verdict"] = "ok" if r == row["painted"] else ("FALSE_POSITIVE" if r else "FALSE_NEGATIVE")
    return row


def run_case_with_shot(browser, label, css, body, setup, shot_name):
    """Same as run_case but also saves a pre-mutation screenshot for MASTER's page."""
    row = {"case": label}
    for tag, js in VERS.items():
        page, errors = new_page(browser)
        page.set_content(HEAD.replace("{css}", css).replace("{body}", body))
        if setup:
            page.evaluate(setup)
        page.wait_for_timeout(150)
        page.evaluate(MO)
        seen = page.evaluate(js)
        row[tag] = {"reported": S in seen, "pos_ctrl": "POSCTRL_OK" in seen, "mutations": page.evaluate(RECS),
                    "console_errors": len(errors)}
        if tag == "MASTER":
            page.evaluate("() => window.scrollTo(0,0)")
            page.screenshot(path=str(EVID / shot_name), full_page=True)
            b = shot(page)
            row["gt_found"] = page.evaluate(GT, S)
            page.wait_for_timeout(80)
            row["painted"] = b != shot(page)
        page.close()
    for tag in VERS:
        r = row[tag]["reported"]
        row[tag]["verdict"] = "ok" if r == row["painted"] else ("FALSE_POSITIVE" if r else "FALSE_NEGATIVE")
    return row


# --- attack3.py point-2 attacks on the NEW mechanisms (verbatim) ---
ROOTS = "window.__roots = window.__roots || [];"


def sh(host_id, mode, inner):
    return (f"{ROOTS} {{ const r = document.getElementById('{host_id}').attachShadow({{mode:'{mode}'}});"
            f" r.innerHTML = {json.dumps(inner)}; window.__roots.push(r); }}")


NESTED = (ROOTS + " const r = document.getElementById('host').attachShadow({mode:'open'});"
          " r.innerHTML = '<div id=\"ih\"><slot></slot></div>'; window.__roots.push(r);"
          " const r2 = r.getElementById('ih').attachShadow({mode:'@M@'}); r2.innerHTML = @INNER@; window.__roots.push(r2);")


def nested(mode, inner):
    return f'<div id="host">{C}</div>', NESTED.replace("@M@", mode).replace("@INNER@", json.dumps(inner))


ATTACKS = [
    ("A1 closed details, NO author override", "", f"<details><summary>s</summary>{C}</details>", None),
    ("A2 open details, NO author override", "", f"<details open><summary>s</summary>{C}</details>", None),
    ("A3 closed, ::details-content{display:contents}", "details::details-content{display:contents}", f"<details><summary>s</summary>{C}</details>", None),
    ("A4 closed, ::details-content{display:inline}", "details::details-content{display:inline}", f"<details><summary>s</summary>{C}</details>", None),
    ("A5 open, ::details-content{display:none}", "details::details-content{display:none}", f"<details open><summary>s</summary>{C}</details>", None),
    ("A6 closed, ::details-content{content-visibility:auto}", "details::details-content{content-visibility:auto}", f"<details><summary>s</summary>{C}</details>", None),
    ("A7 open, [open]::details-content{content-visibility:hidden}", "details[open]::details-content{content-visibility:hidden}", f"<details open><summary>s</summary>{C}</details>", None),
    ("D4 slot->slot, inner CLOSED-mode shadow, slot in closed details", "", *nested("closed", "<details><summary>s</summary><slot></slot></details>")),
    ("D5 closed-mode shadow, slot inside CLOSED details", "", f'<div id="host">{C}</div>', sh("host", "closed", "<details><summary>s</summary><slot></slot></details>")),
    ("D7 closed-mode shadow, slot inside cv:hidden div", "", f'<div id="host">{C}</div>', sh("host", "closed", '<div style="content-visibility:hidden"><slot></slot></div>')),
]


def main():
    results = {"chromium": None, "cases": [], "attacks": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        results["chromium"] = browser.version

        shot_map = {"plain contents": "layout01-plain-contents.png",
                    "closed details with ::details-content visible": "layout43-details-content-visible.png"}
        for c in CASES:
            label = c[0]
            if label in shot_map:
                results["cases"].append(run_case_with_shot(browser, *c, shot_name=shot_map[label]))
            else:
                results["cases"].append(run_case(browser, *c))

        for a in ATTACKS:
            row = run_case(browser, *a)
            results["attacks"].append(row)
            if a[0].startswith("A3"):
                # save a representative attack screenshot too (3rd representative layout)
                page, _ = new_page(browser)
                page.set_content(HEAD.replace("{css}", a[1]).replace("{body}", a[2]))
                page.wait_for_timeout(150)
                page.screenshot(path=str(EVID / "layoutA3-details-content-display-contents.png"), full_page=True)
                page.close()

        browser.close()

    (EVID / "report.json").write_text(json.dumps(results, indent=1), encoding="utf-8")

    # summary counts
    def fn_fp(rows, tag):
        fn = sum(1 for r in rows if r[tag]["verdict"] == "FALSE_NEGATIVE")
        fp = sum(1 for r in rows if r[tag]["verdict"] == "FALSE_POSITIVE")
        return fn, fp

    all_rows = results["cases"] + results["attacks"]
    summary = {}
    for tag in VERS:
        fn, fp = fn_fp(all_rows, tag)
        summary[tag] = {"FN": fn, "FP": fp, "total": len(all_rows)}
    print(json.dumps(summary, indent=1))

    # U14(b): texts OLD reports that C3/MASTER does not (OLD reported=True, C3 reported=False)
    old_yes_c3_no = [r["case"] for r in all_rows if r["OLD"]["reported"] and not r["C3"]["reported"]]
    old_yes_master_no = [r["case"] for r in all_rows if r["OLD"]["reported"] and not r["MASTER"]["reported"]]
    print("OLD reports, C3 does not:", old_yes_c3_no)
    print("OLD reports, MASTER does not:", old_yes_master_no)

    (EVID / "summary.json").write_text(json.dumps({
        "counts": summary,
        "u14b_old_yes_c3_no": old_yes_c3_no,
        "u14b_old_yes_master_no": old_yes_master_no,
    }, indent=1), encoding="utf-8")


main()
