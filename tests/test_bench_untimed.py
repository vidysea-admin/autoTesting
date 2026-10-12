"""AT-655 / bench.md K8: an untimed trial is unavailable on the time axis, never 0 s."""

from __future__ import annotations

import json

from autotester.schema.bench import BenchCorpus, BenchTrial, SeededBug
from autotester.schema.enums import Participant, Severity


def _corpus() -> BenchCorpus:
    return BenchCorpus(
        id="live", app="demo", build_ref="real-build", mode="human_confirmed",
        seeded_bugs=[SeededBug(id="a", description="a", severity=Severity.S1, location="/a",
                               detect_hint="a", provenance="human_independent")],
    )


def _trial(corpus: BenchCorpus, **changes) -> BenchTrial:
    values = dict(id="trial", corpus_id=corpus.id, participant=Participant.HUMAN,
                  kind="human_live", ordering="independent_parallel")
    values.update(changes)
    return BenchTrial(**values)


def test_untimed_timed_and_mixed_trials_score_time_axis_independently() -> None:
    corpus = _corpus()
    untimed = _trial(corpus).score(corpus)
    timed = _trial(corpus, duration_s=42.5).score(corpus)
    zero = _trial(corpus, duration_s=0.0).score(corpus)
    assert untimed["duration_s"] is None
    assert untimed["duration_s_unavailable_reason"] == "timing not recorded"
    assert timed["duration_s"] == 42.5
    assert timed["duration_s_unavailable_reason"] is None
    assert zero["duration_s"] == 0.0, "an explicit measured zero stays a measurement"
    for key in ("detection_rate", "severity_weighted_recall", "false_positive_rate"):
        assert untimed[key] == timed[key]


def test_stored_trial_without_duration_key_loads_as_untimed() -> None:
    corpus = _corpus()
    raw = json.loads(_trial(corpus).model_dump_json())
    raw.pop("duration_s", None)
    legacy = BenchTrial.model_validate(raw)
    assert legacy.duration_s is None
    assert legacy.score(corpus)["duration_s"] is None
