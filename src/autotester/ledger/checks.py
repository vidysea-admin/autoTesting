"""Design rules over the project's RECORDS, as opposed to its source files.

`doctor` enforces two different kinds of rule and they were living in one module.
The rules in `doctor.py` read `src/` and `tests/` and ask whether the code stayed
readable. The rules here read `docs/FEATURES.jsonl` and `qa/` and ask whether the
project's account of itself stayed true — whether a closed task has a ledger row,
whether an issue a handshake artifact names still exists, whether a PASSed unit's
issue is still open.

Split out under AT-506: three consecutive units (AT-496, AT-500, AT-504) grew
`doctor.py` from 264 to 287 lines against C2's 300-line cap, all three of them in
this half of the file, and `doctor` itself would have stayed silent until 301.
Nothing here changed behaviour — the split is the whole change.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from autotester.core.paths import RepoDocs
from autotester.doctor import Violation

ISSUE_ID = r"AT-\d+[a-z]?"
r"""One issue id, in one place, for every regex below.

The letter suffix is not decoration: when two checkers file the same defect, the
second row takes one (AT-293's convention — AT-297b, AT-298b and AT-299b are live
rows). `\bAT-\d+\b` matches NOTHING inside `AT-297b`, so reading an id without this
made every suffixed row invisible to the whole check (AT-500)."""

_MARKER_LEAD = re.compile(r"^[\s>#*_-]*")
"""Markdown decoration before a marker, which is still the marker."""


def _is_marker_line(line: str, marker: str) -> bool:
    """Does this line MAKE the claim, or merely talk about lines that do (AT-504)?

    `marker in line` could not tell the difference, so a manifest documenting the
    guard counted itself, its verdict counted too, and the count compounded without
    bound as more documents discussed it. Measured over the live tree: decoration is
    common and load-bearing — `**ISSUES-WRITTEN:**` and `## ISSUES-WRITTEN:` are both
    real, and requiring a bare prefix would have silently dropped 12 true claims. A
    backtick is the thing that marks prose, so it is deliberately not stripped.
    """
    return _MARKER_LEAD.sub("", line).startswith(marker.strip("*"))


_NEW_FIELD = re.compile(r"^[\s>#*_-]*[A-Z][A-Z -]*(\([^)]*\))?\s*:")
"""An ALL-CAPS label ending in a colon — the next field of a verdict block, not a
continuation of this one.

**The label may carry a parenthetical** (AT-511): `FAILURES (if any):` is in every
verdict here, and `**ISSUES KEPT OPEN (claimed fixed, not fixed):**` and
`**ISSUES CLOSED (open → fixed):**` are live in at097's and at176's. Without that,
each was read as a continuation and its ids misattributed to `ISSUES-WRITTEN` — 6 ids
across 2 verdicts.

