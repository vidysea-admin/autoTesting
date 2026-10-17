// Reachability for visual_order.js — split out (AT-408/AT-416) when the fix
// needed room the 300-line module cap did not have. NOT its own script: this
// file has no wrapper of its own. observe.py splices its text, verbatim, in
// place of the `// AUTOTESTER:REACH_MODULE` marker inside visual_order.js's
// IIFE, so `reachOf`/`isReachable` share that IIFE's closure (`window`,
// `document`) exactly as if this text had never left the file. Edit this file
// for a reachability change; visual_order.js only for anything else.

const SCROLLS = /^(auto|scroll)$/;

// Nearest ancestor that clips its overflow WHERE A READER CANNOT GET AT IT.
// `text-indent:-9999px` and an absolutely-positioned off-screen block both put
// glyphs where no amount of scrolling reveals them.
//
// A genuinely SCROLLABLE pane is the opposite case and was conflated with it
// (AT-379): a reader can scroll an `overflow:auto` pane and read every line,
// so its box is not a boundary. `overflow:hidden` with nothing to scroll still
// is, and the two are told apart by MEASUREMENT — computed overflow is
// `auto`/`scroll` AND the content actually overflows — never by guess.
//
// Per axis, deliberately: `overflow-y:auto; overflow-x:hidden` really does
// hide what runs off its right edge while exposing what runs off its bottom.
//
// TWO running clips, not one (AT-416). A single running clip, narrowed by
// every ancestor's box on the way up and tested against the GLYPH's rect, was
// wrong: a glyph inside a scrollable pane MOVES inside that pane's own box as
// the pane is scrolled, so testing the glyph's CURRENT position against a
// clip an ancestor OUTSIDE the pane contributed made the verdict flip with the
// pane's own scroll offset — reachable only at the instant the glyph happened
// to be coasting through the outer clip band, unreachable a moment earlier or
// later, though nothing about whether a reader can GET there changed. That is
// exactly the scroll-invariance floor this module is charged against (U14a,
// qa/contracts/ui.md): reported=false at rest and reported=true after
// scrolling the SAME pane to the SAME state is two different answers to one
// question, not two different questions.
//
// A reader CAN bring any line inside a genuinely scrollable pane to any
// position within that pane's OWN box by scrolling it — the pane's own box
// does not move when its own content scrolls, only the content does. So the
// question "is this glyph reachable past an ancestor OUTSIDE the pane" does
// not depend on the glyph at all once a scroller has been passed; it depends
// on whether the PANE's own box reaches that ancestor's clip. (Whether a
// SPECIFIC glyph's scroll range actually lands it in the overlap, rather than
// merely somewhere in the pane, is a finer question this does not answer —
// deliberately: U14(b)'s north-star tie-break prefers a reachable glyph
// wrongly kept over a reachable glyph wrongly dropped, and the coarse test is
// the side of that trade this module is built to take.)
//
// The chain is walked in SEGMENTS, not just two (AT-4xx — found by the
// 50-shape corpus once real Chromium finally ran on this fix: two nested
// scrollers under one hard clip re-broke AT-416 one level removed). A
// segment's clip is narrowed by every hard-clip ancestor between one scroller
// crossing and the next, and is tested against that segment's REFERENCE box:
// the glyph's own rect for the first segment (nothing before the first
// scroller moves relative to the glyph), and each further scroller's OWN box
// for the segment after it — never the glyph's, and never an INNER scroller's
// box either. Two nested scrollers taught this: `L2`(auto) inside
// `L1`(auto) inside `L0`(hidden) — testing `L2`'s box (the innermost) against
// `L0`'s clip is exactly as scroll-variant as testing the glyph's own rect
// was, because `L2`'s box moves on screen whenever `L1` — which contains it —
// is scrolled. Only the box of the scroller NEAREST an outer clip is fixed
// relative to that clip (nothing between them scrolls, by definition — if
// something did, it would be that nearer scroller instead). So each scroller
// crossing closes out the current segment and opens a fresh one anchored on
// ITS OWN box, discarding any inner scroller's box as the reference — the
// inner scroller's own reachability was already covered by its own segment.
//
// Returns `{segments, scrollX, scrollY}` — `segments` is an array of
// `{clip, refBox}` (`refBox: null` means "test against the glyph's own
// rect"), each independently required to pass in `isReachable`. `scrollX`/
// `scrollY` is the accumulated scroll offset of the window AND every
// scrollable ancestor (AT-392, AT-408: the walk never stops at the first
// one).
function reachOf(el) {
  let scrollX = window.scrollX;
  let scrollY = window.scrollY;
  let clip = null;
  let refBox = null;
  const segments = [];
  const narrow = (clip, box) => (clip === null ? box : {
    left: Math.max(clip.left, box.left),
    right: Math.min(clip.right, box.right),
    top: Math.max(clip.top, box.top),
    bottom: Math.min(clip.bottom, box.bottom),
  });
  for (let node = el; node && node !== document.documentElement; node = node.parentElement) {
    const style = window.getComputedStyle(node);
    const box = node.getBoundingClientRect();
    const scrollsY = SCROLLS.test(style.overflowY) && node.scrollHeight > node.clientHeight;
    const scrollsX = SCROLLS.test(style.overflowX) && node.scrollWidth > node.clientWidth;
    // AT-417: clip-path and scrolling are independent — a box can be both. A
    // clip-path box that does NOT scroll is a hard clip; one that DOES is a
    // scroller first (its clip is its own box, the very reference the next
    // segment is anchored on, so it can never exclude what that box shows).
    if (style.clipPath !== "none" && !scrollsX && !scrollsY) {
      clip = narrow(clip, box);
      continue;
    }
    if (style.overflow === "visible" && !scrollsX && !scrollsY) continue;
    if (scrollsX) scrollX += node.scrollLeft;
    if (scrollsY) scrollY += node.scrollTop;
    if (scrollsX || scrollsY) {
      // Close out the segment ending at this scroller (tested against the
      // PREVIOUS segment's reference — the glyph, or an earlier scroller's
      // box) and start a fresh one anchored on THIS scroller's own box: it is
      // the new nearest-fixed reference for anything further out, replacing
      // any inner scroller's box.
      segments.push({ clip, refBox });
      clip = null;
      refBox = box;
      continue; // a scroller's own box is a reference, never itself a clip
    }
    clip = narrow(clip, {
      left: scrollsX ? -Infinity : box.left,
      right: scrollsX ? Infinity : box.right,
      top: scrollsY ? -Infinity : box.top,
      bottom: scrollsY ? Infinity : box.bottom,
    });
  }
  segments.push({ clip, refBox });
  return { segments, scrollX, scrollY };
}

