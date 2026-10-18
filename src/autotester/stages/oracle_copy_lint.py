"""The copy, branding and timezone lint oracle (MP25).

One job: run the declared `LintRule`s over every screen's visible text and every received mail
body, and report each hit as a `COPY_OR_BRANDING` finding that cites the screen or message and the
rule. The oracle is deterministic and makes no model call, and a finding carries the rule id, a
slug of the screen or message and a count, never the matched text, so another person's data on the
page cannot reach a finding or a file (MPI1).

Rules: a BRAND_TERM is misspelt when a word window is within a small edit distance of it (or differs
only in case or spacing) but is not the term itself; a FORBIDDEN_STRING is a substring; a
DISPLAY_TIMEZONE is breached by every timestamp whose written zone (an offset, `Z`, `UTC+5:30` or
an abbreviation of `schema/lint_rule.py::ZONE_OFFSETS_MIN`) is a different offset. A timestamp with
no written zone, or an abbreviation outside the table, says nothing about its zone and is ignored.
Declared rules come from `<run_dir>/surface_checks.json`; the texts come from the port's
`TextSurface` capability. With either missing the oracle raises, so a run is never reported clean
because nothing was looked at.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from autotester.schema.lint_rule import (
    LintKind,
    LintRule,
    SurfaceDeclarationMissing,
    SurfaceText,
    SurfaceUnavailable,
    TextOrigin,
    TextSurface,
    load_surface_checks,
    zone_key,
)
from autotester.schema.multi_role_enums import FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext
from autotester.stages.leak_evidence import templatise_url

__all__ = ["SurfaceDeclarationMissing", "SurfaceUnavailable", "lint_texts", "run", "run_copy_lint"]

_WORD = re.compile(r"[A-Za-z0-9À-ɏ]+")
_SIGNED = r"[+-]\d{2}(?::?\d{2})?\b"
_STAMP_SECONDS = re.compile(
    rf"(?<![\d:])\d{{1,2}}:\d{{2}}:\d{{2}}(?:\.\d+)?\s?(?P<z>Z\b|{_SIGNED})")
_STAMP_NAMED = re.compile(
    r"(?<![\d:])\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?[AP]M\b)?"
    r"(?:\s?(?P<z>(?:UTC|GMT)[+-]\d{1,2}(?::?\d{2})?|[A-Z]{2,5}\b)|\s(?P<o>[+-]\d{2}:?\d{2}\b))")
_SAFE_SLUG = re.compile(r"[^a-z0-9_-]+")


def _slug(label: str) -> str:
    return _SAFE_SLUG.sub("-", label.lower()).strip("-")[:40] or "item"


def _osa(a: str, b: str) -> int:
    """Edit distance counting an adjacent swap as one edit."""
    rows = [list(range(len(b) + 1))]
    for i, ca in enumerate(a, 1):
        row = [i]
        for j, cb in enumerate(b, 1):
            best = min(rows[-1][j] + 1, row[j - 1] + 1, rows[-1][j - 1] + (ca != cb))
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                best = min(best, rows[-2][j - 2] + 1)
            row.append(best)
        rows.append(row)
    return rows[-1][-1]


def _norm(raw: str) -> str:
    return "".join(_WORD.findall(raw)).casefold()


def _tolerance(term: str) -> int:
    size = len(_norm(term))
    return 0 if size < 5 else 1 if size < 10 else 2


def count_brand_misspellings(text: str, rule: LintRule) -> int:
    """Word windows close to the brand term that are not the term written exactly.

    Exact occurrences are cut out first, so a correct use never combines with its neighbours into
    a near match. Windows of one fewer, equal and one more word than the term are tried.
    """
    term, want, tol = rule.value, _norm(rule.value), _tolerance(rule.value)
    flags = 0 if rule.is_case_sensitive else re.IGNORECASE
    width, hits = len(_WORD.findall(term)) or 1, 0
    for part in re.split(re.escape(term), text, flags=flags):
        words = list(_WORD.finditer(part))
        i = 0
        while i < len(words):
            step = 1
            for size in dict.fromkeys((width, width - 1, width + 1)):
                if size < 1 or i + size > len(words):
                    continue
                near = _norm(part[words[i].start():words[i + size - 1].end()])
                if abs(len(near) - len(want)) <= tol and _osa(near, want) <= tol:
                    hits, step = hits + 1, size
                    break
            i += step
    return hits

def count_forbidden(text: str, rule: LintRule) -> int:
    flags = 0 if rule.is_case_sensitive else re.IGNORECASE
    return len(re.findall(re.escape(rule.value), text, flags))


def foreign_zones(text: str, display: str) -> dict[str, int]:
    """Zone key -> number of timestamps written in a zone other than `display`."""
    shown, found = zone_key(display), {}
    for pattern in (_STAMP_SECONDS, _STAMP_NAMED):
        for match in pattern.finditer(text):
            token = match.group("z") or (match.groupdict().get("o") or "")
            key = zone_key(token) if token else None
            if key is not None and key != shown:
                found[key] = found.get(key, 0) + 1
    return found


def _zone_text(key: str) -> str:
    return f"UTC{key[0]}{key[1:3]}:{key[3:]}"


def _finding(rule: LintRule, src: SurfaceText, phrase: str, count: int, variant: str = "",
             ) -> MultiRoleFinding:
    ident = "|".join((rule.id, src.kind.value, src.label, src.role_id, variant))
    if src.kind is TextOrigin.MAIL:
        template = "/mail/{id}"
    else:
        template = templatise_url(src.url) if src.url else "/"
    steps = [f"login {src.role_id}", f"goto {template}"]
    return MultiRoleFinding(
        finding_id="cl-" + hashlib.sha1(ident.encode("utf-8")).hexdigest()[:12],
        finding_class=FindingClass.COPY_OR_BRANDING, oracle=OracleName.COPY_LINT,
        title=f"{rule.id}: {phrase} on {_slug(src.label)} ({src.kind.value})",
        role=src.role_id, platform_id=src.platform_id, url_template=template, steps=steps,
        count=count)


def _lint_one(rule: LintRule, src: SurfaceText) -> list[MultiRoleFinding]:
    body = src.text
    if rule.kind is LintKind.BRAND_TERM:
        n = count_brand_misspellings(body, rule)
        return [_finding(rule, src, "brand term misspelt", n)] if n else []
    if rule.kind is LintKind.FORBIDDEN_STRING:
        n = count_forbidden(body, rule)
        return [_finding(rule, src, "forbidden string present", n)] if n else []
    shown = _zone_text(zone_key(rule.value) or "+0000")
    return [_finding(rule, src, f"timestamp in {_zone_text(key)}, display zone is {shown}",
                     n, variant=key)
            for key, n in sorted(foreign_zones(body, rule.value).items())]


def lint_texts(rules: list[LintRule], texts: list[SurfaceText]) -> list[MultiRoleFinding]:
    """Every rule over every text; one finding per (rule, source), per zone for timezone rules."""
    return [f for src in texts for rule in rules for f in _lint_one(rule, src)]


def run_copy_lint(context: OracleContext) -> list[MultiRoleFinding]:
    """The oracle entry point named by `schema/oracle_context.py`."""
    rules = load_surface_checks(Path(context.run_dir)).rules
    if not rules:
        raise SurfaceDeclarationMissing("no lint rules declared")
    if not isinstance(context.port, TextSurface):
        raise SurfaceUnavailable("the port cannot read screen text or mail bodies")
    return lint_texts(rules, context.port.surface_texts())

# The name the oracle registry imports. An alias, so each concept has one definition name.
run = run_copy_lint
