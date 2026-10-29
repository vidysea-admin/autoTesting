"""Follow-ups F6-F9 of the checker verdict `run-error-text-evidence` (cycle 1, low findings).

F6  a `<br>` or block-level separator yields a space, so a typed multi-line value echoed over
    `<br>`/`<p>` is still blanked and ordinary messages do not run words together.
F7  a very long typed value (60,000+ chars made `new RegExp` throw and the read return nothing)
    is blanked and does not stop the other message text from being recorded.
F8  non-ASCII echoes are blanked across Unicode case/normalisation forms (NFC vs NFD, ss vs
    sharp s, Kelvin sign, full-width forms), not only simple case folding.
F9  a `.env` secret echoed in another case is masked on the Python side (see also
    `test_redact_case_insensitive.py`).
H1  a typed value that itself holds U+E000 (private use) is still blanked.
H2  pretty-printed newlines (and their indentation) between blocks are not a real space.
H3  a hostile page (50k `<br>`/`<p>`, a 1M+ char message) cannot stall the read: the scan is
    capped and an excerpt over the cap is masked whole, never leaked.

The real-page tests reuse the Chromium fixture of `test_assertion_error_text.py`. A typed value
must never appear in the excerpt, so every case asserts the value (or its tell-tale part) is gone.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from test_assertion_error_text import _expect_dashboard, _rows, real_page, scrape  # noqa: F401
from test_execute import make_project, session_with_fake_page

from autotester.browser.secrets import SecretStore

# -- F6: separators -------------------------------------------------------------------


def test_f6_br_between_lines_of_a_typed_textarea_value_is_blanked(real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<textarea>line1
line2xx</textarea>
<div role=alert>Rejected: line1<br>line2xx is not allowed</div>""")

    assert "Rejected" in joined and "not allowed" in joined
    assert "line1" not in joined and "line2xx" not in joined


def test_f6_block_elements_between_words_of_a_typed_value_are_blanked(
        real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="Alice 99">
<div role=alert>No user <p>Alice</p><p>99</p> found</div>""")

    assert "No user" in joined and "found" in joined
    assert "Alice" not in joined and "99" not in joined


def test_f6_separators_do_not_run_ordinary_words_together(real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<div role=alert>First line<br>Second line
<ul><li>Item one</li><li>Item two</li></ul><div>Tail</div></div>""")

    assert "First line Second line" in joined
    assert "Item one Item two" in joined and "Item two Tail" in joined


def test_f6_inline_markup_still_joins_text_nodes(real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="Alice99">
<div role=alert>Taken: <b>Al</b>ice<i>99</i> sorry</div>""")

    assert "Taken" in joined and "sorry" in joined and "ice" not in joined


SPLITS = [
    "<p>Alice</p><p>99</p>",
    "Alice<br>99",
    "<table><tr><td>Alice</td><td>99</td></tr></table>",
    "<div>Alice</div><div>99</div>",
]


@pytest.mark.parametrize("echo", SPLITS)
def test_f6b_unspaced_typed_value_split_across_blocks_is_blanked(
        real_page, echo) -> None:  # noqa: F811
    joined = scrape(real_page, f"""<input value="Alice99">
<div role=alert>No user {echo} found</div>""")

    assert joined == "No user [input] found"


def test_f6b_spaced_and_unspaced_echoes_in_one_message_are_both_blanked(
        real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="Alice99"><input value="Bob 77">
<div role=alert>Taken: <p>Alice</p><p>99</p> and <p>Bob</p><p>77</p> and Alice99 ok</div>""")

    assert joined == "Taken: [input] and [input] and [input] ok"


def test_f6b_real_whitespace_next_to_a_separator_is_not_removed(real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="Alice99">
<div role=alert>Seen <p>Alice </p><p>99</p> here</div>""")

    assert joined == "Seen Alice 99 here"  # a genuine space: not the typed value


def test_h1_typed_value_holding_a_private_use_char_is_still_blanked(
        real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="Alice\ue00099">
<div role=alert>No user Alice\ue00099 found</div>""")

    assert joined == "No user [input] found"


@pytest.mark.parametrize("echo", [
    "<p>Alice</p>\n<p>99</p>",
    "<div>\n    Alice\n  </div>\n  <div>\n    99\n  </div>",
    "<ul>\n<li>Alice</li>\n<li>99</li>\n</ul>",
    "Alice\n<br>\n99",
])
def test_h2_pretty_printed_newlines_between_blocks_are_not_a_real_space(
        real_page, echo) -> None:  # noqa: F811
    joined = scrape(real_page, f"""<input value="Alice99">
<div role=alert>No user {echo} found</div>""")

    assert joined == "No user [input] found"


