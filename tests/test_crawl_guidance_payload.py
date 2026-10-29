"""crawl-guidance Unit 2, pure half (qa/contracts/crawl-guidance.md G1, G3): no network, no clock.

G1: whatever a model returns, the order is a permutation of the code's own list. G3: only a
redacted, text-only payload is built. A gate no test defends is decorative, so the permutation
property is also run against a SABOTAGED range check and must fail there.
"""

from __future__ import annotations

import json
import random
from typing import Any

import pytest

from autotester.schema.crawl_guidance import NextActionRanking
from autotester.schema.screen_graph import ElementRef, ScreenNode
from autotester.stages import explore_guidance_payload as payload

SECRET = "S3cretPlant-91xyz"


def _cands(n: int) -> list[ElementRef]:
    return [ElementRef(role="button", name=f"Control {i}", selector=f"#c{i}") for i in range(n)]


def _fuzz_outputs(rng: random.Random, n: int) -> list[Any]:
    junk: list[Any] = [None, "", "garbage", 7, 3.5, True, [], {}, [[0]], {"ranked": "x"},
                       {"ranked": [None]}, {"ranked": ["0", "1"]}, {"ranked": [0.5]},
                       {"ranked": [True, False]}, {"nope": [0]}, ["a", 1], b"bytes"]
    outs = list(junk)
    for _ in range(400):
        size = rng.choice([0, 1, 2, n, n + 3, 3 * n + 5])
        ints = [rng.choice([-5, -1, 0, n - 1, n, n + 9, 10**12, rng.randrange(-3, n + 4)])
                for _ in range(size)]
        outs += [{"ranked": ints}, NextActionRanking(ranked=ints), ints]
    return outs


def _order(raw: Any, n: int) -> list[int] | None:
    usable = payload.parse_ranking(raw, n)
    return None if usable is None else payload.complete_order(usable, n)


def check_permutation_property(n: int) -> int:
    """For every fuzzed model output: failure (None) or a permutation of range(n). Returns the
    number of outputs that produced an order, so the property cannot pass vacuously."""
    produced = 0
    for raw in _fuzz_outputs(random.Random(1017), n):
        order = _order(raw, n)
        if order is None:
            continue
        produced += 1
        assert sorted(order) == list(range(n)), (raw, order)
        items = _cands(n)
        assert sorted(e.selector for e in payload.reorder(items, order)) == sorted(
            e.selector for e in items)
    return produced


@pytest.mark.parametrize("n", [2, 3, 7, 40])
def test_any_model_output_yields_a_permutation_or_a_failure(n: int) -> None:
    assert check_permutation_property(n) > 100


def test_sabotaged_range_check_is_caught_by_the_property(monkeypatch: pytest.MonkeyPatch) -> None:
    """G1 verify: let an out-of-range index through and at least one test must fail."""
    monkeypatch.setattr(payload, "clean_indices", lambda ints, n: list(dict.fromkeys(ints)) or None)
    with pytest.raises((AssertionError, IndexError)):
        check_permutation_property(7)


def test_sabotaged_duplicate_check_is_caught_by_the_property(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(payload, "clean_indices",
                        lambda ints, n: [i for i in ints if 0 <= i < n] or None)
    with pytest.raises(AssertionError):
        check_permutation_property(7)


def test_unmentioned_candidates_follow_in_rule_order() -> None:
    assert payload.complete_order([3, 1], 5) == [3, 1, 0, 2, 4]
    assert payload.parse_ranking({"ranked": [9, 2, 2, -1, 0]}, 4) == [2, 0]


def test_empty_and_wrong_shape_answers_are_failures_not_empty_orders() -> None:
    for raw in (None, "text", {}, {"ranked": []}, {"ranked": [99]}, {"ranked": ["1"]}, [True]):
        assert payload.parse_ranking(raw, 5) is None, raw


def test_candidate_hash_tracks_the_set_and_its_order() -> None:
    a, b = _cands(3), _cands(3)
    assert payload.candidate_hash(a) == payload.candidate_hash(b)
    b[1].name = "Control X"
    assert payload.candidate_hash(a) != payload.candidate_hash(b)
    assert payload.candidate_hash(a) != payload.candidate_hash(list(reversed(a)))


def _node() -> ScreenNode:
    return ScreenNode(id="node_1", crawl_id="c", project="demo", url_template="/people?page=2#x",
                      url_example="https://app.test/people?page=2&token=ABC123", signature="s",
                      title="People", depth=2)


def _payload_text() -> str:
    cands = [
        ElementRef(role="link", name="Reports", selector="a.r", href="/reports?year=2026&q=z#top"),
        ElementRef(role="link", name="Jane Doe 9th grade", selector="a.j", href="/people/77",
                   in_row=True),
        ElementRef(role="textbox", name="Search", selector="input.s", tag="input", type="password"),
        ElementRef(role="button", name=f"Export {SECRET}", selector="b.e", tag="button"),
    ]
    scrub = lambda text: (text or "").replace(SECRET, "[REDACTED]")  # noqa: E731
    body = payload.build_payload(_node(), cands, ["/", "/a?x=1"], scrub)
    return json.dumps(body)


def test_payload_is_text_only_and_leaves_no_query_row_name_or_secret() -> None:
    text = _payload_text()
    for forbidden in ("token=ABC123", "page=2", "year=2026", "q=z", "#top", "Jane Doe",
                      "/people/77", SECRET, "app.test", "x=1"):
        assert forbidden not in text, forbidden
    assert "<row item>" in text and "[REDACTED]" in text and "/reports" in text


def test_payload_never_carries_values_cookies_or_images() -> None:
    keys = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            keys.update(obj)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(json.loads(_payload_text()))
    assert not keys & {"value", "cookie", "cookies", "header", "headers", "token", "image",
                       "screenshot", "url_example", "query"}


def test_payload_caps_names_known_screens_and_indexes_candidates() -> None:
    cands = [ElementRef(role="button", name="N" * 500, selector=f"#b{i}") for i in range(3)]
    body = payload.build_payload(_node(), cands, [f"/s{i}" for i in range(500)], lambda t: t)
    assert [c["i"] for c in body["controls"]] == [0, 1, 2]
    assert all(len(c["name"]) <= payload.NAME_CHARS for c in body["controls"])
    assert len(body["known_screens"]) == payload.KNOWN_CAP


def test_href_path_keeps_only_the_path() -> None:
    assert payload.href_path("https://evil.test/a/b?x=1#f") == "/a/b"
    assert payload.href_path("/a?b=c") == "/a" and payload.href_path(None) == ""
