"""`core.urls.url_template` — the shared identity input for both Track A's
ingest (`Screen.url_pattern`) and Track B's screen identity (`ScreenNode`).
"""

from __future__ import annotations

from autotester.core.urls import absolute_url, screen_url_pattern, url_template


def test_numeric_segment_is_templated() -> None:
    assert url_template("/students/1/") == "/students/{id}"
    assert url_template("/students/42") == "/students/{id}"


def test_uuid_and_ulid_segments_are_templated() -> None:
    assert url_template("/erp/batch/01J8Z1Q2R3S4T5V6W7X8Y9ZABC/edit") == "/erp/batch/{id}/edit"
    assert url_template("/items/550e8400-e29b-41d4-a716-446655440000") == "/items/{id}"


def test_hex_id_segment_is_templated() -> None:
    assert url_template("/objects/deadbeefcafef00d1234") == "/objects/{id}"


def test_date_segment_is_templated() -> None:
    assert url_template("/erp/reports/2026-09") == "/erp/reports/{date}"
    assert url_template("/erp/reports/2026-09-07") == "/erp/reports/{date}"


def test_non_id_shaped_segment_is_left_alone() -> None:
    assert url_template("/erp/p/me") == "/erp/p/me"


def test_query_and_fragment_are_stripped() -> None:
    assert url_template("/erp/students/123?tab=2#x") == "/erp/students/{id}"


def test_full_url_with_host_kept_by_default() -> None:
    result = url_template("https://www.vidysea.com/erp/students/123?tab=2#x")
    assert result == "www.vidysea.com/erp/students/{id}"


def test_keep_host_false_returns_path_only() -> None:
    result = url_template("https://www.vidysea.com/erp/students/123", keep_host=False)
    assert result == "/erp/students/{id}"


def test_root_path_stays_root() -> None:
    assert url_template("https://app.test/", keep_host=False) == "/"
    assert url_template("https://app.test", keep_host=False) == "/"


def test_repeated_slashes_are_collapsed() -> None:
    assert url_template("/erp//students//1", keep_host=False) == "/erp/students/{id}"


def test_idempotent_on_path_only_output() -> None:
    once = url_template("/students/1/", keep_host=False)
    twice = url_template(once, keep_host=False)
    assert once == twice == "/students/{id}"


# -- AT-287: one canonical stored shape, because no parser can infer host-ness --

def test_a_path_shaped_pattern_survives_re_templating_unchanged() -> None:
    """The invariant coverage actually relies on. `Screen.url_pattern` is stored
    host-LESS by every producer, and re-templating such a value is a no-op — so
    a stored pattern and a freshly observed URL reduce to the same identity."""
    for url in ("https://demo.test/students/42", "https://demo.test/", "/reports/new",
                "http://localhost/students/1"):
        stored = url_template(url, keep_host=False)
        assert url_template(stored, keep_host=False) == stored, url
        assert stored.startswith("/"), stored


def test_a_video_pattern_and_a_fresh_url_agree_on_the_path() -> None:
    """What ingest stores and what a run observes must reduce to the same thing,
    or the screen is invisible to coverage (AT-287)."""
    stored = url_template("https://demo.test/students/42", keep_host=False)
    observed = url_template("https://demo.test/students/99", keep_host=False)

    assert stored == observed == "/students/{id}"


def test_host_ful_output_is_documented_as_NOT_re_templatable() -> None:
    """Pinned deliberately, because this asymmetry is the whole reason
    url_pattern is stored host-less. `urlsplit("demo.test/x")` has no "//", so
    the host becomes a path segment. A test that hid this would let a future
    producer store host-ful again and re-introduce AT-287."""
    host_ful = url_template("https://demo.test/students/42")

    assert host_ful == "demo.test/students/{id}"
    assert url_template(host_ful, keep_host=False) == "/demo.test/students/{id}"


def test_no_path_segment_is_ever_swallowed() -> None:
    """The first fix for AT-287 guessed host-ness from the string, which silently
    DELETED a dotted first segment: "settings.json" became "/" and "v1.2/foo"
    became "/foo". `settings.json` and `example.com` are the same shape, so the
    guess is unwinnable in principle — hence one canonical shape instead."""
    assert url_template("settings.json", keep_host=False) == "/settings.json"
    assert url_template("sitemap.xml", keep_host=False) == "/sitemap.xml"
    assert url_template("v1.2/foo", keep_host=False) == "/v1.2/foo"
    assert url_template("reports/new", keep_host=False) == "/reports/new"


# -- AT-299b: absolute_url must not eat the first segment of a hostless input --