def test_h2_a_space_without_a_newline_next_to_a_block_is_still_real(real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="Alice99">
<div role=alert>Seen <p>Alice </p>\n<p>99</p> here</div>""")

    assert joined == "Seen Alice 99 here"


# -- H3: a hostile page cannot stall the read -----------------------------------------------

BOUND_S = 20  # generous: the capped scan takes well under a second; the old loop took > 50 s


def _timed_scrape(page, html: str) -> tuple[str, float]:
    started = time.monotonic()
    joined = scrape(page, html)
    return joined, time.monotonic() - started


@pytest.mark.parametrize("unit", ["x<br>", "<p>x</p>"])
def test_h3_fifty_thousand_separators_are_capped_and_masked_not_leaked(
        real_page, unit) -> None:  # noqa: F811
    joined, took = _timed_scrape(real_page, f"""<input value="Alice99">
<div role=alert>Hi Alice99 {unit * 50_000} Alice<br>99</div><div role=alert>Other alert</div>""")

    assert took < BOUND_S
    assert "Alice" not in joined and "99" not in joined
    assert "masked" in joined  # the over-cap excerpt is replaced whole


def test_h3_below_the_cap_a_long_message_is_still_scanned_and_blanked(
        real_page) -> None:  # noqa: F811
    joined, took = _timed_scrape(real_page, f"""<input value="Alice99">
<div role=alert>Alice<br>99 end{"<br>a" * 3_000}</div>""")

    assert took < BOUND_S  # the output is cut to 200 chars, so the typed part comes first
    assert joined.startswith("[input] end a a a") and "masked" not in joined


def test_h3_many_alerts_share_one_run_budget(real_page) -> None:  # noqa: F811
    alerts = "".join(f"<div role=alert>Alice99 {'x<br>' * 3_000}</div>" for _ in range(30))
    joined, took = _timed_scrape(real_page, f'<input value="Alice99">{alerts}')

    assert took < BOUND_S
    assert "Alice" not in joined and "99" not in joined


def test_h3_an_oversized_message_is_masked_whole(real_page) -> None:  # noqa: F811
    joined, took = _timed_scrape(real_page, f"""<input value="Zq7secret">
<div role=alert>{"filler " * 200_000} Zq7secret</div>""")

    assert took < BOUND_S
    assert "Zq7" not in joined and "filler" not in joined and "masked" in joined


# -- F7: long typed values -------------------------------------------------------------


def test_f7_very_long_typed_value_is_blanked_and_the_message_survives(
        real_page) -> None:  # noqa: F811
    long = "Zq7" * 40_000  # 120,000 chars: new RegExp(...) threw "Invalid regular expression"
    joined = scrape(real_page, f"""<textarea>{long}</textarea>
<div role=alert>Upload rejected. {long} Please retry.</div>
<div role=alert>Second alert stays</div>""")

    assert "Upload rejected" in joined and "Please retry" in joined
    assert "Second alert stays" in joined
    assert "Zq7" not in joined


def test_f7_long_typed_value_not_echoed_does_not_hide_other_alerts(
        real_page) -> None:  # noqa: F811
    long = "Qw9" * 40_000
    joined = scrape(real_page, f"""<textarea>{long}</textarea>
<input value="short-secret-1">
<div role=alert>Server said short-secret-1 is invalid</div>""")

    assert "Server said" in joined and "is invalid" in joined
    assert "short-secret-1" not in joined


# -- F8: Unicode folding ---------------------------------------------------------------

FORMS = [
    ("caf\u00e9-pw", "cafe\u0301-PW"),  # NFC typed, NFD echoed
    ("cafe\u0301-pw", "CAF\u00c9-pw"),  # NFD typed, NFC echoed
    ("Stra\u00dfe99", "STRASSE99"),  # sharp s upper-cases to SS
    ("STRASSE99", "stra\u00dfe99"),
    ("kelvin-pw9", "\u212aelvin-pw9"),  # Kelvin sign vs k
    ("\u212aelvin-pw9", "kelvin-PW9"),
    ("abc123xyz", "\uff41\uff42\uff43\uff11\uff12\uff13xyz"),  # full-width forms
]


@pytest.mark.parametrize(("typed", "echoed"), FORMS)
def test_f8_non_ascii_echo_forms_are_blanked(real_page, typed, echoed) -> None:  # noqa: F811
    joined = scrape(real_page, f"""<input value="{typed}">
<div role=alert>Account {echoed} is locked</div>""")

    assert joined == "Account [input] is locked"


def test_f8_unrelated_text_is_not_blanked(real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="Stra\u00dfe99">
<div role=alert>Account locked, try again later.</div>""")

    assert joined == "Account locked, try again later."


def test_f8_adjacent_echoes_keep_separate_markers_and_nested_values_do_not_re_match(
        real_page) -> None:  # noqa: F811
    joined = scrape(real_page, """<input value="alpha99"><input value="inp">
<div role=alert>Bad alpha99 and ALPHA99 end</div>""")

    # the 3-char value "inp" must not re-match inside the "[input]" markers it sits next to
    assert joined == "Bad [input] and [input] end"


# -- F9: the Python scrubber -----------------------------------------------------------


def test_f9_env_secret_echoed_in_another_case_is_masked_in_the_row(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)
    (tmp_path / ".env").write_text('PATHLYNKS_PASSWORD="pass word 9"' + chr(10), encoding="utf-8")
    session.secrets = SecretStore.load(make_project(), tmp_path / ".env")
    session.page.body_text = "Sign in"
    session.page.evaluate = lambda js: ["Wrong credential PASS WORD 9 for this account"]

    rows = _rows(_expect_dashboard(session))

    assert len(rows) == 1
    assert "pass word 9" not in rows[0].path.lower()  # the mask names the KEY, never the value
    assert "[REDACTED]" in rows[0].path and "for this account" in rows[0].path
