"""T-179b HG-1 gaps (ISS-t179b-hg1-1/-2): invisible-filler click names and 'close account'-style
phrases are refused under READ_ONLY; ALLOW_WRITES behaviour for them is unchanged."""

from __future__ import annotations

import pytest

from autotester.agents import guards
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, WritePolicy
from autotester.schema.flowspec import Step
from autotester.schema.project import Project

FILLERS = ["\u2800", "\u3164", "\u115f", "\u1160", "\uffa0", "\u200b", "\u200d", "\u2060",
           "\ufeff", "\u00ad", "\u200e", " \u2800\u3164 ", "\u2800\u200b\uffa0"]
PHRASES = ["Close account", "Close my account", "Deactivate account", "Terminate account",
           "Cancel account", "Cancel my subscription", "Cancel subscription",
           "Close subscription", "Deactivate subscription", "Terminate subscription",
           "Close membership", "Cancel subscriptions", "Cancel this subscription",
           "Cancel our subscription", "Cancel Premium subscription", "Stop subscription",
           "End membership", "Cancel plan", "Cancel auto-renew", "Turn off auto-renew",
           "Unsubscribe", "Close account settings now"]
SAFE = ["Open menu", "Close", "\u00d7", "Close dialog", "Close menu", "Close account settings",
        "Cancel", "Back", "Plan your trip", "Subscription details", "Membership benefits",
        "Open\u2800menu", "\u2764\ufe0f Like", "Close (\u00d7)", "View plan", "Change plan"]


def _project(policy: WritePolicy) -> Project:
    return Project(slug="demo", name="Demo", base_url="https://app.test",
                   allowed_domains=["app.test"], write_policy=policy)


def _case(target: str) -> Case:
    return Case(project="demo", flow_id="f", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
                title="c", steps=[Step(order=1, action=Action.CLICK, target=target)])


@pytest.mark.parametrize("name", FILLERS)
def test_read_only_refuses_invisible_filler_names(name: str) -> None:
    out = guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY))
    assert out is not None and "unnamed control" in out[1]


@pytest.mark.parametrize("name", [f"\u2800{p}\u3164" for p in PHRASES] + PHRASES)
def test_read_only_refuses_account_closing_phrases(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY))


@pytest.mark.parametrize("name", SAFE)
def test_read_only_still_allows_ordinary_names(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY)) is None


@pytest.mark.parametrize("name", ["\u2800", "\u3164", "\u115f", "\u1160", "\uffa0"])
def test_allow_writes_unchanged_for_fillers(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.ALLOW_WRITES)) is None


@pytest.mark.parametrize("name", ["Cancel subscription", "Close subscription",
                                  "Deactivate subscription", "Terminate subscription"])
def test_allow_writes_still_permits_subscription_phrases(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.ALLOW_WRITES)) is None


@pytest.mark.parametrize("name", ["Deᅟlete", "Del͏ete", "Dele\ufe0fte", "Del᠋ete",
                                  "Saᅟve", "Purch͏ase", "Sub\ufe0fmit", "Deㅤlete",
                                  "Del\u2800ete", "Sa​ve"])
def test_read_only_refuses_invisible_chars_inside_words(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY))


def test_read_only_keeps_real_word_boundaries() -> None:
    project = _project(WritePolicy.READ_ONLY)
    assert guards.write_policy_refusal(_case("Open\u2800menu"), project) is None


def test_is_destructive_reads_deny_list_at_every_policy() -> None:
    """Intended: 'Cancel membership' sorts last in the ALLOW_WRITES crawl too (safe direction)."""
    from autotester.schema.screen_graph import ElementRef
    from autotester.stages.explore_safety import is_destructive, policy_for
    el = ElementRef(role="button", name="Cancel membership", selector="#c")
    assert is_destructive(el, policy_for(_project(WritePolicy.ALLOW_WRITES)))