**The label contains no DIGITS, and that is what keeps the rule safe.** `AT-036
(filed in the previous unit): …` is a list item, not a field. A rule that accepted any
parenthetical before a colon matched 167 live lines and would have ended blocks early,
re-creating the very misses AT-509 had just fixed. Measured with the digit rule in
place: 6 ids drop, 0 are added."""


def _marker_lines(body: str, marker: str) -> list[str]:
    """Every line of the marker's PARAGRAPH, not just the first one (AT-509).

    The claim wraps. Both checks gated on a single physical line, so an id on the
    continuation was read by neither — invisible, never mis-judged. Measured over the
    live manifests when this was fixed: 14 of them wrap, hiding 30 ids. AT-496
    disclosed it as a known limit and four units inherited that framing untested.

    A markdown paragraph is the right unit for a MANIFEST, because that is how they
    are written: the block ends at a blank line or the next block, and every one of
    the 14 terminates that way. Consuming to the end of the paragraph — rather than a
    fixed number of lines — keeps the rule honest when someone wraps to three lines.

    A VERDICT is not a paragraph, and assuming it was is the first thing this got
    wrong. Its block is a run of labelled fields with no blank line between them, so
    `ISSUES-WRITTEN:` is followed immediately by `EXPLANATION:` and several lines of
    free prose. Walking to the blank line swallowed all of it and reported two ids
    that were merely being discussed — the same false-accusation shape as AT-504,
    reintroduced by the fix for AT-509. Hence `_NEW_FIELD`: an ALL-CAPS label ending
    in a colon starts the next field and ends this one.
    """
    lines = body.splitlines()
    out: list[str] = []
    for n, line in enumerate(lines):
        if not _is_marker_line(line, marker):
            continue
        out.append(line)
        for follow in lines[n + 1:]:
            stripped = follow.lstrip()
            if (not follow.strip() or stripped.startswith("#") or stripped.startswith("```")
                    or _NEW_FIELD.match(follow) or _is_marker_line(follow, marker)):
                break
            out.append(follow)
    return out


_FIXED = re.compile(r"\bfixed\b", re.IGNORECASE)
_NOT_FIXED = re.compile(r"\bnot\b[\w\s-]{0,15}?\bfixed\b", re.IGNORECASE)


def _claims_a_fix(note: str) -> bool:
    """Does this parenthetical claim the unit FIXED the issue (AT-508)?

    It was `"fixed" in note and "not fixed" not in note`, which read `unfixed`,
    `not-fixed`, `not yet fixed` and `prefixed` as fix claims. The direction is what
    made it serious: it accused a manifest that had correctly declared an issue
    unfixed of leaving a stale row — the one case this filter exists to protect —
    and a false accusation costs more than a miss. Live since AT-496; found by a
    fresh engineering review rather than by the four units built on top of it.

    Word boundaries settle `unfixed`/`prefixed` on their own. The negation stays a
    regex so it also catches a hyphen or a word in between, and its character class
    cannot cross punctuation, so a `not` belonging to another clause
    (`not a duplicate, open -> fixed`) does not swallow the claim. Measured over all
    54 distinct notes in the live manifests: not one changes verdict.
    """
    return bool(_FIXED.search(note)) and not _NOT_FIXED.search(note)


def check_ledger(root: Path) -> list[Violation]:
    """L2/L3: every FEATURES.jsonl row validates; closed high-value tasks have a row."""
    from autotester.ledger.store import check_rows_on_pass, load_events, load_goal_tasks

    docs = RepoDocs(root)
    try:
        events = load_events(docs.features)
    except Exception as exc:  # a doctor reports, it never tracebacks (AT-021)
        return [Violation("ledger-invalid", "docs/FEATURES.jsonl", f"{type(exc).__name__}: {exc}")]
    missing = check_rows_on_pass(events, load_goal_tasks(docs.goal))
    return [Violation("ledger-row-missing", task, "closed high-value task has no live/updated row")
            for task in missing]


def _status_by_id(text: str) -> dict[str, str]:
    """Each row's `id` -> `status`, read as JSON so key order does not matter (AT-571).
    A line that is not a JSON object is skipped: C10 judges rows, not syntax."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and re.fullmatch(ISSUE_ID, str(row.get("id", ""))):
            out[row["id"]] = str(row.get("status", ""))
    return out


def check_qa_issue_rows(root: Path) -> list[Violation]:
    """C10: the ledger never silently loses what the handshake recorded (AT-496).

    Two maker loops share this working tree. A commit built from a stale copy of
    `qa/issues.jsonl` drops rows the other loop appended and reverts statuses it
    flipped, and nothing noticed: AT-494's row vanished after its own PASS, and
    AT-401 went back to `open` a commit after being closed. The manifests and
    verdicts survive in git, so they are what makes the loss visible — an issue a
    handshake artifact names must have a row, and a PASSed unit's issue must not
    still be `open`.
    """
    ledger = root / "qa" / "issues.jsonl"
    if not ledger.exists():
        return []
    status_of = _status_by_id(ledger.read_text(encoding="utf-8", errors="replace"))
    out: list[Violation] = []
    for kind, marker in (("manifests", "**Issues addressed:**"), ("verdicts", "ISSUES-WRITTEN")):
        for path in sorted((root / "qa" / kind).glob("*.md")):
            body = path.read_text(encoding="utf-8", errors="replace")
            named = {i for line in _marker_lines(body, marker)
                     for i in re.findall(rf"\b{ISSUE_ID}\b", line)}
            subject = f"qa/{kind}/{path.name}"
            out += [Violation("ledger-row-lost", subject,
                              f"{issue} is named here but has no row in qa/issues.jsonl")
                    for issue in sorted(named - set(status_of))]
            if kind == "manifests" and _passed(root, path.name):
                # Only an issue this manifest CLAIMS to have fixed — "AT-x (low, open -> fixed)".
                # A line may also name issues it deliberately did NOT fix, and those stay open.
                claimed = {i for line in _marker_lines(body, marker)
                           for i, note in re.findall(rf"\b({ISSUE_ID})\s*\(([^)]*)\)", line)
                           if _claims_a_fix(note)}
                out += [Violation("ledger-row-stale", subject,
                                  f"{issue} is still `open` although this unit PASSed")
                        for issue in sorted(claimed) if status_of.get(issue) == "open"]
    return out