def test_absolute_url_leaves_a_genuine_hostless_relative_path_alone() -> None:
    """Regression: `absolute_url` used to prepend `https://` unconditionally,
    so `urlsplit` read the first segment as a host and `keep_host=False`
    silently deleted it -- "erp/trainers" collapsed to "/trainers", losing
    "erp" entirely (cycle-2 code, without `absolute_url`, produced the correct
    "/erp/trainers"). Neither "erp" nor "students" carries a domain dot or a
    port colon, so nothing here should be read as a host."""
    assert absolute_url("erp/trainers") == "erp/trainers"
    assert url_template(absolute_url("erp/trainers"), keep_host=False) == "/erp/trainers"

    assert absolute_url("students/1") == "students/1"
    assert url_template(absolute_url("students/1"), keep_host=False) == "/students/{id}"


def test_absolute_url_still_restores_scheme_for_a_dotted_or_ported_host() -> None:
    """The address-bar shapes AT-294 actually fixed must keep working: a
    domain-dotted or port-colon'd first segment is still the host, and
    `keep_host=False` still drops it."""
    assert absolute_url("vidysea.com/erp/trainers") == "https://vidysea.com/erp/trainers"
    assert url_template(
        absolute_url("vidysea.com/erp/trainers"), keep_host=False
    ) == "/erp/trainers"

    assert absolute_url("localhost:3000/students/1") == "https://localhost:3000/students/1"
    assert url_template(
        absolute_url("localhost:3000/students/1"), keep_host=False
    ) == "/students/{id}"


def test_absolute_url_passes_through_scheme_ful_and_absolute_path_input() -> None:
    """Unaffected shapes: a real scheme, a scheme-relative `//host/...`, and an
    already-absolute path are all returned unchanged by `absolute_url` itself."""
    assert absolute_url("https://vidysea.com/erp/trainers") == "https://vidysea.com/erp/trainers"
    assert absolute_url("//host/x") == "//host/x"
    assert absolute_url("/erp/trainers") == "/erp/trainers"


def test_a_non_url_transcription_no_longer_falsely_claims_the_site_root() -> None:
    """AT-299b: prose the model returns (e.g. "Sign in page") used to collapse
    to "/", a false claim that the site ROOT is covered. It must not become a
    host either, so it now reduces to the same harmless single path segment
    `url_template` alone already produced pre-AT-294 -- junk, but not a false
    positive on the root."""
    result = url_template(absolute_url("Sign in page"), keep_host=False)
    assert result != "/"
    assert result == "/Sign in page"


# -- AT-299b cycle 2: the caller boundary must not claim a false root either --

def test_screen_url_pattern_reports_none_for_a_bare_ambiguous_token() -> None:
    """The checker's FAIL: `url_template(absolute_url(x), keep_host=False)`, which
    every one of the three callers uses, still turned a schemeless, slash-free,
    dotted token into "/" -- indistinguishable BY SHAPE from a real bare host's
    root (AT-287's own "settings.json vs example.com" ambiguity). `None` is the
    honest "no pattern is knowable" outcome (I7), not a false claim on the root."""
    for bare in ("file.html", "sitemap.xml", "report.pdf", "robots.txt", "a.b", "example.com"):
        assert screen_url_pattern(bare) is None, bare


def test_screen_url_pattern_keeps_root_when_the_raw_string_actually_said_so() -> None:
    """Never suppresses a GENUINE root: an explicit trailing slash after a
    promoted host, an already-absolute path, and a real scheme all keep "/"."""
    assert screen_url_pattern("example.com/") == "/"
    assert screen_url_pattern("/") == "/"
    assert screen_url_pattern("https://app.test") == "/"
    assert screen_url_pattern("https://app.test/") == "/"


def test_screen_url_pattern_is_unaffected_when_a_real_path_survives() -> None:
    """Every AT-299b cycle-1 shape (a real path templates to something other
    than "/") is untouched by the None guard -- it only fires when the
    templated result IS "/"."""
    assert screen_url_pattern("erp/trainers") == "/erp/trainers"
    assert screen_url_pattern("students/1") == "/students/{id}"
    assert screen_url_pattern("vidysea.com/erp/trainers") == "/erp/trainers"
    assert screen_url_pattern("localhost:3000/students/1") == "/students/{id}"
    assert screen_url_pattern("Sign in page") == "/Sign in page"


def test_screen_url_pattern_is_none_for_no_input() -> None:
    assert screen_url_pattern(None) is None
    assert screen_url_pattern("") is None


# -- AT-334: a directory index reached by "/" and by "/index.html" is one screen --
# The fold is opt-in (`fold_index=True`, default False) -- see
# test_fold_index_defaults_to_off_... below for why.