# Cycle 2 (N1): a join-meaning invisible inside a word mixed with a gap-meaning blank between
# words. The first six were refused at base c4d48ad1 and must never be allowed.
MIXED = ["Pur\u200bchase\u2800now", "De\u200blete\u2800item", "Sub\u200bmit\u2800form",
         "Sa\u200bve\u2800draft", "Pa\u200by\u2800now", "Unsub\u200bscribe\u2800now",
         "De\u034flete\u2800item", "Can\u034fcel\u2800plan", "Cancel\u2800subscri\u034fption",
         "Sa\u034fve\u2800draft", "Sub\ufe0fmit\u3164form", "Cancel\u3164member\u200bship",
         "Del\u2800ete\u200bitem", "De\u200blete\u200bitem", "Del\u2800ete\u2800item",
         "De\u200blete\u200bi\u200btem", "Can\u200bcel\u3164sub\u200bscrip\u2800tion"]


@pytest.mark.parametrize("name", MIXED)
def test_read_only_refuses_mixed_join_and_gap_invisibles(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY))


@pytest.mark.parametrize("name", ["Cancel: subscription", "Cancel, subscription",
                                  "Cancel\u2014subscription", "Cancel (subscription)",
                                  "Cancel 'subscription'", "Cancel \u201cplan\u201d",
                                  "Cancel my current premium subscription",
                                  "Cancel your Premium Plus subscription",
                                  "\u0421ancel plan", "\u0421LOSE ACCOUNT"])
def test_read_only_refuses_punctuated_wide_and_capital_lookalike_phrases(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.READ_ONLY))


def test_read_only_refuses_names_hiding_too_many_invisible_runs() -> None:
    out = guards.write_policy_refusal(_case("O\u200bp\u200be\u200bn m\u200be\u200bnu"),
                                      _project(WritePolicy.READ_ONLY))
    assert out is not None and "too many places" in out[1]


@pytest.mark.parametrize("name", [*MIXED[:6], "\u2800", "Open\u2800menu"])
def test_allow_writes_unchanged_for_mixed_invisibles(name: str) -> None:
    assert guards.write_policy_refusal(_case(name), _project(WritePolicy.ALLOW_WRITES)) is None


CORPUS_PHRASES = ["Delete item", "Purchase now", "Submit form", "Save draft", "Pay now",
                  "Unsubscribe now", "Cancel subscription", "Cancel plan", "Close account",
                  "Remove user", "Cancel my membership"]
CORPUS_POINTS = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad", "\u200e",
                 "\u202a", "\u034f", "\ufe00", "\ufe0f", "\u180b", "\u17b4", "\U000e0041",
                 "\U000e0100", "\u115f", "\u1160", "\u3164", "\uffa0", "\u2800"]


def _intra(phrase: str) -> list[int]:
    """Every index strictly inside a word (between two letters)."""
    return [i for i in range(1, len(phrase)) if phrase[i - 1] != " " and phrase[i] != " "]


def _corpus() -> list[str]:
    """Each point inside every word position, each point as every word separator, and a seeded
    sample of one point inside a word plus another as a separator (both classes mixed)."""
    import random
    rng, out = random.Random(20261016), []
    for phrase in CORPUS_PHRASES:
        spaces = [i for i, ch in enumerate(phrase) if ch == " "]
        for cp in CORPUS_POINTS:
            out += [phrase[:i] + cp + phrase[i:] for i in _intra(phrase)]
            out += [phrase[:i] + cp + phrase[i + 1:] for i in spaces]
        for _ in range(60):
            inner, sep = rng.choice(CORPUS_POINTS), rng.choice(CORPUS_POINTS)
            at, gap = rng.choice(_intra(phrase)), rng.choice(spaces)
            text = phrase[:gap] + sep + phrase[gap + 1:]
            out.append(text[:at] + inner + text[at:])
    return out


def test_read_only_refuses_every_invisible_placement_in_deny_phrases() -> None:
    project = _project(WritePolicy.READ_ONLY)
    corpus = _corpus()
    allowed = [ascii(n) for n in corpus if not guards.write_policy_refusal(_case(n), project)]
    assert len(corpus) >= 3000 and allowed == []
