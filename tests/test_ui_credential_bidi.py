"""One question: are bidi OVERRIDES refused outright, rather than folded away?

AT-355. `U+202E` followed by a credential written backwards renders as plain
type in the correct reading order, and the guard could not see it *because* it
stripped the override as a format character -- deleting the one character that
causes the leak, then comparing a string that is not the credential:

    fold("ZEBRA_QUILT_APIKEY_31")     -> zebraquiltapikey31
    fold("\\u202e" + its reverse)      -> 13yekipatliuqarbez

Every earlier fix in this family worked by subtracting more. That operation is
exactly wrong here, so this one refuses instead. Refusing is also the only
answer that stays bounded: a reordering character has no legitimate use in a
project name or a case title, so there is nothing to weigh it against.

Scope is deliberately the two OVERRIDES, and the rest of the bidi family is
deliberately untouched:

  - `U+202D`/`U+202E` force direction character by character regardless of
    content. That is what reverses a pure-ASCII credential.
  - `U+200E`/`U+200F` (LRM/RLM) are ordinary punctuation in Hebrew and Arabic
    text. Refusing them would make the guard reject real input, and
    false-positive rate is a term in this product's north star (AT-078 and
    AT-086 are two prior occasions when this guard made a real project
    uneditable).

Contract: qa/contracts/ui.md U8/U9; threat model pending as U11 (see
qa/gates/at355-guard-shape.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

UPPER_CREDENTIAL = "ZEBRA_QUILT_APIKEY_31"

RLO = "‮"
LRO = "‭"
OVERRIDES = {"right-to-left-override": RLO, "left-to-right-override": LRO}
LEGITIMATE_BIDI = {
    "right-to-left-mark": "‏",
    "left-to-right-mark": "‎",
    "right-to-left-isolate": "⁧",
    "pop-directional-isolate": "⁩",
}


@pytest.fixture
def scratch_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _seed(client: TestClient, scratch_root: Path, slug: str) -> None:
    (scratch_root / ".env").write_text(
        f"DEMO_PASSWORD={UPPER_CREDENTIAL}\n", encoding="utf-8")
    client.post("/onboard", data={
        "slug": slug, "name": slug.title(), "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    client.post(f"/projects/{slug}/secrets", data={
        "key": "DEMO_PASSWORD", "domains": "demo.test", "mask_in_screenshot": "on",
    })


@pytest.mark.parametrize("label", sorted(OVERRIDES))
def test_a_bidi_override_is_refused_at_onboarding(
    client: TestClient, scratch_root: Path, label: str
) -> None:
    """Refused for CONTAINING the override, not for matching a credential --
    which is why the name here is ordinary text with one override in it."""
    _seed(client, scratch_root, "seedbidi")

    response = client.post("/onboard", data={
        "slug": "leaky-" + label, "name": f"Quarterly {OVERRIDES[label]}report",
        "base_url": "https://demo.test", "allowed_domains": "demo.test",
    }, follow_redirects=False)

    assert response.status_code == 400, f"{label} was accepted"
    assert not (scratch_root / "projects" / ("leaky-" + label)).exists()


def test_the_at355_spelling_is_refused_at_onboarding(
    client: TestClient, scratch_root: Path
) -> None:
    """The exact spelling a checker used to render the credential on the home
    index in plain type, 21 glyphs, in the correct reading order."""
    _seed(client, scratch_root, "seedat355")

    response = client.post("/onboard", data={
        "slug": "leaky-at355", "name": RLO + UPPER_CREDENTIAL[::-1],
        "base_url": "https://demo.test", "allowed_domains": "demo.test",
    }, follow_redirects=False)

    assert response.status_code == 400
    assert not (scratch_root / "projects" / "leaky-at355").exists()


def test_the_at355_spelling_is_refused_by_the_case_form(
    client: TestClient, scratch_root: Path
) -> None:
    """The second door: a checker found 7 `\\u202e` escapes in git-tracked
    `cases.jsonl`, with the Cases page rendering the credential in the title."""
    _seed(client, scratch_root, "demo")
    spelled = RLO + UPPER_CREDENTIAL[::-1]

    for field in ("title", "step_value", "step_expected"):
        data = {
            "title": "Log in", "case_class": "happy",
            "step_action": ["fill"], "step_target": ["#q"],
            "step_value": ["x"], "step_expected": [""],
        }
        data[field] = spelled if field == "title" else [spelled]
        response = client.post("/projects/demo/cases", data=data,
                               follow_redirects=False)
        assert response.status_code == 400, f"override via {field} was accepted"

    assert ProjectStore("demo", scratch_root).list_cases() == []


def test_the_refusal_names_the_override_rather_than_claiming_a_credential(
    client: TestClient, scratch_root: Path
) -> None:
    """The message has to be true. Text containing an override is refused even
    when it holds no credential at all, so a message saying "this looks like a
    credential" would send the user hunting for a secret that is not there --
    the same false-diagnosis problem as the "split across" message in AT-339."""
    _seed(client, scratch_root, "seedmsg")

    response = client.post("/onboard", data={
        "slug": "leaky-msg", "name": f"Totally {RLO}innocent",
        "base_url": "https://demo.test", "allowed_domains": "demo.test",
    }, follow_redirects=False)

    assert response.status_code == 400
    assert "direction" in response.text.lower()
    assert "looks like it contains a real credential" not in response.text


@pytest.mark.parametrize("label", sorted(LEGITIMATE_BIDI))
def test_ordinary_bidi_punctuation_is_still_accepted(
    client: TestClient, scratch_root: Path, label: str
) -> None:
    """The bound. LRM/RLM and the isolates are ordinary punctuation in Hebrew
    and Arabic text, and none of them reverses a pure-ASCII run. Refusing them
    would cost real input for no security gain."""
    _seed(client, scratch_root, "seedok")

    response = client.post("/onboard", data={
        "slug": "ok-" + label, "name": f"עברית{LEGITIMATE_BIDI[label]} report",
        "base_url": "https://demo.test", "allowed_domains": "demo.test",
    }, follow_redirects=False)

    assert response.status_code in (200, 303), f"{label}: {response.text[:200]}"


def test_a_declared_placeholder_combined_with_an_override_is_still_refused(
    client: TestClient, scratch_root: Path
) -> None:
    """AT-360: the ORDERING property. A value holding a declared
    `{{SECRET:KEY}}` placeholder takes the placeholder early return in
    `_refuse_unsafe_value`, so if the override check ran after that return the
    value would be accepted and stored with a reordering character in it. The
    check must run before the placeholder branch; none of the tests above feed
    a placeholder, so none of them can see it move."""
    _seed(client, scratch_root, "demo")
    placeholder = "{{SECRET:DEMO_PASSWORD}}"

    for field in ("title", "step_value", "step_expected"):
        data = {
            "title": "Log in", "case_class": "happy",
            "step_action": ["fill"], "step_target": ["#q"],
            "step_value": ["x"], "step_expected": [""],
        }
        mixed = f"{placeholder}{RLO}{placeholder[::-1]}"
        data[field] = mixed if field == "title" else [mixed]
        response = client.post("/projects/demo/cases", data=data,
                               follow_redirects=False)
        assert response.status_code == 400, (
            f"placeholder + override via {field} was accepted")
        assert "direction" in response.text.lower()

    assert ProjectStore("demo", scratch_root).list_cases() == []