def test_trailing_index_html_folds_to_root() -> None:
    assert url_template("/index.html", keep_host=False, fold_index=True) == "/"


def test_trailing_index_htm_also_folds_to_root() -> None:
    assert url_template("/index.htm", keep_host=False, fold_index=True) == "/"


def test_root_and_index_html_produce_the_identical_template() -> None:
    """The exact AT-334 measurement: a browser crawl reaching the same page via
    "/" and via "/index.html" must land on one `url_template`, or explore's
    node identity (a pure function of `(url_template, signature)`) counts one
    screen twice."""
    assert url_template("/", keep_host=False) == url_template(
        "/index.html", keep_host=False, fold_index=True
    )


def test_nested_trailing_index_html_folds_to_the_directory() -> None:
    """Folds to whatever the directory form ITSELF already normalises to --
    `/docs/` already drops its trailing slash under this function's own
    documented rule, so `/docs/index.html` must land on that same `/docs`,
    not on a third, unvisited `/docs/` shape. Landing on `/docs/` instead
    would break the idempotence this module already promises: re-templating
    `/docs/` collapses to `/docs`, so `/docs/` could never be a stable output
    of this function in the first place."""
    assert url_template("/docs/index.html", keep_host=False, fold_index=True) == "/docs"
    assert (
        url_template("/docs/index.html", keep_host=False, fold_index=True)
        == url_template("/docs/", keep_host=False)
        == url_template("/docs", keep_host=False)
    )


def test_index_html_fold_survives_query_and_fragment() -> None:
    assert url_template("/index.html?tab=2#x", keep_host=False, fold_index=True) == "/"


def test_index_html_fold_works_with_host_kept() -> None:
    assert url_template("https://app.test/docs/index.html", fold_index=True) == "app.test/docs"


def test_bare_index_html_with_host_kept_folds_to_host_root() -> None:
    assert url_template("https://app.test/index.html", fold_index=True) == "app.test/"


def test_fold_index_defaults_to_off_so_migrate_url_patterns_repair_is_unaffected() -> None:
    """`scripts/migrate_url_patterns.py::repair` calls `url_template` directly
    and its own tests pin `/index.html` as an ordinary, unchanged remainder
    once a real declared host has been stripped off -- that script sits behind
    its own separate, unanswered gate (qa/gates/t135-url-pattern-data-migration.md)
    and AT-334 does not authorize touching it. The fold must therefore be
    opt-in, not the default, so every caller that never asked for it (like
    `repair`) keeps behaving exactly as before with zero code changes."""
    assert url_template("/index.html", keep_host=False) == "/index.html"
    assert url_template("/docs/index.html", keep_host=False) == "/docs/index.html"


# -- AT-334: what must NOT fold, pinned so the fold cannot over-broaden --
# Called WITH fold_index=True throughout -- the guard must hold even when
# folding is actively requested, not merely when it is off by default.

def test_myindex_html_is_not_folded() -> None:
    """Only the exact segment `index.html`/`index.htm` folds -- a filename that
    merely ends with it is an ordinary, distinct page."""
    assert url_template("/myindex.html", keep_host=False, fold_index=True) == "/myindex.html"


def test_index_html_bak_is_not_folded() -> None:
    assert (
        url_template("/index.html.bak", keep_host=False, fold_index=True) == "/index.html.bak"
    )


def test_index_php_is_not_folded() -> None:
    assert url_template("/index.php", keep_host=False, fold_index=True) == "/index.php"


def test_index_html_fold_is_case_sensitive() -> None:
    """Case-sensitive on purpose: most web servers (and every Linux one) treat
    paths as case-sensitive, so `/Index.html` is not provably the same
    resource as `/index.html` -- folding it too would be a guess this module's
    own history (AT-287, AT-299b) already warns against making."""
    assert url_template("/Index.html", keep_host=False, fold_index=True) == "/Index.html"
    assert url_template("/INDEX.HTML", keep_host=False, fold_index=True) == "/INDEX.HTML"


# -- AT-334: the boundary callers that DO opt in --

def test_screen_url_pattern_folds_trailing_index_html_like_node_identity_does() -> None:
    """`screen_url_pattern` is the ingest/product_map/login-case boundary X15
    requires to agree with `ScreenNode.url_template` -- both must fold, or a
    screen learned via a video's `/index.html` frame never matches a crawl
    observing the same page at `/`."""
    assert screen_url_pattern("/index.html") == "/"
    assert screen_url_pattern("/docs/index.html") == "/docs"
    assert screen_url_pattern("erp/index.html") == "/erp"