function isReachable(rect, reach) {
  // Off the DOCUMENT's left edge or above its top cannot be scrolled to.
  // Further down or right can be, so those stay.
  //
  // THIS LINE HAS BEEN WRONG FIVE TIMES, always the same way: a fix for false
  // POSITIVES that manufactured a false NEGATIVE of the AT-355 shape — a
  // credential rendering in plain type while this returns a clean string.
  // AT-373 (viewport-relative test), AT-379 (a scrollable pane read as a
  // clip), AT-392 (window offset only), AT-408 (walk stopped at the first
  // one-axis scroller), AT-416 (the outer clip tested the glyph's own MOVING
  // rect instead of the scroller's FIXED box, so the verdict flipped with the
  // scroller's own scroll position). Each asked "can a reader SEE this right
  // now?" where the question is "can a reader REACH it, ever?". Details in
  // those ledger rows; the rule here:
  //
  //   a glyph is unreachable only if it sits before the document origin after
  //   everything scrollable has been scrolled back, OR any segment of the
  //   scroller chain carrying it sits outside a hard clip that no scroll of
  //   THAT segment's own reference (the glyph, or the scroller that opened
  //   the segment) moves it into.
  //
  // `reach.scrollX/scrollY` carry the first part — window plus every
  // scrollable ancestor — and are already scroll-position invariant (moving a
  // scroller by `d` moves `rect` by `-d` and `scrollY` by `+d`). Each segment
  // in `reach.segments` is the second part: its `clip` is tested against its
  // `refBox` (or `rect`, the glyph itself, when `refBox` is null — the first
  // segment, nothing before the first scroller moves relative to the glyph).
  // A scroller's own box does NOT move when its own content is scrolled —
  // only the glyph (or an inner scroller) inside it does — so testing each
  // segment's own fixed reference is what keeps every segment invariant
  // (AT-416, and the nested-scroller case one level removed that the 50-shape
  // corpus caught in this same fix once real Chromium finally ran it: a
  // segment's reference must be the NEAREST scroller to its own clip, never
  // an inner one, since only the nearest one's box is fixed relative to it).
  if (rect.right + reach.scrollX <= 0) return false;
  if (rect.bottom + reach.scrollY <= 0) return false;
  for (const seg of reach.segments) {
    if (!seg.clip) continue;
    const box = seg.refBox || rect;
    const c = seg.clip;
    if (!(box.right > c.left && box.left < c.right &&
          box.bottom > c.top && box.top < c.bottom)) return false;
  }
  return true;
}