def _passed(root: Path, name: str) -> bool:
    verdict = root / "qa" / "verdicts" / name
    return verdict.exists() and "VERDICT: PASS" in verdict.read_text(encoding="utf-8",
                                                                     errors="replace")


# -- AT-523/AT-524: a CLI -q must never stack on pyproject.toml's own addopts -----

_Q_TOKEN = re.compile(r"^-q+$")
_ADDOPTS_OVERRIDE = re.compile(r"-o\s+addopts=(\S*)")


def _count_q_tokens(text: str) -> int:
    """pytest's `-q` is `argparse`'s `action="count"`: `-q` contributes 1, `-qq`
    contributes 2. Sum every purely-`-q...` short flag among whitespace tokens."""
    return sum(len(tok) - 1 for tok in text.split() if _Q_TOKEN.match(tok))


def _pyproject_addopts_q_count(root: Path) -> int:
    """How many `-q` pytest's OWN config already contributes, read from the live
    `pyproject.toml` rather than assumed — so this guard tracks the config, not a
    copy of today's value baked into the rule (AT-503 found `addopts = "-q"`;
    nothing says it stays that way)."""
    path = root / "pyproject.toml"
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    addopts = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", "")
    return _count_q_tokens(str(addopts))


def _pytest_invocations(cmd: str) -> list[str]:
    """Split a shell command on `&&`/`||`/`|` and keep only the sub-commands that
    actually invoke pytest — the config's `addopts` applies to those, not to
    whatever else a chained command runs afterward."""
    parts = re.split(r"&&|\|\|?", cmd)
    return [p.strip() for p in parts if re.search(r"(?<![\w./-])pytest\b", p)]


def _effective_q_total(subcmd: str, config_q: int) -> int:
    """The total `-q` weight ONE pytest invocation actually runs with.

    An explicit `-o addopts=...` on the CLI REPLACES `pyproject.toml`'s `addopts`
    for that invocation (pytest's own precedence rule) — AT-506's subset runs add
    a bare `-q` on top of `-o addopts=` for exactly this reason, and that is not a
    doubling even though the config file still says `-q`. Without this, a guard
    that merely grepped for `-q` would misfire on every one of those runs."""
    override = _ADDOPTS_OVERRIDE.search(subcmd)
    if override:
        remainder = subcmd[:override.start()] + subcmd[override.end():]
        return _count_q_tokens(override.group(1)) + _count_q_tokens(remainder)
    return config_q + _count_q_tokens(subcmd)


def _q_doubling_violations(cmds: list[tuple[str, str]], config_q: int) -> list[Violation]:
    """Shared scan over `(location, cmd)` pairs — the adapter has one, goal.json
    has one per task, but the rule being checked is identical for both."""
    out = []
    for location, cmd in cmds:
        for sub in _pytest_invocations(cmd):
            if _effective_q_total(sub, config_q) >= 2:
                out.append(Violation("pytest-q-doubled", location,
                                     f"'{sub}' stacks a CLI -q on addopts's own -q; "
                                     "the summary line is suppressed"))
    return out


def check_adapter_pytest_q(root: Path) -> list[Violation]:
    """AT-523: `qa/adapter.json`'s verify command must never stack a CLI `-q` on
    top of `pyproject.toml`'s `addopts` — that reaches `-qq`, which prints no
    `N passed`/`N failed` summary line at all (AT-503)."""
    path = root / "qa" / "adapter.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    cmds = [("qa/adapter.json", entry.get("cmd", ""))
            for entry in data.get("verify", {}).get("commands", [])]
    return _q_doubling_violations(cmds, _pyproject_addopts_q_count(root))


def check_goal_pytest_q(root: Path) -> list[Violation]:
    """AT-524: the same guard, extended to every `done_check.cmd` in
    `.goal/goal.json` — 43 of its ~50 rows carried this exact defect until
    AT-521/AT-522 swept the live file by hand; nothing stopped it coming back."""
    from autotester.ledger.store import load_goal_tasks

    goal_path = root / ".goal" / "goal.json"
    if not goal_path.exists():
        return []
    config_q = _pyproject_addopts_q_count(root)
    cmds = []
    for task in load_goal_tasks(goal_path):
        done_check = task.get("done_check") or {}
        if done_check.get("type") == "cmd":
            cmds.append((f".goal/goal.json:{task.get('id')}", done_check.get("cmd", "")))
    return _q_doubling_violations(cmds, config_q)
